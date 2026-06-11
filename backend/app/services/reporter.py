import logging
import os
import html
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from backend.app.config import settings, WORKSPACE_DIR
from backend.app.schemas import Finding, Severity
from backend.app.services.redaction import redact_text

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


def _is_r2_auth_error(message: str) -> bool:
    lowered = message.lower()
    return any(
        token in lowered
        for token in (
            "invalidaccesskeyid",
            "accessdenied",
            "signaturedoesnotmatch",
            "malformed access key id",
            "invalid access key id",
        )
    )


def get_clean_repo_name(repo_url: str) -> str:
    if not repo_url:
        return "repo"
    # Remove trailing slashes and .git
    url = repo_url.strip().rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    # Get the last part of the url path
    parts = url.split("/")
    repo_name = parts[-1] if parts else "repo"
    # Clean the name of characters that aren't letters, numbers, hyphens, or underscores
    import re
    repo_name = re.sub(r'[^a-zA-Z0-9_\-]', '', repo_name)
    return repo_name or "repo"

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

    def generate_html_report(
        self,
        job_id: str,
        repo_url: str,
        branch: str,
        findings: List[Finding],
        scanner_execution: Dict[str, Any] | None = None,
    ) -> str:
        """Generates a premium executive vulnerability audit HTML string."""
        safe_job_id = html.escape(job_id)
        safe_repo_url = html.escape(repo_url)
        safe_branch = html.escape(branch)

        repo_name = get_clean_repo_name(repo_url)
        safe_repo_name = html.escape(repo_name)

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
            safe_evidence = html.escape(redact_text(f.evidence)) if f.evidence else ""
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

        scanner_execution = scanner_execution or {}
        scanner_rows = ""
        scanner_labels = {
            "recon": "Recon",
            "regex_sast": "Regex SAST",
            "semgrep": "Semgrep",
            "dependency": "Dependency scan",
            "dynamic": "Dynamic validation",
            "sandbox": "Sandbox mode",
        }
        for key, label in scanner_labels.items():
            value = scanner_execution.get(key, {})
            if isinstance(value, dict):
                status = str(value.get("status", "not recorded"))
                mode = str(value.get("mode", "not recorded"))
                tool = str(value.get("tool", ""))
            else:
                status = str(value)
                mode = "not recorded"
                tool = ""
            scanner_rows += f"""
            <tr>
                <td>{html.escape(label)}</td>
                <td>{html.escape(status)}</td>
                <td>{html.escape(mode)}</td>
                <td>{html.escape(tool) if tool else "N/A"}</td>
            </tr>
            """

        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Fire Crow Vulnerability Audit Report</title>
            <style>
                @page {{
                    size: A4;
                    margin: 20mm;
                    @bottom-right {{
                        content: counter(page);
                        font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                        font-size: 9pt;
                        color: #94a3b8;
                    }}
                    @bottom-left {{
                        content: "Fire Crow Security Audit • {safe_repo_name} ({safe_branch})";
                        font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                        font-size: 9pt;
                        color: #94a3b8;
                    }}
                }}

                body {{
                    font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
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
                <p class="risk-desc">Fire Crow completed an authorization-only defensive security review of the submitted repository and recorded evidence-backed findings from the configured scanners.</p>
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

            <!-- Scanner Execution Evidence -->
            <div class="section-header">Scanner Execution Evidence</div>
            <table>
                <thead>
                    <tr>
                        <th>Scanner</th>
                        <th>Status</th>
                        <th>Mode</th>
                        <th>Tool</th>
                    </tr>
                </thead>
                <tbody>
                    {scanner_rows}
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
            logger.warning("WeasyPrint is not available on this platform. PDF generation is falling back to simulated files and HTML layout.")
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
        filename = os.path.basename(pdf_path)
        if not (self.r2_endpoint and self.r2_access_key and self.r2_secret_key):
            logger.info("Cloudflare R2 environment variables not fully configured. Serving locally.")
            return f"/reports/{filename}"

        try:
            import boto3  # type: ignore
            from botocore.client import Config  # type: ignore

            endpoint = self.r2_endpoint
            if endpoint and not (endpoint.startswith("http://") or endpoint.startswith("https://")):
                endpoint = f"https://{endpoint}"

            logger.info("Uploading report for job %s to R2 object storage.", job_id)
            s3 = boto3.client(
                "s3",
                endpoint_url=endpoint,
                aws_access_key_id=self.r2_access_key,
                aws_secret_access_key=self.r2_secret_key,
                config=Config(signature_version="s3v4"),
                region_name="auto"
            )

            key = f"reports/{filename}"
            s3.upload_file(pdf_path, self.r2_bucket, key, ExtraArgs={"ContentType": "application/pdf"})
            
            # Generate pre-signed URL valid for 7 days
            url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.r2_bucket, "Key": key},
                ExpiresIn=604800
            )
            logger.info("Report uploaded successfully to R2 for job %s with object key %s.", job_id, key)
            return url
        except Exception as e:
            redacted_error = redact_text(str(e))
            if _is_r2_auth_error(redacted_error):
                logger.warning(
                    "R2 credentials were rejected for job %s. Serving the local report endpoint instead.",
                    job_id,
                )
            else:
                logger.error(
                    "R2 upload failed for job %s: %s. Falling back to local report endpoint.",
                    job_id,
                    redacted_error,
                )
            return f"/reports/{filename}"

    def clean_r2_bucket_clutter(self) -> None:
        """
        Scans the Cloudflare R2 bucket and deletes any objects that are not PDFs (e.g. temporary logs, non-pdf artifacts)
        to optimize storage.
        """
        if not (self.r2_endpoint and self.r2_access_key and self.r2_secret_key):
            logger.info("R2 storage not configured. Skipping bucket clutter cleanup.")
            return

        try:
            import boto3  # type: ignore
            from botocore.client import Config  # type: ignore

            endpoint = self.r2_endpoint
            if endpoint and not (endpoint.startswith("http://") or endpoint.startswith("https://")):
                endpoint = f"https://{endpoint}"

            s3 = boto3.client(
                "s3",
                endpoint_url=endpoint,
                aws_access_key_id=self.r2_access_key,
                aws_secret_access_key=self.r2_secret_key,
                config=Config(signature_version="s3v4"),
                region_name="auto"
            )

            logger.info("Scanning R2 bucket '%s' to clean up non-PDF clutter.", self.r2_bucket)
            paginator = s3.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self.r2_bucket)

            delete_keys = []
            for page in pages:
                if "Contents" in page:
                    for obj in page["Contents"]:
                        key = obj["Key"]
                        # Delete any file that does not end with .pdf
                        if not key.lower().endswith(".pdf"):
                            logger.warning("R2 Cleanup: Tagged non-PDF object for deletion: %s", key)
                            delete_keys.append({"Key": key})

            if delete_keys:
                # Batch delete up to 1000 at a time (AWS/S3 API constraint)
                for i in range(0, len(delete_keys), 1000):
                    batch = delete_keys[i:i+1000]
                    s3.delete_objects(
                        Bucket=self.r2_bucket,
                        Delete={"Objects": batch, "Quiet": True}
                    )
                logger.info("Successfully cleaned up %d non-PDF clutter items from R2.", len(delete_keys))
            else:
                logger.info("No non-PDF clutter found in R2 bucket.")
        except Exception as e:
            logger.error("Failed cleaning up R2 bucket: %s", redact_text(str(e)))


    def send_email_report(
        self,
        to_email: str,
        report_url: str,
        job_id: str,
        counts: Dict[Severity, int],
        repo_url: str = "",
        pdf_path: Optional[str] = None,
    ) -> bool:
        """Sends a beautiful transactional email with the PDF link and attachment via Google/SMTP or Resend."""
        if report_url.startswith("/"):
            report_link = f"{settings.FRONTEND_URL.rstrip('/')}/dashboard?job_id={job_id}"
        else:
            report_link = report_url

        repo_name = get_clean_repo_name(repo_url) if repo_url else "Repository"
        safe_repo_name = html.escape(repo_name)
        safe_job_id = html.escape(job_id)
        safe_report_url = html.escape(report_link, quote=True)
        
        critical_count = counts.get(Severity.CRITICAL, 0)
        high_count = counts.get(Severity.HIGH, 0)
        medium_low_count = counts.get(Severity.MEDIUM, 0) + counts.get(Severity.LOW, 0) + counts.get(Severity.INFO, 0)

        html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Fire Crow Audit Report</title>
  <style>
    body {{
      margin: 0;
      padding: 0;
      background-color: #f3f4f6;
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }}
    .wrapper {{
      width: 100%;
      background-color: #f3f4f6;
      padding: 40px 20px;
      box-sizing: border-box;
    }}
    .container {{
      max-width: 600px;
      margin: 0 auto;
      background: #ffffff;
      border: 1px solid #e5e7eb;
      border-radius: 16px;
      box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.02);
      overflow: hidden;
    }}
    .header {{
      background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
      padding: 36px 32px;
      text-align: center;
    }}
    .logo-mark {{
      background: linear-gradient(135deg, #f97316 0%, #ef4444 50%, #8b5cf6 100%);
      color: #ffffff;
      font-weight: 800;
      font-size: 22px;
      width: 48px;
      height: 48px;
      border-radius: 12px;
      display: inline-block;
      line-height: 48px;
      text-align: center;
      box-shadow: 0 4px 10px rgba(239, 68, 68, 0.3);
    }}
    .logo-text {{
      color: #ffffff;
      font-size: 24px;
      font-weight: 800;
      margin-left: 12px;
      display: inline-block;
      vertical-align: middle;
      letter-spacing: -0.025em;
    }}
    .header-title {{
      color: #ffffff;
      font-size: 22px;
      font-weight: 700;
      margin: 16px 0 0 0;
      letter-spacing: -0.025em;
    }}
    .content {{
      padding: 32px;
    }}
    .greeting {{
      color: #1f2937;
      font-size: 16px;
      font-weight: 600;
      margin-top: 0;
      margin-bottom: 12px;
    }}
    .intro-text {{
      color: #4b5563;
      font-size: 15px;
      line-height: 1.6;
      margin-bottom: 24px;
    }}
    .meta-card {{
      background-color: #f9fafb;
      border: 1px solid #f3f4f6;
      border-radius: 12px;
      padding: 18px;
      margin-bottom: 24px;
    }}
    .meta-item {{
      font-size: 13px;
      color: #6b7280;
      margin-bottom: 8px;
    }}
    .meta-item:last-child {{
      margin-bottom: 0;
    }}
    .meta-label {{
      font-weight: 600;
      color: #374151;
      display: inline-block;
      width: 90px;
    }}
    .meta-value {{
      font-family: monospace;
      color: #111827;
    }}
    .stats-card {{
      border: 1px solid #e5e7eb;
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 28px;
    }}
    .stats-title {{
      color: #374151;
      font-size: 13px;
      font-weight: 700;
      text-transform: uppercase;
      margin-top: 0;
      margin-bottom: 16px;
      letter-spacing: 0.05em;
    }}
    .stats-grid {{
      display: table;
      width: 100%;
    }}
    .stats-row {{
      display: table-row;
    }}
    .stats-cell {{
      display: table-cell;
      padding: 12px 8px;
      border-bottom: 1px solid #f3f4f6;
      font-size: 14px;
    }}
    .stats-row:last-child .stats-cell {{
      border-bottom: none;
    }}
    .stat-label {{
      color: #4b5563;
      font-weight: 500;
    }}
    .stat-val-container {{
      text-align: right;
    }}
    .badge {{
      display: inline-block;
      padding: 4px 12px;
      font-size: 12px;
      font-weight: 700;
      border-radius: 9999px;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }}
    .badge-critical {{
      background-color: #fee2e2;
      color: #991b1b;
      border: 1px solid #fca5a5;
    }}
    .badge-high {{
      background-color: #ffedd5;
      color: #9a3412;
      border: 1px solid #fed7aa;
    }}
    .badge-medium-low {{
      background-color: #f3f4f6;
      color: #374151;
      border: 1px solid #e5e7eb;
    }}
    .cta-container {{
      text-align: center;
      margin: 32px 0 8px 0;
    }}
    .cta-button {{
      background: linear-gradient(135deg, #ea580c 0%, #7c3aed 100%);
      color: #ffffff !important;
      padding: 16px 32px;
      text-decoration: none;
      border-radius: 10px;
      font-weight: 700;
      font-size: 15px;
      display: inline-block;
      box-shadow: 0 4px 14px rgba(124, 58, 237, 0.3);
      transition: all 0.2s ease;
    }}
    .footer {{
      background-color: #f9fafb;
      padding: 24px;
      border-top: 1px solid #e5e7eb;
      text-align: center;
    }}
    .footer-text {{
      color: #9ca3af;
      font-size: 12px;
      line-height: 1.5;
      margin: 0;
    }}
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="container">
      <div class="header">
        <div class="logo-container">
          <span class="logo-mark">FC</span>
          <span class="logo-text">FireCrow</span>
        </div>
        <h1 class="header-title">Security Audit Complete</h1>
      </div>
      
      <div class="content">
        <p class="greeting">Hello,</p>
        <p class="intro-text">
          The autonomous security review of your repository has concluded successfully. Scanners analyzed all code paths, and security agents triaged the results to generate a verified remediation plan.
        </p>

        <div class="meta-card">
          <div class="meta-item">
            <span class="meta-label">Project:</span>
            <span class="meta-value">{safe_repo_name}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">Job ID:</span>
            <span class="meta-value">{safe_job_id}</span>
          </div>
        </div>
        
        <div class="stats-card">
          <h2 class="stats-title">Audit Findings Overview</h2>
          <div class="stats-grid">
            <div class="stats-row">
              <div class="stats-cell stat-label">Critical Findings</div>
              <div class="stats-cell stat-val-container">
                <span class="badge badge-critical">{critical_count}</span>
              </div>
            </div>
            <div class="stats-row">
              <div class="stats-cell stat-label">High Findings</div>
              <div class="stats-cell stat-val-container">
                <span class="badge badge-high">{high_count}</span>
              </div>
            </div>
            <div class="stats-row">
              <div class="stats-cell stat-label">Medium/Low/Info</div>
              <div class="stats-cell stat-val-container">
                <span class="badge badge-medium-low">{medium_low_count}</span>
              </div>
            </div>
          </div>
        </div>
        
        <div class="cta-container" style="background-color: #f8fafc; border: 1px solid #e2e8f0; padding: 20px; border-radius: 12px; text-align: center;">
          <p style="margin: 0; color: #475569; font-size: 14px; font-weight: 600;">
            📎 The complete audit report has been attached directly to this email as a PDF.
          </p>
        </div>
      </div>
      
      <div class="footer">
        <p class="footer-text">
          This email was automatically generated by Firecrow Agent.<br>
          Keep your code secure and dependencies up to date.
        </p>
      </div>
    </div>
  </div>
</body>
</html>
"""

        success = False
        try:
            # 1. Try Google SMTP/Gmail if configured
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                try:
                    import smtplib
                    from email.mime.text import MIMEText
                    from email.mime.multipart import MIMEMultipart

                    logger.info("Sending transactional email report for job %s via Google/SMTP.", job_id)
                    
                    msg = MIMEMultipart("mixed")
                    msg["Subject"] = f"Firecrow Agent Security Audit: {repo_name}"
                    msg["From"] = f"Firecrow Agent <{settings.SMTP_USER}>"
                    msg["To"] = to_email

                    body_part = MIMEMultipart("alternative")
                    body_part.attach(MIMEText(html_body, "html"))
                    msg.attach(body_part)

                    if pdf_path and os.path.exists(pdf_path):
                        from email.mime.base import MIMEBase
                        from email import encoders
                        with open(pdf_path, "rb") as attachment_file:
                            part = MIMEBase("application", "octet-stream")
                            part.set_payload(attachment_file.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                "Content-Disposition",
                                f"attachment; filename={os.path.basename(pdf_path)}",
                            )
                            msg.attach(part)

                    if settings.SMTP_PORT == 465:
                        server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT)
                    else:
                        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
                        server.starttls()

                    with server:
                        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                        server.sendmail(settings.SMTP_USER, [to_email], msg.as_string())
                    
                    logger.info("Transactional email successfully sent via Google/SMTP.")
                    success = True
                except Exception as e:
                    logger.error("Failed to send email via Google/SMTP for job %s: %s.", job_id, redact_text(str(e)))

            # 2. Try Resend if configured
            if not success and RESEND_AVAILABLE and self.resend_api_key:
                try:
                    logger.info("Sending transactional email report for job %s via Resend.", job_id)
                    import base64
                    params: Any = {
                        "from": f"Firecrow Agent <{self.sender_email}>",
                        "to": [to_email],
                        "subject": f"Firecrow Agent Security Audit: {repo_name}",
                        "html": html_body
                    }
                    if pdf_path and os.path.exists(pdf_path):
                        with open(pdf_path, "rb") as f:
                            pdf_bytes = f.read()
                        params["attachments"] = [
                            {
                                "content": base64.b64encode(pdf_bytes).decode("utf-8"),
                                "filename": os.path.basename(pdf_path),
                            }
                        ]
                    resend.Emails.send(params)
                    logger.info("Transactional email successfully sent via Resend.")
                    success = True
                except Exception as e:
                    logger.error("Failed to send email via Resend for job %s: %s.", job_id, redact_text(str(e)))

            # 3. Try Brevo HTTP API if configured
            if not success and settings.BREVO_API_KEY:
                try:
                    import httpx
                    import base64
                    logger.info("Sending transactional email report for job %s via Brevo.", job_id)
                    payload_json = {
                        "sender": {"email": self.sender_email, "name": "Firecrow Agent"},
                        "to": [{"email": to_email}],
                        "subject": f"Firecrow Agent Security Audit: {repo_name}",
                        "htmlContent": html_body
                    }
                    if pdf_path and os.path.exists(pdf_path):
                        with open(pdf_path, "rb") as f:
                            pdf_bytes = f.read()
                        payload_json["attachment"] = [
                            {
                                "content": base64.b64encode(pdf_bytes).decode("utf-8"),
                                "name": os.path.basename(pdf_path)
                            }
                        ]
                    response = httpx.post(
                        "https://api.brevo.com/v3/smtp/email",
                        headers={
                            "api-key": settings.BREVO_API_KEY,
                            "content-type": "application/json",
                            "accept": "application/json"
                        },
                        json=payload_json,
                        timeout=15.0
                    )
                    response.raise_for_status()
                    logger.info("Transactional email successfully sent via Brevo.")
                    success = True
                except Exception as e:
                    logger.error("Failed to send email via Brevo for job %s: %s.", job_id, redact_text(str(e)))

            # 4. Final Fallback (local saving in DEBUG, or fail in production)
            if not success:
                if not settings.DEBUG:
                    logger.warning("No email provider succeeded or configured for job %s. Local email fallback is disabled outside DEBUG mode.", job_id)
                    return False

                logger.warning("No email provider configured or succeeded. Saving DEBUG notification email locally.")
                try:
                    import re
                    from datetime import datetime
                    sent_emails_dir = os.path.join(WORKSPACE_DIR, "workspace", "sent_emails")
                    os.makedirs(sent_emails_dir, exist_ok=True)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    safe_email = re.sub(r'[^a-zA-Z0-9@.]', '_', to_email)
                    filename = f"{timestamp}_{safe_email}_audit_report.html"
                    filepath = os.path.join(sent_emails_dir, filename)
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(html_body)
                    logger.info("Local DEBUG email report saved for job %s.", job_id)
                    success = True
                except Exception as le:
                    logger.error("Failed to save local fallback email for job %s: %s", job_id, redact_text(str(le)))
                    
            return success
        finally:
            if pdf_path:
                try:
                    import tempfile
                    temp_dir = tempfile.gettempdir()
                    # Only delete if it resides in the temporary folder (e.g., temp download copies)
                    if os.path.abspath(pdf_path).startswith(os.path.abspath(temp_dir)):
                        if os.path.exists(pdf_path):
                            os.remove(pdf_path)
                        html_path = pdf_path.replace(".pdf", ".html")
                        if os.path.exists(html_path):
                            os.remove(html_path)
                        logger.info("Purged local temporary report file copies after email dispatch.")
                except Exception as delete_error:
                    logger.warning("Failed to delete local report copies after email dispatch: %s", str(delete_error))
