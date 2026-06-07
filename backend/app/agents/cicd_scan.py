import os
import re
from typing import Any, Dict, List
from backend.app.schemas.audit_state import AuditState, Finding, Severity
from backend.app.services.evidence_normalizer import normalize_finding, to_finding_model

def scan_cicd_files(clone_path: str) -> List[Finding]:
    findings = []
    if not clone_path or not os.path.exists(clone_path):
        return findings

    github_workflows_dir = os.path.join(clone_path, '.github', 'workflows')
    if os.path.exists(github_workflows_dir):
        for file in os.listdir(github_workflows_dir):
            if not file.endswith(('.yml', '.yaml')):
                continue

            filepath = os.path.join(github_workflows_dir, file)
            rel_path = os.path.relpath(filepath, clone_path)

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                    if 'pull_request_target' in content and 'checkout' in content:
                        norm = normalize_finding(
                            title="Dangerous pull_request_target checkout",
                            description="Workflow uses pull_request_target and checks out code, potentially exposing secrets to untrusted PRs.",
                            severity=Severity.HIGH,
                            agent_source="CICD_SCAN",
                            file_path=rel_path,
                            confidence="MEDIUM"
                        )
                        findings.append(to_finding_model(norm))

                    if re.search(r'run:\s*curl\s+.*?\|\s*bash', content, re.IGNORECASE):
                        norm = normalize_finding(
                            title="Unsafe curl to bash in CI",
                            description="Workflow executes an unverified remote script directly in the shell.",
                            severity=Severity.MEDIUM,
                            agent_source="CICD_SCAN",
                            file_path=rel_path,
                            confidence="HIGH"
                        )
                        findings.append(to_finding_model(norm))

                    if 'permissions: write-all' in content:
                        norm = normalize_finding(
                            title="Overly permissive GITHUB_TOKEN",
                            description="Workflow uses 'write-all' permissions, which violates least privilege.",
                            severity=Severity.HIGH,
                            agent_source="CICD_SCAN",
                            file_path=rel_path,
                            confidence="HIGH"
                        )
                        findings.append(to_finding_model(norm))

            except Exception:
                continue

    return findings

def cicd_scan_body(db: Any, state: AuditState) -> Dict[str, Any]:
    findings = scan_cicd_files(state.clone_path)

    from backend.app.orchestrator.maestro import log_agent_message, persist_findings
    if findings:
        persist_findings(db, state.job_id, findings)

    log_agent_message(db, state.job_id, "CICD_SCAN", f"CI/CD scan complete. Found {len(findings)} issues.")

    return {
        "cicd_findings": findings
    }
