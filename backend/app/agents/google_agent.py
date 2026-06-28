import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any
from app.schemas import Finding, Severity
from app.config import settings, WORKSPACE_DIR
from app.services.redaction import redact_text

logger = logging.getLogger("firecrow.agents.google_agent")


def html_escape(text: str) -> str:
    """Escapes HTML special characters."""
    import html
    return html.escape(text)


def _deterministic_pr_risk_analysis(findings: List[Finding], remediations: List[Dict[str, Any]]) -> Dict[str, Any]:
    severity_counts = {
        Severity.CRITICAL: sum(1 for finding in findings if finding.severity == Severity.CRITICAL),
        Severity.HIGH: sum(1 for finding in findings if finding.severity == Severity.HIGH),
        Severity.MEDIUM: sum(1 for finding in findings if finding.severity == Severity.MEDIUM),
        Severity.LOW: sum(1 for finding in findings if finding.severity == Severity.LOW),
        Severity.INFO: sum(1 for finding in findings if finding.severity == Severity.INFO),
    }

    if severity_counts[Severity.CRITICAL]:
        risk_level = "CRITICAL"
        recommendation = "BLOCK"
        description = "Critical findings remain unresolved. Merging would keep materially exploitable risk in the branch."
    elif severity_counts[Severity.HIGH]:
        risk_level = "HIGH"
        recommendation = "BLOCK"
        description = "High-severity findings remain unresolved and should be remediated before merge."
    elif severity_counts[Severity.MEDIUM]:
        risk_level = "MEDIUM"
        recommendation = "REVIEW"
        description = "Medium-severity findings need reviewer attention before the change is considered safe to merge."
    elif findings:
        risk_level = "LOW"
        recommendation = "APPROVE"
        description = "Only low or informational findings remain. Merge can proceed with normal reviewer awareness."
    else:
        risk_level = "LOW"
        recommendation = "APPROVE"
        description = "No findings were supplied to the PR risk agent."

    key_risk_factors: List[str] = []
    if severity_counts[Severity.CRITICAL]:
        key_risk_factors.append(f"{severity_counts[Severity.CRITICAL]} critical finding(s) are still open.")
    if severity_counts[Severity.HIGH]:
        key_risk_factors.append(f"{severity_counts[Severity.HIGH]} high-severity finding(s) are still open.")
    if severity_counts[Severity.MEDIUM]:
        key_risk_factors.append(f"{severity_counts[Severity.MEDIUM]} medium-severity finding(s) require review.")
    if remediations:
        key_risk_factors.append(f"{len(remediations)} remediation change(s) require manual verification before merge.")
    if not key_risk_factors:
        key_risk_factors.append("No blocking risk factors were detected from the supplied findings.")

    return {
        "overall_pr_risk": risk_level,
        "risk_description": description,
        "key_risk_factors": key_risk_factors[:4],
        "merge_recommendation": recommendation,
    }

def run_google_agent(
    job_id: str,
    repo_url: str,
    findings: List[Finding],
    remediations: List[Dict[str, Any]],
    recipient_email: str
) -> Dict[str, Any]:
    """
    Runs the Google Security Agent.
    1. Analyzes the security findings and remediations for PR/Merge risks deterministically.
    2. Sends a structured PR Risk Assessment Alert email via Google SMTP (Gmail) or Resend.
    """
    logger.info("Running Google Security Agent for job %s...", job_id)
    logs = [f"Started Google Agent for job {job_id}"]

    logs.append("Using deterministic PR risk assessment. LLM scoring is disabled for this workflow.")
    pr_risk_analysis = _deterministic_pr_risk_analysis(findings, remediations)

    # 2. Format a gorgeous Google Agent PR Risk Alert email
    risk_level = str(pr_risk_analysis.get("overall_pr_risk", "UNKNOWN")).upper()
    recommendation = str(pr_risk_analysis.get("merge_recommendation", "REVIEW")).upper()
    if risk_level not in {"CRITICAL", "HIGH", "MEDIUM", "LOW"}:
        risk_level = "UNKNOWN"
    if recommendation not in {"BLOCK", "REVIEW", "APPROVE"}:
        recommendation = "REVIEW"
    risk_desc = str(pr_risk_analysis.get("risk_description", ""))
    raw_factors = pr_risk_analysis.get("key_risk_factors", [])
    if not isinstance(raw_factors, list):
        raw_factors = [raw_factors]
    key_factors: List[str] = [str(f) for f in raw_factors]
    
    # Visual styling based on risk level
    risk_color = "#ef4444"  # Red
    rec_badge_style = "background-color: #fee2e2; color: #991b1b; border: 1px solid #fca5a5;"
    if risk_level == "HIGH":
        risk_color = "#f97316"  # Orange
        rec_badge_style = "background-color: #ffedd5; color: #9a3412; border: 1px solid #fed7aa;"
    elif risk_level == "MEDIUM":
        risk_color = "#eab308"  # Yellow/Gold
        rec_badge_style = "background-color: #fef9c3; color: #713f12; border: 1px solid #fef08a;"
    elif risk_level == "LOW":
        risk_color = "#10b981"  # Green
        rec_badge_style = "background-color: #d1fae5; color: #065f46; border: 1px solid #a7f3d0;"

    factors_html = "".join(f"<li style='margin-bottom: 8px;'>⚠️ {html_escape(factor)}</li>" for factor in key_factors)
    safe_repo_url = html_escape(repo_url)
    safe_risk_level = html_escape(risk_level)
    safe_recommendation = html_escape(recommendation)

    dashboard_url = f"{settings.FRONTEND_URL.rstrip('/')}/dashboard" if settings.FRONTEND_URL else "#"

    html_body = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 25px; border: 1px solid #e2e8f0; border-radius: 12px; color: #1e293b; background-color: #ffffff; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
        <div style="text-align: center; border-bottom: 2px solid #f1f5f9; padding-bottom: 15px; margin-bottom: 20px;">
            <span style="font-size: 24px; font-weight: bold; color: #0f172a;">🤖 Google AI Security Agent</span>
            <div style="font-size: 14px; color: #64748b; margin-top: 5px;">Repository Pull Request Risk Evaluation</div>
        </div>
        
        <p style="font-size: 16px; line-height: 1.6; color: #334155;">Hello Security Team,</p>
        <p style="font-size: 16px; line-height: 1.6; color: #334155;">The <strong>Google Security Agent</strong> has finished evaluating PR merge risks for repository: <br><code style="background-color: #f1f5f9; padding: 3px 6px; border-radius: 4px; font-size: 14px;">{safe_repo_url}</code></p>
        
        <div style="margin: 25px 0; padding: 15px; border-radius: 8px; border-left: 5px solid {risk_color}; background-color: #f8fafc;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <span style="font-size: 18px; font-weight: 700; color: #0f172a;">Risk Assessment: <span style="color: {risk_color};">{safe_risk_level}</span></span>
                <span style="padding: 4px 10px; font-size: 12px; font-weight: bold; border-radius: 4px; {rec_badge_style}">REC: {safe_recommendation}</span>
            </div>
            <p style="font-size: 14px; line-height: 1.5; color: #475569; margin: 5px 0 0 0;">{html_escape(risk_desc)}</p>
        </div>

        <h4 style="color: #0f172a; margin-top: 25px; margin-bottom: 10px; border-bottom: 1px solid #e2e8f0; padding-bottom: 5px;">Key Risk Factors</h4>
        <ul style="padding-left: 20px; font-size: 14px; line-height: 1.6; color: #334155; margin-top: 5px;">
            {factors_html or "<li>No critical security risk factors identified.</li>"}
        </ul>

        <div style="text-align: center; margin-top: 35px; margin-bottom: 15px;">
            <a href="{html_escape(dashboard_url)}" style="background-color: #0f172a; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; display: inline-block; transition: background-color 0.2s;">View Full Security Dashboard</a>
        </div>
        
        <p style="font-size: 12px; color: #94a3b8; border-top: 1px solid #f1f5f9; padding-top: 15px; margin-top: 30px; text-align: center;">This analysis was autonomously formulated by the Fire Crow Google Security Agent orchestrator.</p>
    </div>
    """

    if not recipient_email:
        logs.append("No recipient email is available for Google Agent delivery. Skipping email transmission.")
        return {
            "google_agent_delivered": False,
            "google_agent_pr_risks_analyzed": True,
            "google_agent_risk_report": pr_risk_analysis,
            "google_agent_logs": logs,
        }

    # Send email
    delivered = False
    
    # 1. Try Google SMTP
    if settings.SMTP_USER and settings.SMTP_PASSWORD:
        try:
            logger.info("Google Agent sending PR Risk email to %s via Google SMTP", recipient_email)
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"🤖 Google Agent Alert: PR Risk Assessment ({risk_level}) - Job {job_id[:8]}"
            msg["From"] = f"Google Security Agent <{settings.SMTP_USER}>"
            msg["To"] = recipient_email
            msg.attach(MIMEText(html_body, "html"))
            
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_USER, [recipient_email], msg.as_string())
                
            delivered = True
            logs.append(f"PR risk assessment email alert successfully sent via Google SMTP to {recipient_email}.")
        except Exception as e:
            logs.append(f"Google SMTP email delivery failed: {redact_text(str(e))}. Attempting Resend fallback...")
            
    # 2. Resend fallback
    if not delivered and settings.RESEND_API_KEY:
        try:
            import resend
            logger.info("Google Agent sending PR Risk email to %s via Resend", recipient_email)
            resend.api_key = settings.RESEND_API_KEY
            sender_email = settings.SENDER_EMAIL or settings.SMTP_USER
            resend.Emails.send({
                "from": f"Google Security Agent <{sender_email}>",
                "to": [recipient_email],
                "subject": f"🤖 Google Agent Alert: PR Risk Assessment ({risk_level}) - Job {job_id[:8]}",
                "html": html_body
            })
            delivered = True
            logs.append(f"PR risk assessment email alert successfully sent via Resend to {recipient_email}.")
        except Exception as e:
            logs.append(f"Resend email delivery failed: {redact_text(str(e))}.")

    # 3. Brevo fallback
    if not delivered and settings.BREVO_API_KEY:
        try:
            import httpx
            logger.info("Google Agent sending PR Risk email to %s via Brevo", recipient_email)
            sender_email = settings.SENDER_EMAIL or settings.SMTP_USER
            response = httpx.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={
                    "api-key": settings.BREVO_API_KEY,
                    "content-type": "application/json",
                    "accept": "application/json"
                },
                json={
                    "sender": {"email": sender_email, "name": "Google Security Agent"},
                    "to": [{"email": recipient_email}],
                    "subject": f"🤖 Google Agent Alert: PR Risk Assessment ({risk_level}) - Job {job_id[:8]}",
                    "htmlContent": html_body
                },
                timeout=15.0
            )
            response.raise_for_status()
            delivered = True
            logs.append(f"PR risk assessment email alert successfully sent via Brevo to {recipient_email}.")
        except Exception as e:
            logs.append(f"Brevo email delivery failed: {redact_text(str(e))}.")

    if not delivered:
        if not settings.DEBUG:
            logs.append("No active mail gateway transmitted the PR risk email. Local fallback is disabled outside DEBUG mode.")
            return {
                "google_agent_delivered": False,
                "google_agent_pr_risks_analyzed": True,
                "google_agent_risk_report": pr_risk_analysis,
                "google_agent_logs": logs,
            }
        try:
            import os
            import re
            from datetime import datetime
            sent_emails_dir = os.path.join(WORKSPACE_DIR, "workspace", "sent_emails")
            os.makedirs(sent_emails_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_email = re.sub(r'[^a-zA-Z0-9@.]', '_', recipient_email)
            filename = f"{timestamp}_{safe_email}_google_agent_alert.html"
            filepath = os.path.join(sent_emails_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html_body)
            delivered = True
            logs.append(f"Saved fallback local Google Security Agent PR risk assessment HTML email report to: {filepath}")
        except Exception as le:
            logs.append(f"Failed to write local fallback email: {redact_text(str(le))}")
            logs.append("No active mail gateway was able to transmit the PR risk email. Logged output to console.")
        
    return {
        "google_agent_delivered": delivered,
        "google_agent_pr_risks_analyzed": True,
        "google_agent_risk_report": pr_risk_analysis,
        "google_agent_logs": logs
    }
