import os
import tempfile
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.app.config import settings, WORKSPACE_DIR
from backend.app.models import AuditJob, AuditReport
from backend.app.schemas import Finding, Severity
from backend.app.services.reporter import ReportGenerator, get_clean_repo_name

logger = logging.getLogger("firecrow.services.report_service")

def generate_markdown_report(
    job_id: str,
    repo_url: str,
    branch: str,
    findings: List[Finding],
    scanner_execution: Dict[str, Any] | None = None
) -> str:
    repo_name = get_clean_repo_name(repo_url)
    date_str = datetime.now(timezone.utc).strftime('%B %d, %Y')
    
    # Calculate summary metrics
    counts = {Severity.CRITICAL: 0, Severity.HIGH: 0, Severity.MEDIUM: 0, Severity.LOW: 0, Severity.INFO: 0}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    total_issues = len(findings)
    
    if counts[Severity.CRITICAL] > 0:
        risk_label = "CRITICAL RISK"
    elif counts[Severity.HIGH] > 0:
        risk_label = "HIGH RISK"
    elif counts[Severity.MEDIUM] > 0:
        risk_label = "MEDIUM RISK"
    elif counts[Severity.LOW] > 0:
        risk_label = "LOW RISK"
    else:
        risk_label = "SECURE"

    md = []
    md.append(f"# Fire Crow Security Audit Report")
    md.append(f"**Continuous Offensive Security & SAST Agent Analysis**\n")
    md.append(f"## Metadata")
    md.append(f"- **Job ID:** {job_id}")
    md.append(f"- **Repository:** {repo_url}")
    md.append(f"- **Branch:** {branch}")
    md.append(f"- **Audit Date:** {date_str}")
    md.append(f"- **Total Findings:** {total_issues}")
    md.append(f"- **Overall Posture:** {risk_label}\n")
    
    md.append(f"## Summary of Findings")
    md.append(f"- **Critical:** {counts[Severity.CRITICAL]}")
    md.append(f"- **High:** {counts[Severity.HIGH]}")
    md.append(f"- **Medium:** {counts[Severity.MEDIUM]}")
    md.append(f"- **Low:** {counts[Severity.LOW]}")
    md.append(f"- **Info:** {counts[Severity.INFO]}\n")
    
    md.append(f"## Findings Table")
    if total_issues > 0:
        md.append("| ID | Title | Severity | Agent | CWE |")
        md.append("| --- | --- | --- | --- | --- |")
        for idx, f in enumerate(findings, 1):
            cwe = f.cwe_id if f.cwe_id else "N/A"
            md.append(f"| FC-{idx:03d} | {f.title} | {f.severity.value.upper()} | {f.agent_source} | {cwe} |")
    else:
        md.append("No security issues detected. Clean audit report.")
    md.append("")
    
    md.append("## Detailed Findings")
    if total_issues > 0:
        for idx, f in enumerate(findings, 1):
            cwe = f.cwe_id if f.cwe_id else "N/A"
            cvss_score = f.cvss_score if f.cvss_score is not None else "N/A"
            cvss_vector = f.cvss_vector if f.cvss_vector else "N/A"
            
            md.append(f"### FC-{idx:03d}: {f.title}")
            md.append(f"- **Severity:** {f.severity.value.upper()}")
            md.append(f"- **Source Agent:** {f.agent_source}")
            md.append(f"- **CWE:** {cwe}")
            md.append(f"- **CVSS:** {cvss_score} ({cvss_vector})")
            md.append(f"\n#### Description")
            md.append(f"{f.description}")
            if f.evidence:
                md.append(f"\n#### Evidence")
                md.append(f"```\n{f.evidence}\n```")
            if f.remediation:
                md.append(f"\n#### Remediation")
                md.append(f"{f.remediation}")
            md.append("\n---\n")
    else:
        md.append("No vulnerabilities were found during static signature auditing or sandbox execution runs.")
        
    return "\n".join(md)

def create_report_in_db(
    db: Session,
    job_id: str,
    repo_url: str,
    branch: str,
    findings: List[Finding],
    scanner_execution: Dict[str, Any] | None = None
) -> AuditReport:
    logger.info("Creating structured database report for job %s", job_id)
    
    # 1. Generate HTML Content
    generator = ReportGenerator()
    html_content = ""
    if settings.REPORT_STORE_HTML_IN_DB:
        html_content = generator.generate_html_report(
            job_id=job_id,
            repo_url=repo_url,
            branch=branch,
            findings=findings,
            scanner_execution=scanner_execution
        )
        
    # 2. Generate Markdown Content
    markdown_content = ""
    if settings.REPORT_STORE_MARKDOWN_IN_DB:
        markdown_content = generate_markdown_report(
            job_id=job_id,
            repo_url=repo_url,
            branch=branch,
            findings=findings,
            scanner_execution=scanner_execution
        )
        
    # 3. Create AuditReport record
    report = AuditReport(
        job_id=job_id,
        html_content=html_content,
        markdown_content=markdown_content
    )
    db.add(report)
    db.flush() # Populate report.id
    
    # 4. Update AuditJob to link this report
    job = db.query(AuditJob).filter(AuditJob.id == job_id).first()
    if job:
        job.report_id = report.id
        db.add(job)
        
    db.commit()
    logger.info("Successfully created structured report %s for job %s", report.id, job_id)
    return report

def generate_temp_pdf_report(html_content: str, job_id: str) -> str:
    """Generates a transient PDF report on disk, returning the absolute path."""
    temp_dir = settings.REPORT_TEMP_DIR
    if not temp_dir:
        temp_dir = os.path.join(WORKSPACE_DIR, "workspace", "temp")
        
    os.makedirs(temp_dir, exist_ok=True)
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_filename = f"fc_report_{job_id}_{timestamp}.pdf"
    pdf_path = os.path.join(temp_dir, pdf_filename)
    
    generator = ReportGenerator()
    success = generator.compile_pdf(html_content, pdf_path)
    if not success:
        raise RuntimeError("Failed to compile temporary PDF report.")
        
    logger.info("Generated temporary PDF report for job %s at %s", job_id, pdf_path)
    return pdf_path
