from typing import Any, Dict, List
from backend.app.schemas.audit_state import AuditState, Finding

def generate_remediation_plan(findings: List[Finding]) -> Dict[str, Any]:
    """
    Generate actionable fix plans without attempting self-edits of the repo.
    """
    tasks = []

    for f in findings:
        if not f.remediation and f.severity.value in ["critical", "high"]:
            # Provide generic remediation if none exists for high severity
            f.remediation = "Review the affected code and apply standard security best practices to mitigate this vulnerability."

        if f.remediation:
            task = {
                "finding_id": f.id,
                "title": f"Fix: {f.title}",
                "description": f.remediation,
                "severity": f.severity.value,
                "file_path": f.file_path,
                "priority": 1 if f.severity.value == "critical" else 2 if f.severity.value == "high" else 3
            }
            tasks.append(task)

    # Sort tasks by priority
    tasks.sort(key=lambda x: x["priority"])

    plan = {
        "summary": f"Generated {len(tasks)} prioritized remediation tasks.",
        "tasks": tasks
    }
    return plan

def remediation_planner_body(db: Any, state: AuditState) -> Dict[str, Any]:
    all_vulns = (state.static_findings + state.semgrep_findings +
                 state.iac_findings + state.dependency_vulns +
                 state.authz_findings + state.cicd_findings + state.container_findings +
                 state.dynamic_findings)

    plan = generate_remediation_plan(all_vulns)

    from backend.app.orchestrator.maestro import log_agent_message
    log_agent_message(db, state.job_id, "REMEDIATION_PLANNER", f"Remediation plan generated with {len(plan['tasks'])} tasks.")

    return {
        "remediation_plan": plan,
        "remediation_tasks": plan.get("tasks", [])
    }
