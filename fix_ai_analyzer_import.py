with open("backend/app/agents/ai_analyzer.py", "r") as f:
    content = f.read()
if "def ai_analyzer_body" not in content:
    content += """
def ai_analyzer_body(db, state):
    from backend.app.reporting.fallback_writer import generate_fallback_report
    from backend.app.config import settings

    if not settings.GEMINI_MODEL:
        return generate_fallback_report(state)

    try:
        dedup, fps, chains, rems = run_ai_analyzer(
            state.static_findings,
            state.dynamic_findings,
            state.dependency_vulns,
            state.iac_findings,
            state.semgrep_findings
        )
        return {
            "deduplicated_findings": dedup,
            "false_positives": fps,
            "attack_chains": chains,
            "remediations": rems
        }
    except Exception as e:
        return generate_fallback_report(state)
"""
with open("backend/app/agents/ai_analyzer.py", "w") as f:
    f.write(content)
