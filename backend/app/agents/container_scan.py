import os
import re
from typing import Any, Dict, List
from app.schemas.audit_state import AuditState, Finding, Severity
from app.services.evidence_normalizer import normalize_finding, to_finding_model

def scan_dockerfiles(clone_path: str) -> List[Finding]:
    findings = []
    if not clone_path or not os.path.exists(clone_path):
        return findings

    for root, _, files in os.walk(clone_path):
        if any(skip in root.split(os.sep) for skip in ['.git', 'node_modules', 'venv', '.venv']):
            continue

        for file in files:
            if file == 'Dockerfile' or file.endswith('.Dockerfile'):
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, clone_path)

                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()

                        if re.search(r'^FROM\s+[^\s:]+(:latest)?\s', content, re.MULTILINE):
                            norm = normalize_finding(
                                title="Unpinned Base Image",
                                description="Dockerfile uses 'latest' or an unpinned base image.",
                                severity=Severity.MEDIUM,
                                agent_source="CONTAINER_SCAN",
                                file_path=rel_path,
                                confidence="HIGH"
                            )
                            findings.append(to_finding_model(norm))

                        if not re.search(r'^USER\s+(?!root)[^\s]+', content, re.MULTILINE):
                            norm = normalize_finding(
                                title="Container Runs as Root",
                                description="Dockerfile does not declare a non-root USER, causing the container to run as root by default.",
                                severity=Severity.HIGH,
                                agent_source="CONTAINER_SCAN",
                                file_path=rel_path,
                                confidence="MEDIUM"
                            )
                            findings.append(to_finding_model(norm))
                except Exception:
                    continue

    return findings

def container_scan_body(db: Any, state: AuditState) -> Dict[str, Any]:
    findings = scan_dockerfiles(state.clone_path)

    from app.orchestrator.maestro import log_agent_message, persist_findings
    if findings:
        persist_findings(db, state.job_id, findings)

    log_agent_message(db, state.job_id, "CONTAINER_SCAN", f"Container scan complete. Found {len(findings)} issues.")

    return {
        "container_findings": findings
    }
