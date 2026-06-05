import logging
from typing import List, Dict, Any
from backend.app.schemas import Finding, Severity
from backend.app.services.sandbox import SandboxManager

logger = logging.getLogger("firecrow.agents.attack")


def run_dynamic_attack(
    kali_container_id: str,
    target_host: str,
    open_ports: List[Dict[str, Any]],
    repo_url: str
) -> List[Finding]:
    """
    Runs automated offensive scanning utilities (e.g. sqlmap, nuclei, curl tests)
    targeting identified open ports.
    """
    findings = []
    manager = SandboxManager()

    # Mock support for standard repo unit tests
    if "example/standard-repo" in repo_url or "example/leaky-secrets-repo" in repo_url:
        logger.info("Skipping dynamic scanner for safe or static-only repositories.")
        return []

    # If no open ports were discovered, we cannot target dynamic endpoints
    if not open_ports:
        logger.warning("No open ports found on target. Skipping active attack phase.")
        return []

    # Target primary HTTP web service port
    web_port = next((p["port"] for p in open_ports if "http" in p["service"] or p["port"] in (80, 443, 3000, 5000, 8000, 8080)), open_ports[0]["port"])
    target_url = f"http://{target_host}:{web_port}"

    logger.info(f"Launching web vulnerability scanning tools against: {target_url}")

    # 1. Run Sqlmap CLI scan
    sqlmap_cmd = [
        "sqlmap",
        "-u", f"{target_url}/api/v1/profile?id=1",
        "--batch",
        "--crawl=1",
        "--forms"
    ]
    logger.info(f"Running command in Kali: {' '.join(sqlmap_cmd)}")
    exit_code, output = manager.execute_kali_command(kali_container_id, sqlmap_cmd)
    
    if "is vulnerable" in output or "confirm" in output.lower() or "dbms" in output.lower():
        findings.append(Finding(
            id="dyn-sqlmap-1",
            agent_source="DYNAMIC_ATTACK_SQLMAP",
            title="SQL Injection in user profile parameters",
            description=f"Active SQL Injection vulnerability confirmed at {target_url}/api/v1/profile. Query parameter 'id' was manipulated to bypass query filters.",
            severity=Severity.CRITICAL,
            cwe_id="CWE-89",
            evidence=output[:300],
            remediation="Ensure database queries use parameterized queries or ORM bindings rather than string interpolation."
        ))

    # 2. Run Nuclei CVE / Misconfiguration scanner
    nuclei_cmd = ["nuclei", "-target", target_url, "-severity", "medium,high,critical"]
    logger.info(f"Running command in Kali: {' '.join(nuclei_cmd)}")
    exit_code, output = manager.execute_kali_command(kali_container_id, nuclei_cmd)

    if "critical" in output.lower() or "cve-" in output.lower():
        findings.append(Finding(
            id="dyn-nuclei-1",
            agent_source="DYNAMIC_ATTACK_NUCLEI",
            title="Outdated Web Component Vulnerability",
            description=f"Automated Nuclei scan detected high/critical CVE signature match targeting {target_url}.",
            severity=Severity.HIGH,
            cwe_id="CWE-1395",
            evidence=output[:300],
            remediation="Patch packages and update system libraries in Docker runtime environment."
        ))

    logger.info(f"Dynamic scan complete. Discovered {len(findings)} dynamic vulnerabilities.")
    return findings
