import re

with open("backend/app/orchestrator/maestro.py", "r") as f:
    content = f.read()

import_statement = "from backend.app.reporting.fallback_writer import generate_fallback_report\n"
if "from backend.app.reporting.fallback_writer" not in content:
    content = content.replace("from backend.app.schemas.audit_state import AuditState, Finding, JobStatus, Severity\n",
                              "from backend.app.schemas.audit_state import AuditState, Finding, JobStatus, Severity\n" + import_statement)

ai_analyzer_body_replacement = """def ai_analyzer_body(db: Session, state: AuditState) -> Dict[str, Any]:
    from backend.app.config import settings

    if not settings.GEMINI_MODEL:
        log_agent_message(db, state.job_id, "AI_ANALYZER", "AI model not configured. Routing to deterministic fallback.")
        return generate_fallback_report(state)

    try:
        dedup, fps, chains, rems = run_ai_analyzer(
            state.static_findings,
            state.dynamic_findings,
            state.dependency_vulns,
            state.iac_findings,
            state.semgrep_findings
        )
        log_agent_message(db, state.job_id, "AI_ANALYZER", f"AI Analyzer complete. {len(dedup)} findings retained.")
        return {
            "deduplicated_findings": dedup,
            "false_positives": fps,
            "attack_chains": chains,
            "remediations": rems
        }
    except Exception as e:
        logger.error(f"AI Analyzer failed: {str(e)}")
        log_agent_message(db, state.job_id, "AI_ANALYZER", f"AI Analyzer failed. Routing to deterministic fallback.")
        return generate_fallback_report(state)"""

content = re.sub(
    r'def ai_analyzer_body\(db: Session, state: AuditState\) -> Dict\[str, Any\]:.*?(?=def ai_analyzer_node)',
    ai_analyzer_body_replacement + "\n\n",
    content,
    flags=re.DOTALL
)

with open("backend/app/orchestrator/maestro.py", "w") as f:
    f.write(content)
