import os
import re
from typing import Any, Dict, List
from backend.app.schemas.audit_state import AuditState, Finding, Severity
from backend.app.services.evidence_normalizer import normalize_finding, to_finding_model

# Extremely simplified heuristics for demonstration/fallback
SECRET_PATTERNS = {
    "AWS_ACCESS_KEY": r"(?i)aws_access_key_id\s*={1,2}\s*[\'\"]?(AKIA[0-9A-Z]{16})[\'\"]?",
    "GENERIC_API_KEY": r"(?i)(?:api_key|token|secret)\s*[:=]\s*[\'\"]([a-zA-Z0-9_\-]{20,})[\'\"]",
    "PRIVATE_KEY": r"-----BEGIN (?:RSA )?PRIVATE KEY-----",
    "GITHUB_TOKEN": r"(?i)gh[pousr]_[A-Za-z0-9_]{36}"
}

def scan_for_secrets(clone_path: str) -> List[Finding]:
    findings = []
    if not clone_path or not os.path.exists(clone_path):
        return findings

    for root, _, files in os.walk(clone_path):
        if any(skip in root.split(os.sep) for skip in ['.git', 'node_modules', 'venv', '.venv']):
            continue

        for file in files:
            filepath = os.path.join(root, file)
            rel_path = os.path.relpath(filepath, clone_path)

            # Catch committed .env files
            if file == '.env' or file.endswith('.pem') or file.endswith('.key'):
                norm = normalize_finding(
                    title="Sensitive File Committed",
                    description=f"A potentially sensitive file '{file}' was found in the repository.",
                    severity=Severity.HIGH,
                    agent_source="SECRET_HISTORY",
                    file_path=rel_path,
                    confidence="HIGH"
                )
                findings.append(to_finding_model(norm))
                continue

            # Skip large files or non-text
            try:
                if os.path.getsize(filepath) > 1024 * 1024:
                    continue
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        # truncate long lines
                        line = line[:2048]
                        for key, pattern in SECRET_PATTERNS.items():
                            if re.search(pattern, line):
                                norm = normalize_finding(
                                    title=f"Potential Hardcoded {key}",
                                    description=f"Found a pattern matching {key}.",
                                    severity=Severity.CRITICAL,
                                    agent_source="SECRET_HISTORY",
                                    file_path=rel_path,
                                    line_number=line_num,
                                    confidence="MEDIUM",
                                    evidence="<REDACTED SECRET VALUE>"
                                )
                                findings.append(to_finding_model(norm))
            except Exception:
                continue

    return findings

def secret_history_body(db: Any, state: AuditState) -> Dict[str, Any]:
    findings = scan_for_secrets(state.clone_path)

    from backend.app.orchestrator.maestro import log_agent_message, persist_findings
    if findings:
        persist_findings(db, state.job_id, findings)

    log_agent_message(db, state.job_id, "SECRET_HISTORY", f"Secret scan complete. Found {len(findings)} issues.")

    return {
        "secret_history_findings": findings
    }
