import logging
import json
import urllib.request
import urllib.error
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any
from backend.app.schemas import Finding, Severity
from backend.app.config import settings

logger = logging.getLogger("firecrow.agents.google_agent")

def run_google_agent(
    job_id: str,
    repo_url: str,
    findings: List[Finding],
    remediations: List[Dict[str, Any]],
    recipient_email: str
) -> Dict[str, Any]:
    """
    Runs the Google Security Agent.
    1. Analyzes the security findings and remediations for PR/Merge risks using Gemini.
    2. Sends a structured PR Risk Assessment Alert email via Google SMTP (Gmail) or Resend.
    """
    logger.info("Running Google Security Agent for job %s...", job_id)
    logs = [f"Started Google Agent for job {job_id}"]
    
    # 1. Analyze PR Risks using Gemini
    api_key = settings.GEMINI_API_KEY
    pr_risk_analysis = {}
    
    if not api_key:
        logs.append("GEMINI_API_KEY not configured. Generating simulated PR risk report.")
        # Simulated PR risks if no Gemini API Key is configured
        has_critical = any(f.severity == Severity.CRITICAL for f in findings)
        has_high = any(f.severity == Severity.HIGH for f in findings)
        
        risk_level = "LOW"
        risk_desc = "The changes checked appear generally low risk. No critical vulnerabilities detected."
        if has_critical:
            risk_level = "CRITICAL"
            risk_desc = "Critical risks identified! Exposed credentials or active exploit paths detected. Merging is highly discouraged."
        elif has_high:
            risk_level = "HIGH"
            risk_desc = "High security risks identified. Vulnerabilities found that could lead to unauthorized access. Suggest addressing remediations before merge."
            
        pr_risk_analysis = {
            "overall_pr_risk": risk_level,
            "risk_description": risk_desc,
            "key_risk_factors": [
                "Exposed secrets or API keys" if has_critical else "Static analysis code quality alerts",
                "High severity security findings present" if has_high else "Dependency vulnerabilities checked"
            ],
            "merge_recommendation": "BLOCK" if (has_critical or has_high) else "APPROVE"
        }
    else:
        # Prompt Gemini to evaluate PR risks
        findings_summary = []
        for f in findings:
            findings_summary.append({
                "id": f.id,
                "title": f.title,
                "severity": f.severity.value,
                "description": f.description
            })
            
        prompt = f"""You are a senior Google AI Security Architect. Analyze the security audit findings for a proposed pull request/code merge:
Repository: {repo_url}
Findings: {json.dumps(findings_summary, indent=2)}
Remediations: {json.dumps(remediations, indent=2)}

Your task:
Evaluate the security risk of merging this code.
1. Determine the overall PR risk level (CRITICAL | HIGH | MEDIUM | LOW).
2. Write a detailed risk description summarizing the threat.
3. List 2-4 key risk factors (concrete items).
4. Provide a merge recommendation: "BLOCK" (if there are critical or high findings), "REVIEW" (if medium), or "APPROVE" (if low/info or clean).

Output your evaluation in this exact JSON format (and ONLY output this raw JSON structure, no other text or explanation):
{{
  "overall_pr_risk": "CRITICAL | HIGH | MEDIUM | LOW",
  "risk_description": "Summary of the merge risks...",
  "key_risk_factors": ["Factor 1", "Factor 2"],
  "merge_recommendation": "BLOCK | REVIEW | APPROVE"
}}
"""
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.1
            }
        }
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=req_data)
            req.add_header("Content-Type", "application/json")
            
            with urllib.request.urlopen(req, timeout=30) as response:
                res_content = response.read().decode("utf-8")
                res_json = json.loads(res_content)
                text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                
                # Strip markdown blocks
                if text.startswith("```"):
                    lines = text.splitlines()
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines[-1].startswith("```"):
                        lines = lines[:-1]
                    text = "\n".join(lines).strip()
                    
                pr_risk_analysis = json.loads(text)
                logs.append("Successfully evaluated Pull Request security risks using Gemini.")
        except Exception as exc:
            logs.append(f"AI PR Risk evaluation failed: {exc}. Using fallback analysis.")
            pr_risk_analysis = {
                "overall_pr_risk": "HIGH" if findings else "LOW",
                "risk_description": "Failed to run LLM assessment. Fallback analysis flags high risk due to presence of unresolved findings.",
                "key_risk_factors": ["AI analysis connection timeout", "Unresolved findings in pipeline"],
                "merge_recommendation": "REVIEW" if findings else "APPROVE"
            }

    # 2. Format a gorgeous Google Agent PR Risk Alert email
    risk_level = str(pr_risk_analysis.get("overall_pr_risk", "UNKNOWN")).upper()
    recommendation = str(pr_risk_analysis.get("merge_recommendation", "REVIEW")).upper()
    if risk_level not in {"CRITICAL", "HIGH", "MEDIUM", "LOW"}:
        risk_level = "UNKNOWN"
    if recommendation not in {"BLOCK", "REVIEW", "APPROVE"}:
        recommendation = "REVIEW"
    risk_desc = pr_risk_analysis.get("risk_description", "")
    key_factors = pr_risk_analysis.get("key_risk_factors", [])
    
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
            <a href="http://localhost:3000/dashboard" style="background-color: #0f172a; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; display: inline-block; transition: background-color 0.2s;">View Full Security Dashboard</a>
        </div>
        
        <p style="font-size: 12px; color: #94a3b8; border-top: 1px solid #f1f5f9; padding-top: 15px; margin-top: 30px; text-align: center;">This analysis was autonomously formulated by the Fire Crow Google Security Agent orchestrator.</p>
    </div>
    """

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
            logs.append(f"Google SMTP email delivery failed: {e}. Attempting Resend fallback...")
            
    # 2. Resend fallback
    if not delivered and settings.RESEND_API_KEY:
        try:
            import resend
            logger.info("Google Agent sending PR Risk email to %s via Resend", recipient_email)
            resend.api_key = settings.RESEND_API_KEY
            resend.Emails.send({
                "from": f"Google Security Agent <{settings.SENDER_EMAIL}>",
                "to": [recipient_email],
                "subject": f"🤖 Google Agent Alert: PR Risk Assessment ({risk_level}) - Job {job_id[:8]}",
                "html": html_body
            })
            delivered = True
            logs.append(f"PR risk assessment email alert successfully sent via Resend to {recipient_email}.")
        except Exception as e:
            logs.append(f"Resend email delivery failed: {e}.")

    if not delivered:
        logs.append("No active mail gateway was able to transmit the PR risk email. Logged output to console.")
        
    return {
        "google_agent_delivered": delivered,
        "google_agent_pr_risks_analyzed": True,
        "google_agent_risk_report": pr_risk_analysis,
        "google_agent_logs": logs
    }

def html_escape(text: str) -> str:
    """Escapes HTML special characters."""
    import html
    return html.escape(text)
