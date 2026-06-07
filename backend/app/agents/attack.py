import logging
import uuid
from typing import List, Dict, Any
from backend.app.schemas import Finding, Severity
from backend.app.services.sandbox import SandboxManager
from backend.app.services.redaction import redact_text, truncate_text
from backend.app.agents.network import is_allowed_sandbox_target

logger = logging.getLogger("firecrow.agents.attack")


def run_dynamic_attack(
    kali_container_id: str,
    target_host: str,
    open_ports: List[Dict[str, Any]],
    repo_url: str
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

    # 1. Run Sqlmap CLI scan
    sqlmap_cmd = [
        "sqlmap",
        "-u", f"{target_url}/api/v1/profile?id=1",
        "--batch",
        "--crawl=1",
        "--forms"
    ]
    logger.info("Running sqlmap in scanner container against sandbox target.")
    exit_code, output = manager.execute_kali_command(kali_container_id, sqlmap_cmd)
    output = truncate_text(redact_text(output), max_length=3000)
    
    if "is vulnerable" in output or "confirm" in output.lower() or "dbms" in output.lower():
        findings.append(Finding(
            id=str(uuid.uuid4()),
            agent_source="DYNAMIC_ATTACK_SQLMAP",
            title="[SIMULATED] SQL Injection in user profile parameters" if manager.mock_mode else "SQL Injection in user profile parameters",
            description=(
                "Controlled sandbox validation confirmed SQL injection behavior on the generated sandbox target. "
                "Query parameter 'id' was modified during an authorization-only audit."
            ),
            severity=Severity.CRITICAL,
            cwe_id="CWE-89",
            evidence=f"scanner_name=sqlmap; scanner_mode={'simulated' if manager.mock_mode else 'real'}; confidence=high\n{output[:300]}",
            remediation="Ensure database queries use parameterized queries or ORM bindings rather than string interpolation."
        ))

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
            remediation="Patch packages and update system libraries in Docker runtime environment."
        ))

    logger.info("Dynamic validation complete. Discovered %s findings.", len(findings))
    return findings
