import json
import logging
import shutil
import subprocess
import uuid
from typing import Any, List

from app.schemas import Finding, Severity
from app.services.redaction import redact_text, truncate_text

logger = logging.getLogger("firecrow.agents.semgrep")


def _severity(value: str | None) -> Severity:
    normalized = (value or "").lower()
    if normalized in {"error", "critical"}:
        return Severity.HIGH
    if normalized in {"warning", "medium"}:
        return Severity.MEDIUM
    if normalized in {"info", "low"}:
        return Severity.LOW
    return Severity.MEDIUM


def _run_semgrep_json(clone_path: str) -> dict[str, Any] | None:
    semgrep = shutil.which("semgrep")
    if not semgrep:
        return None

    command = [
        semgrep,
        "--config",
        "p/default",
        "--json",
        "--quiet",
        "--no-git-ignore",
        ".",
    ]
    try:
        result = subprocess.run(
            command,
            cwd=clone_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=240,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("Semgrep command failed: %s", redact_text(str(exc)))
        return None

    if result.returncode not in {0, 1}:
        logger.warning("Semgrep exited with code %s: %s", result.returncode, redact_text(result.stderr))
        return None

    try:
        return json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        logger.warning("Semgrep returned non-JSON output.")
        return None


def _finding_from_result(result: dict[str, Any]) -> Finding:
    extra = result.get("extra", {})
    metadata = extra.get("metadata") or {}
    path = result.get("path", "")
    start = result.get("start") or {}
    rule_id = result.get("check_id", "semgrep")
    cwe = ""
    cwe_values = metadata.get("cwe") or []
    if isinstance(cwe_values, list) and cwe_values:
        cwe = str(cwe_values[0]).split(":", 1)[0]

    return Finding(
        id=str(uuid.uuid4()),
        agent_source="SEMGREP",
        title=extra.get("message") or rule_id,
        description=f"Semgrep rule {rule_id} reported a finding in {path}.",
        severity=_severity(extra.get("severity")),
        evidence=truncate_text(
            redact_text(
                "scanner_name=semgrep; scanner_mode=real; confidence=medium\n"
                f"rule_id={rule_id}; path={path}; line={start.get('line', '')}"
            ),
            max_length=1000,
        ),
        cwe_id=cwe or None,
        remediation="Review the Semgrep rule guidance and update the affected code path.",
    )


def _simulated_findings(tech_stack: List[str]) -> list[Finding]:
    if not any("python" in stack.lower() for stack in tech_stack):
        return []
    return [
        Finding(
            id=str(uuid.uuid4()),
            agent_source="SEMGREP",
            title="[SIMULATED] Hardcoded Secret or Insecure Deserialization",
            description=(
                "Debug-mode simulated Semgrep finding. Production reports only include Semgrep "
                "findings when the semgrep CLI executes successfully."
            ),
            severity=Severity.HIGH,
            evidence="scanner_name=semgrep-simulation; scanner_mode=simulated; confidence=low\nrule_id=debug.simulated.yaml-load",
            cwe_id="CWE-502",
        )
    ]


def run_semgrep_scan(clone_path: str, tech_stack: List[str]) -> List[Finding]:
    logger.info("Running Semgrep AST scanning.")
    data = _run_semgrep_json(clone_path)
    if data is not None:
        return [_finding_from_result(result) for result in data.get("results", [])]

    logger.info("Semgrep unavailable; no Semgrep findings will be generated.")
    return []
