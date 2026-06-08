import json
import logging
from typing import Any, Dict, List
from backend.app.schemas.audit_state import AuditState, Finding, Severity

logger = logging.getLogger("firecrow.reporting.fallback")

def generate_fallback_report(state: AuditState) -> Dict[str, Any]:
    logger.info("Generating deterministic fallback report for job %s", state.job_id)

    # We will use all findings as "deduplicated" since we skip AI Analyzer
    all_findings = (state.static_findings + state.semgrep_findings +
                    state.iac_findings + state.dependency_vulns +
                    state.authz_findings + state.cicd_findings + state.container_findings +
                    state.dynamic_findings)

    # Very basic deduplication
    seen = set()
    dedup = []
    for f in all_findings:
        key = f"{f.title}|{f.file_path}|{f.line_number}"
        if key not in seen:
            seen.add(key)
            dedup.append(f)

    # Generate executive summary
    critical_count = sum(1 for f in dedup if f.severity == Severity.CRITICAL)
    high_count = sum(1 for f in dedup if f.severity == Severity.HIGH)
    medium_low_count = sum(1 for f in dedup if f.severity in [Severity.MEDIUM, Severity.LOW, Severity.INFO])

    summary = f"Deterministic audit complete. Found {critical_count} critical, {high_count} high, and {medium_low_count} medium/low severity issues."

    remediation_tasks = []
    for f in dedup:
        if f.severity in [Severity.CRITICAL, Severity.HIGH]:
            remediation_tasks.append({
                "finding_id": f.id,
                "title": f"Fix {f.severity.value.upper()}: {f.title}",
                "description": f.remediation or "Review code for this security vulnerability.",
                "file_path": f.file_path
            })

    email_body = f"""
    Security Audit Fallback Report

    Project: {state.repo_url}
    Branch: {state.repo_branch}
    Job ID: {state.job_id}

    {summary}

    Please check the FireCrow dashboard for complete details.
    """

    pr_body = f"""
    ## Security Remediation Plan

    This is an automatically generated remediation plan from FireCrow (Fallback Deterministic Engine).

    {summary}

    ### Action Items:
    """
    for task in remediation_tasks[:5]: # Limit to top 5 in PR
        pr_body += f"- [ ] **{task['title']}**: {task['description']} (File: `{task['file_path']}`)\n"

    if len(remediation_tasks) > 5:
        pr_body += f"\n*(and {len(remediation_tasks) - 5} more... please see full report)*\n"

    return {
        "deduplicated_findings": dedup,
        "false_positives": [],
        "attack_chains": [],
        "remediations": [],
        "fallback_report": {
            "executive_summary": summary,
            "risk_summary": {
                "critical": critical_count,
                "high": high_count,
                "medium_low": medium_low_count
            },
            "remediation_tasks": remediation_tasks,
        },
        "email_subject": f"FireCrow Security Audit Fallback: {state.repo_name}",
        "email_body": email_body,
        "pr_title": f"Security Remediation: {state.repo_name}",
        "pr_body": pr_body
    }
