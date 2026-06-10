import re
from typing import Any, Dict, List
from app.schemas.audit_state import AuditState, Finding, Severity
from app.services.evidence_normalizer import normalize_finding, to_finding_model

def analyze_authz(api_surface: List[Dict[str, Any]]) -> List[Finding]:
    """
    Very basic heuristic authorization analyzer that checks detected routes
    for patterns that might indicate IDOR or missing auth.
    """
    findings = []

    for route in api_surface:
        path = route.get("path", "")
        file_path = route.get("file", "")
        line_num = route.get("line")

        # Check if the route has a path parameter like {id} or :id
        if re.search(r'\{.*id\}', path) or re.search(r':\w*id', path):
            # Without doing deep AST analysis, we flag it as a potential IDOR risk
            # if we don't clearly see a risk tag that implies it's guarded.

            norm = normalize_finding(
                title="Potential IDOR (Insecure Direct Object Reference)",
                description=f"Route '{path}' accepts an ID parameter. Ensure that ownership checks (e.g., tenant_id, user_id) are enforced in the handler.",
                severity=Severity.HIGH,
                agent_source="AUTHZ_IDOR",
                file_path=file_path,
                line_number=line_num,
                route=path,
                confidence="LOW" # Low because it's just a regex heuristic
            )
            findings.append(to_finding_model(norm))

        # Check for admin routes
        if "admin" in path.lower() and "admin" not in route.get("risk_tag", ""):
            norm = normalize_finding(
                title="Potential Missing Admin Guard",
                description=f"Route '{path}' appears to be administrative but its guard status is unclear.",
                severity=Severity.HIGH,
                agent_source="AUTHZ_IDOR",
                file_path=file_path,
                line_number=line_num,
                route=path,
                confidence="LOW"
            )
            findings.append(to_finding_model(norm))

    return findings

def authz_idor_body(db: Any, state: AuditState) -> Dict[str, Any]:
    findings = analyze_authz(state.api_surface)

    from app.orchestrator.maestro import log_agent_message, persist_findings
    if findings:
        persist_findings(db, state.job_id, findings)

    log_agent_message(db, state.job_id, "AUTHZ_IDOR", f"Authz/IDOR scan complete. Found {len(findings)} potential issues.")

    return {
        "authz_findings": findings
    }
