import json
import logging
import shutil
import subprocess
import uuid
from typing import Any, List

from app.schemas import Finding, Severity
from app.services.redaction import redact_text, truncate_text

logger = logging.getLogger("firecrow.agents.dependency")


def _severity(value: str | None) -> Severity:
    normalized = (value or "").lower()
    if normalized in {"critical"}:
        return Severity.CRITICAL
    if normalized in {"high"}:
        return Severity.HIGH
    if normalized in {"medium", "moderate"}:
        return Severity.MEDIUM
    if normalized in {"low"}:
        return Severity.LOW
    return Severity.INFO


def _run_json_command(command: list[str], clone_path: str) -> dict[str, Any] | None:
    try:
        result = subprocess.run(
            command,
            cwd=clone_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=180,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("Dependency scanner command failed: %s", redact_text(str(exc)))
        return None

    if result.returncode not in {0, 1}:
        logger.warning("Dependency scanner exited with code %s: %s", result.returncode, redact_text(result.stderr))
        return None

    try:
        return json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        logger.warning("Dependency scanner returned non-JSON output.")
        return None


def _findings_from_osv(data: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    for result in data.get("results", []):
        packages = result.get("packages", [])
        source = result.get("source", {})
        for package in packages:
            package_info = package.get("package", {})
            package_name = package_info.get("name", "unknown")
            ecosystem = package_info.get("ecosystem", "unknown")
            version = package.get("version", "unknown")
            for vuln in package.get("vulnerabilities", []):
                aliases = vuln.get("aliases") or []
                vuln_id = vuln.get("id") or (aliases[0] if aliases else "OSV")
                severity = Severity.MEDIUM
                severity_records = vuln.get("severity") or []
                if severity_records:
                    severity = _severity(severity_records[0].get("score"))
                findings.append(
                    Finding(
                        id=str(uuid.uuid4()),
                        agent_source="DEPENDENCY_OSV",
                        title=f"{vuln_id} in {package_name}",
                        description=(
                            f"OSV Scanner reported {vuln_id} for {package_name} {version} "
                            f"({ecosystem})."
                        ),
                        severity=severity,
                        evidence=truncate_text(
                            redact_text(
                                "scanner_name=osv-scanner; scanner_mode=real; confidence=high\n"
                                f"manifest={source.get('path', '')}; package={package_name}; "
                                f"version={version}; aliases={', '.join(aliases[:5])}"
                            ),
                            max_length=1000,
                        ),
                        remediation="Upgrade the affected package to a non-vulnerable version listed by OSV.",
                    )
                )
    return findings


def _findings_from_trivy(data: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    for result in data.get("Results", []):
        target = result.get("Target", "")
        for vuln in result.get("Vulnerabilities") or []:
            vuln_id = vuln.get("VulnerabilityID", "TRIVY")
            package_name = vuln.get("PkgName", "unknown")
            installed = vuln.get("InstalledVersion", "unknown")
            fixed = vuln.get("FixedVersion") or "not specified"
            findings.append(
                Finding(
                    id=str(uuid.uuid4()),
                    agent_source="DEPENDENCY_TRIVY",
                    title=f"{vuln_id} in {package_name}",
                    description=(
                        f"Trivy reported {vuln_id} for {package_name} {installed}. "
                        f"Fixed version: {fixed}."
                    ),
                    severity=_severity(vuln.get("Severity")),
                    evidence=truncate_text(
                        redact_text(
                            "scanner_name=trivy; scanner_mode=real; confidence=high\n"
                            f"target={target}; package={package_name}; installed={installed}; fixed={fixed}"
                        ),
                        max_length=1000,
                    ),
                    remediation=f"Upgrade {package_name} to {fixed} or the nearest non-vulnerable release.",
                )
            )
    return findings


def _simulated_findings(dependency_manifests: List[str]) -> list[Finding]:
    if not dependency_manifests:
        return []
    return [
        Finding(
            id=str(uuid.uuid4()),
            agent_source="DEPENDENCY_SCAN",
            title="[SIMULATED] Outdated dependency with known CVE",
            description=(
                "Debug-mode simulated dependency finding. Production reports only include dependency "
                "findings from configured scanners such as osv-scanner or trivy."
            ),
            severity=Severity.MEDIUM,
            evidence="scanner_name=dependency-simulation; scanner_mode=simulated; confidence=low\npackage=requests; version=2.28.1",
            cwe_id="CWE-200",
        )
    ]


def run_dependency_scan(clone_path: str, dependency_manifests: List[str]) -> List[Finding]:
    logger.info("Running dependency scanning on %s manifests.", len(dependency_manifests))
    if not dependency_manifests:
        return []

    osv = shutil.which("osv-scanner")
    if osv:
        data = _run_json_command([osv, "--format", "json", "--recursive", "."], clone_path)
        if data is not None:
            return _findings_from_osv(data)

    trivy = shutil.which("trivy")
    if trivy:
        data = _run_json_command([trivy, "fs", "--format", "json", "--quiet", "."], clone_path)
        if data is not None:
            return _findings_from_trivy(data)

    logger.info("Dependency scanner unavailable; no dependency findings will be generated.")
    return []
