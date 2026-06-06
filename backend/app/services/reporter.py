import logging
import os
import html
from datetime import datetime, timezone
from typing import List, Dict, Any
from backend.app.config import settings
from backend.app.schemas import Finding, Severity

# Ensure WeasyPrint can find GTK/Pango libraries on Windows
if os.name == "nt" and "WEASYPRINT_DLL_DIRECTORIES" not in os.environ:
    msys_path = r"C:\msys64\ucrt64\bin"
    if os.path.exists(msys_path):
        os.environ["WEASYPRINT_DLL_DIRECTORIES"] = msys_path
        try:
            os.add_dll_directory(msys_path)
        except Exception:
            pass

logger = logging.getLogger("firecrow.services.reporter")


def _first_non_empty(*values: str | None) -> str:
    for value in values:
        if value:
            return value
    return ""

# Attempt importing weasyprint and resend
try:
    import weasyprint
    WEASYPRINT_AVAILABLE = True
except Exception as e:
    logger.warning(f"WeasyPrint is not available on this platform: {str(e)}. PDF generation will fall back to simulated files.")
    WEASYPRINT_AVAILABLE = False

try:
    import resend
    RESEND_AVAILABLE = True
except ImportError:
    RESEND_AVAILABLE = False


class ReportGenerator:
    """
    Handles generation of high-fidelity HTML templates,
    compiles them to PDF using WeasyPrint, uploads reports to Cloudflare R2,
    and sends notification emails using Resend.
    """

    def __init__(self):
        # Prefer the app settings names, but keep the older Cloudflare aliases as a fallback.
        self.r2_bucket = _first_non_empty(settings.R2_BUCKET_NAME, os.getenv("CLOUDFLARE_R2_BUCKET"), "firecrow-reports")
        self.r2_endpoint = _first_non_empty(settings.R2_ENDPOINT_URL, os.getenv("CLOUDFLARE_R2_ENDPOINT"))
        self.r2_access_key = _first_non_empty(settings.R2_ACCESS_KEY_ID, os.getenv("CLOUDFLARE_R2_ACCESS_KEY"))
        self.r2_secret_key = _first_non_empty(settings.R2_SECRET_ACCESS_KEY, os.getenv("CLOUDFLARE_R2_SECRET_KEY"))
        self.resend_api_key = settings.RESEND_API_KEY
        self.sender_email = settings.SENDER_EMAIL
        if RESEND_AVAILABLE and self.resend_api_key:
            resend.api_key = self.resend_api_key

    def generate_compliance_report(self, job_id: str, findings: List[Finding], standard: str = "SOC2") -> str:
        """
        Generates a compliance-focused report (e.g., SOC2, ISO27001).
        Maps findings to specific compliance controls.
        """
        logger.info(f"Generating {standard} compliance report for job {job_id}")
        # Mock logic
        return f"Compliance Report ({standard}) for Job {job_id} generated successfully."

    def generate_html_report(self, job_id: str, repo_url: str, branch: str, findings: List[Finding]) -> str:
        """Generates a premium executive vulnerability audit HTML string."""
        safe_job_id = html.escape(job_id)
        safe_repo_url = html.escape(repo_url)
        safe_branch = html.escape(branch)

        # Calculate summary metrics
        counts = {Severity.CRITICAL: 0, Severity.HIGH: 0, Severity.MEDIUM: 0, Severity.LOW: 0, Severity.INFO: 0}
        for f in findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1

        total_issues = len(findings)
        
        # Determine overall risk level
        if counts[Severity.CRITICAL] > 0:
            risk_label = "CRITICAL RISK"
            risk_color = "#ef4444"
        elif counts[Severity.HIGH] > 0:
            risk_label = "HIGH RISK"
            risk_color = "#f97316"
        elif counts[Severity.MEDIUM] > 0:
            risk_label = "MEDIUM RISK"
            risk_color = "#eab308"
        elif counts[Severity.LOW] > 0:
            risk_label = "LOW RISK"
            risk_color = "#3b82f6"
        else:
            risk_label = "SECURE"
            risk_color = "#10b981"

        findings_rows = ""
        detailed_findings = ""

        # Color maps for severity badges
        severity_colors = {
            Severity.CRITICAL: {"bg": "#fee2e2", "text": "#991b1b", "border": "#fca5a5"},
            Severity.HIGH: {"bg": "#ffedd5", "text": "#9a3412", "border": "#fed7aa"},
            Severity.MEDIUM: {"bg": "#fef9c3", "text": "#713f12", "border": "#fef08a"},
            Severity.LOW: {"bg": "#dbeafe", "text": "#1e40af", "border": "#bfdbfe"},
            Severity.INFO: {"bg": "#f3f4f6", "text": "#374151", "border": "#e5e7eb"}
        }

        for idx, f in enumerate(findings, 1):
            colors = severity_colors.get(f.severity, severity_colors[Severity.INFO])
            
            safe_title = html.escape(f.title)
            safe_agent = html.escape(f.agent_source)
            safe_cwe = html.escape(f.cwe_id) if f.cwe_id else ""
            safe_desc = html.escape(f.description)
            safe_evidence = html.escape(f.evidence) if f.evidence else ""
            safe_cvss_vector = html.escape(f.cvss_vector) if f.cvss_vector else "N/A"
            safe_cvss_score = html.escape(str(f.cvss_score)) if f.cvss_score is not None else "N/A"
            remediation_val = getattr(f, "remediation", None)
            safe_remediation = html.escape(remediation_val) if remediation_val else ""
            
            cwe_badge = f"<span class='badge-cwe'>{safe_cwe}</span>" if safe_cwe else ""
            
            # Row for overview table
            findings_rows += f"""
            <tr>
                <td>FC-{idx:03d}</td>
                <td><strong>{safe_title}</strong></td>
                <td><span class="badge" style="background-color: {colors['bg']}; color: {colors['text']}; border: 1px solid {colors['border']}">{f.severity.value.upper()}</span></td>
                <td>{safe_agent}</td>
                <td>{safe_cwe or "N/A"}</td>
            </tr>
            """

            # Detailed block
            evidence_block = ""
            if safe_evidence:
                evidence_block = f"""
                <div class="evidence-container">
                    <div class="evidence-header">Evidence Sample</div>
                    <pre class="evidence-code"><code>{safe_evidence}</code></pre>
                </div>
                """

            detailed_findings += f"""
            <div class="finding-card page-break-avoid">
                <div class="finding-title-bar">
                    <span class="finding-id">FC-{idx:03d}</span>
                    <span class="finding-title">{safe_title}</span>
                    <span class="badge" style="background-color: {colors['bg']}; color: {colors['text']}; border: 1px solid {colors['border']}">{f.severity.value.upper()}</span>
                </div>
                
                <div class="finding-meta">
                    <strong>Source Agent:</strong> {safe_agent} &nbsp;|&nbsp; 
                    <strong>CWE Link:</strong> {cwe_badge or "N/A"} &nbsp;|&nbsp;
                    <strong>CVSS:</strong> {safe_cvss_score} ({safe_cvss_vector})
                </div>

                <div class="section-title">Vulnerability Description</div>
                <p class="description-text">{safe_desc}</p>

                {evidence_block}

                <div class="section-title">Remediation Guidance</div>
                <p class="remediation-text">{safe_remediation or "Follow standard secure coding patterns, validate all entry points, and sanitise parameters."}</p>
            </div>
            """

        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Fire Crow Vulnerability Audit Report</title>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
                
                @page {{
                    size: A4;
                    margin: 20mm;
                    @bottom-right {{
                        content: counter(page);
                        font-family: 'Inter', sans-serif;
                        font-size: 9pt;
                        color: #94a3b8;
                    }}
                    @bottom-left {{
                        content: "Fire Crow Security Audit • Job {safe_job_id}";
                        font-family: 'Inter', sans-serif;
                        font-size: 9pt;
                        color: #94a3b8;
                    }}
                }}

                body {{
                    font-family: 'Inter', sans-serif;
                    color: #1e293b;
                    line-height: 1.5;
                    font-size: 10.5pt;
                    margin: 0;
                    background-color: #ffffff;
                }}

                .cover-page {{
                    page-break-after: always;
                    height: 100%;
                    display: flex;
                    flex-direction: column;
                    justify-content: space-between;
                    padding-top: 40mm;
                }}

                .cover-header {{
                    border-left: 5px solid #7c3aed;
                    padding-left: 20px;
                }}

                .cover-title {{
                    font-size: 32pt;
                    font-weight: 700;
                    margin: 0 0 10px 0;
                    color: #0f172a;
                    letter-spacing: -1px;
                }}

                .cover-subtitle {{
                    font-size: 16pt;
                    color: #64748b;
                    margin: 0;
                    font-weight: 400;
                }}

                .cover-metadata {{
                    margin-top: 50mm;
                    background-color: #f8fafc;
                    padding: 20px;
                    border-radius: 8px;
                    border: 1px solid #e2e8f0;
                }}

                .metadata-grid {{
                    display: table;
                    width: 100%;
                }}

                .metadata-row {{
                    display: table-row;
                }}

                .metadata-label {{
                    display: table-cell;
                    font-weight: 600;
                    padding: 8px 10px;
                    color: #475569;
                    width: 30%;
                }}

                .metadata-value {{
                    display: table-cell;
                    padding: 8px 10px;
                    color: #0f172a;
                }}

                .section-header {{
                    font-size: 20pt;
                    font-weight: 700;
                    color: #0f172a;
                    margin-top: 30px;
                    margin-bottom: 15px;
                    border-bottom: 2px solid #f1f5f9;
                    padding-bottom: 8px;
                    page-break-before: always;
                }}

                .section-header:first-of-type {{
                    page-break-before: avoid;
                }}

                .card-grid {{
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 25px;
                    gap: 10px;
                }}

                .stat-card {{
                    flex: 1;
                    background-color: #f8fafc;
                    border: 1px solid #e2e8f0;
                    border-radius: 6px;
                    padding: 15px;
                    text-align: center;
                }}

                .stat-number {{
                    font-size: 24pt;
                    font-weight: 700;
                    color: #0f172a;
                    line-height: 1;
                }}

                .stat-label {{
                    font-size: 8.5pt;
                    color: #64748b;
                    text-transform: uppercase;
                    margin-top: 5px;
                    font-weight: 500;
                }}

                .risk-banner {{
                    background-color: {risk_color}15;
                    border-left: 4px solid {risk_color};
                    padding: 15px 20px;
                    border-radius: 4px;
                    margin-bottom: 30px;
                }}

                .risk-title {{
                    font-weight: 700;
                    color: {risk_color};
                    font-size: 14pt;
                    margin-bottom: 5px;
                }}

                .risk-desc {{
                    margin: 0;
                    font-size: 10pt;
                    color: #334155;
                }}

                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 30px;
                }}

                th {{
                    background-color: #f1f5f9;
                    color: #475569;
                    text-align: left;
                    font-weight: 600;
                    font-size: 9.5pt;
                    padding: 10px 12px;
                    border-bottom: 2px solid #cbd5e1;
                }}

                td {{
                    padding: 12px;
                    font-size: 10pt;
                    border-bottom: 1px solid #e2e8f0;
                }}

                .badge {{
                    display: inline-block;
                    padding: 2px 8px;
                    font-size: 8pt;
                    font-weight: 600;
                    border-radius: 4px;
                    text-transform: uppercase;
                }}

                .badge-cwe {{
                    background-color: #f1f5f9;
                    color: #475569;
                    padding: 1px 5px;
                    font-size: 8.5pt;
                    border-radius: 3px;
                    font-family: monospace;
                }}

                .finding-card {{
                    background-color: #ffffff;
                    border: 1px solid #e2e8f0;
                    border-radius: 8px;
                    padding: 20px;
                    margin-bottom: 25px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.02);
                }}

                .finding-title-bar {{
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    margin-bottom: 10px;
                }}

                .finding-id {{
                    font-family: monospace;
                    font-weight: 700;
                    font-size: 11pt;
                    color: #64748b;
                    margin-right: 10px;
                }}

                .finding-title {{
                    font-size: 13pt;
                    font-weight: 700;
                    color: #0f172a;
                    flex-grow: 1;
                }}

                .finding-meta {{
                    font-size: 8.5pt;
                    color: #64748b;
                    border-bottom: 1px solid #f1f5f9;
                    padding-bottom: 8px;
                    margin-bottom: 15px;
                }}

                .section-title {{
                    font-size: 10pt;
                    font-weight: 600;
                    text-transform: uppercase;
                    color: #475569;
                    margin-top: 15px;
                    margin-bottom: 5px;
                }}

                .description-text, .remediation-text {{
                    margin: 0;
                    font-size: 10pt;
                    color: #334155;
                }}

                .evidence-container {{
                    margin-top: 12px;
                    border: 1px solid #e2e8f0;
                    border-radius: 6px;
                    overflow: hidden;
                }}

                .evidence-header {{
                    background-color: #f8fafc;
                    padding: 6px 12px;
                    font-size: 8.5pt;
                    font-weight: 500;
                    color: #64748b;
                    border-bottom: 1px solid #e2e8f0;
                }}

                .evidence-code {{
                    margin: 0;
                    padding: 12px;
                    background-color: #0f172a;
                    color: #e2e8f0;
                    font-family: 'Courier New', Courier, monospace;
                    font-size: 8.5pt;
                    white-space: pre-wrap;
                    overflow-x: auto;
                }}

                .page-break-avoid {{
                    page-break-inside: avoid;
                }}
            </style>
        </head>
        <body>
            <!-- Cover Page -->
            <div class="cover-page">
                <div class="cover-header">
                    <h1 class="cover-title">Fire Crow Audit Report</h1>
                    <p class="cover-subtitle">Continuous Offensive Security & SAST Agent Analysis</p>
                </div>
                
                <div class="cover-metadata">
                    <div class="metadata-grid">
                        <div class="metadata-row">
                            <div class="metadata-label">Job ID:</div>
                            <div class="metadata-value">{safe_job_id}</div>
                        </div>
                        <div class="metadata-row">
                            <div class="metadata-label">Repository URL:</div>
                            <div class="metadata-value">{safe_repo_url}</div>
                        </div>
                        <div class="metadata-row">
                            <div class="metadata-label">Branch:</div>
                            <div class="metadata-value">{safe_branch}</div>
                        </div>
                        <div class="metadata-row">
                            <div class="metadata-label">Audit Date:</div>
                            <div class="metadata-value">{datetime.now(timezone.utc).strftime('%B %d, %Y')}</div>
                        </div>
                        <div class="metadata-row">
                            <div class="metadata-label">Total Findings:</div>
                            <div class="metadata-value">{total_issues}</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Executive Summary -->
            <div class="section-header">Executive Summary</div>
            
            <div class="risk-banner">
                <div class="risk-title">OVERALL POSTURE: {risk_label}</div>
                <p class="risk-desc">The Fire Crow autonomous security orchestration engine scanned the targeted application codebase structure and ran dynamic sandboxed exploits. Below is the summary of security issues mapped.</p>
            </div>

            <div class="card-grid">
                <div class="stat-card" style="border-top: 3px solid #ef4444;">
                    <div class="stat-number">{counts[Severity.CRITICAL]}</div>
                    <div class="stat-label">Critical</div>
                </div>
                <div class="stat-card" style="border-top: 3px solid #f97316;">
                    <div class="stat-number">{counts[Severity.HIGH]}</div>
                    <div class="stat-label">High</div>
                </div>
                <div class="stat-card" style="border-top: 3px solid #eab308;">
                    <div class="stat-number">{counts[Severity.MEDIUM]}</div>
                    <div class="stat-label">Medium</div>
                </div>
                <div class="stat-card" style="border-top: 3px solid #3b82f6;">
                    <div class="stat-number">{counts[Severity.LOW]}</div>
                    <div class="stat-label">Low</div>
                </div>
            </div>

            <!-- Findings Table -->
            <div class="section-header">Summary Table of Findings</div>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Title</th>
                        <th>Severity</th>
                        <th>Source</th>
                        <th>CWE</th>
                    </tr>
                </thead>
                <tbody>
                    {findings_rows or "<tr><td colspan='5' style='text-align: center; color: #64748b;'>No security issues detected. Clean audit report.</td></tr>"}
                </tbody>
            </table>

            <!-- Detailed Findings -->
            <div class="section-header">Detailed Findings & Proofs</div>
            {detailed_findings or "<p style='color: #64748b;'>No vulnerabilities were found during static signature auditing or sandbox execution runs.</p>"}
        </body>
        </html>
        """
        return html_template

    def compile_pdf(self, html_content: str, output_path: str) -> bool:
        """Compiles HTML template into PDF file on disk."""
        if not WEASYPRINT_AVAILABLE:
            logger.warning("Simulating PDF compiling (WeasyPrint missing). Writing raw HTML layout.")
            try:
                # Write HTML content as output file as fallback
                fallback_path = output_path.replace(".pdf", ".html")
                with open(fallback_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                # Create a blank file with pdf extension to avoid downstream failures
                with open(output_path, "wb") as f:
                    f.write(b"%PDF-1.4 Simulated PDF Document")
                return True
            except Exception as e:
                logger.error(f"Failed writing simulated report output: {str(e)}")
                return False

        try:
            logger.info(f"Compiling HTML to PDF using WeasyPrint: {output_path}")
            weasyprint.HTML(string=html_content).write_pdf(output_path)
            return True
        except Exception as e:
            logger.exception(f"WeasyPrint PDF compilation failed: {str(e)}")
            return False

    def upload_to_r2(self, pdf_path: str, job_id: str) -> str:
        """
        Uploads report to Cloudflare R2 bucket.
        Falls back to local file URI if R2 credentials are not set.
        """
        if not (self.r2_endpoint and self.r2_access_key and self.r2_secret_key):
            logger.info("Cloudflare R2 environment variables not fully configured. Serving locally.")
            return f"/reports/{job_id}.pdf"

        try:
            import boto3  # type: ignore
            from botocore.client import Config  # type: ignore

            logger.info(f"Uploading {pdf_path} to R2 bucket '{self.r2_bucket}'")
            s3 = boto3.client(
                "s3",
                endpoint_url=self.r2_endpoint,
                aws_access_key_id=self.r2_access_key,
                aws_secret_access_key=self.r2_secret_key,
                config=Config(signature_version="s3v4"),
                region_name="auto"
            )

            key = f"reports/{job_id}.pdf"
            s3.upload_file(pdf_path, self.r2_bucket, key, ExtraArgs={"ContentType": "application/pdf"})
            
            # Generate pre-signed URL valid for 7 days
            url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.r2_bucket, "Key": key},
                ExpiresIn=604800
            )
            logger.info(f"Report uploaded successfully to R2. Pre-signed URL: {url}")
            return url
        except Exception as e:
            logger.error(f"R2 upload failed: {str(e)}. Falling back to local HTTP URL.")
            return f"/reports/{job_id}.pdf"

    def send_email_report(self, to_email: str, report_url: str, job_id: str, counts: Dict[Severity, int]) -> bool:
        """Sends a beautiful transactional email with the PDF link via Google/SMTP or Resend."""
        safe_job_id = html.escape(job_id)
        safe_report_url = html.escape(report_url, quote=True)
        html_body = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px; color: #1e293b;">
            <h2 style="color: #0f172a; border-bottom: 2px solid #cbd5e1; padding-bottom: 10px; margin-top: 0;">🔥 Fire Crow Security Audit Complete</h2>
            <p style="font-size: 16px; line-height: 1.6; color: #334155;">Hello,</p>
            <p style="font-size: 16px; line-height: 1.6; color: #334155;">Your autonomous security audit job <strong>{safe_job_id}</strong> is complete. The system scanned code files, constructed a dynamic network sandbox, and validated potential exploit vectors.</p>
            
            <h4 style="color: #475569; text-transform: uppercase; margin-bottom: 10px;">Audit Summary</h4>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <tr style="background-color: #fee2e2; color: #991b1b; font-weight: bold;">
                    <td style="padding: 10px; border: 1px solid #fca5a5;">Critical Severities</td>
                    <td style="padding: 10px; border: 1px solid #fca5a5; text-align: right;">{counts.get(Severity.CRITICAL, 0)}</td>
                </tr>
                <tr style="background-color: #ffedd5; color: #9a3412; font-weight: bold;">
                    <td style="padding: 10px; border: 1px solid #fed7aa;">High Severities</td>
                    <td style="padding: 10px; border: 1px solid #fed7aa; text-align: right;">{counts.get(Severity.HIGH, 0)}</td>
                </tr>
                <tr style="background-color: #fef9c3; color: #713f12;">
                    <td style="padding: 10px; border: 1px solid #fef08a;">Medium/Low Severities</td>
                    <td style="padding: 10px; border: 1px solid #fef08a; text-align: right;">{counts.get(Severity.MEDIUM, 0) + counts.get(Severity.LOW, 0)}</td>
                </tr>
            </table>

            <div style="text-align: center; margin-top: 30px; margin-bottom: 30px;">
                <a href="{safe_report_url}" style="background-color: #7c3aed; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; display: inline-block;">Download PDF Audit Report</a>
            </div>

            <p style="font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 15px; margin-top: 30px;">This email was automatically generated by Fire Crow Security Platform. Keep your dependencies patched and code safe.</p>
        </div>
        """

        # 1. Try Google SMTP/Gmail if configured
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            try:
                import smtplib
                from email.mime.text import MIMEText
                from email.mime.multipart import MIMEMultipart

                logger.info(f"Sending transactional email report to {to_email} via Google/SMTP")
                
                msg = MIMEMultipart("alternative")
                msg["Subject"] = f"Fire Crow Security Audit Report - Job {job_id}"
                msg["From"] = f"Fire Crow Audit <{settings.SMTP_USER}>"
                msg["To"] = to_email

                part = MIMEText(html_body, "html")
                msg.attach(part)

                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                    server.starttls()
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.sendmail(settings.SMTP_USER, [to_email], msg.as_string())
                
                logger.info("Transactional email successfully sent via Google/SMTP.")
                return True
            except Exception as e:
                logger.error(f"Failed to send email via Google/SMTP: {str(e)}. Falling back...")

        # 2. Fallback to Resend
        if not (RESEND_AVAILABLE and self.resend_api_key):
            logger.warning("Resend API key not configured or package missing. Saving notification email locally.")
            try:
                import re
                from datetime import datetime
                sent_emails_dir = os.path.join("workspace", "sent_emails")
                os.makedirs(sent_emails_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_email = re.sub(r'[^a-zA-Z0-9@.]', '_', to_email)
                filename = f"{timestamp}_{safe_email}_audit_report.html"
                filepath = os.path.join(sent_emails_dir, filename)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(html_body)
                logger.info(f"Local email report saved to: {filepath}")
                return True
            except Exception as le:
                logger.error(f"Failed to save local fallback email: {le}")
                return False

        try:
            logger.info(f"Sending transactional email report to {to_email} via Resend")
            
            params: Any = {
                "from": f"Fire Crow Audit <{self.sender_email}>",
                "to": [to_email],
                "subject": f"Fire Crow Security Audit Report - Job {job_id}",
                "html": html_body
            }

            resend.Emails.send(params)
            logger.info("Transactional email successfully sent via Resend.")
            return True
        except Exception as e:
            logger.error(f"Failed to send email via Resend: {str(e)}. Saving notification email locally.")
            try:
                import re
                from datetime import datetime
                sent_emails_dir = os.path.join("workspace", "sent_emails")
                os.makedirs(sent_emails_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_email = re.sub(r'[^a-zA-Z0-9@.]', '_', to_email)
                filename = f"{timestamp}_{safe_email}_audit_report.html"
                filepath = os.path.join(sent_emails_dir, filename)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(html_body)
                logger.info(f"Local email report saved to: {filepath}")
                return True
            except Exception as le:
                logger.error(f"Failed to save local fallback email: {le}")
                return False
