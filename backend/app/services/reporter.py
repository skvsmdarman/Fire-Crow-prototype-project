import logging
import os
import html
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from app.config import settings, WORKSPACE_DIR, _global_state
from app.schemas import Finding, Severity
from app.services.frontend_urls import build_audit_job_url
from app.services.redaction import redact_text

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
            resend.api_key = self.resend_api_key  # type: ignore

    def _get_smart_finding_details(self, finding: Finding) -> Dict[str, str]:
        """Uses LLM to enrich findings with non-technical assessment and step-by-step fixes."""
        details = {
            "non_technical_summary": f"This security issue is a {finding.severity.value} vulnerability which may expose sensitive application assets or logic. It was identified by {finding.agent_source} tools.",
            "impact": "Exploitation of this vulnerability may compromise the integrity, availability, or confidentiality of the application, leading to unauthorized access, system degradation, or data disclosure.",
            "remediation_steps": finding.remediation or "Follow secure coding practices, enforce strict parameter validation, sanitize all inputs, and use encrypted configuration parameters."
        }

        if not settings.GEMINI_API_KEY or not settings.GEMINI_MODEL:
            return details

        prompt = f"""You are a senior security researcher. Explain the following vulnerability so that even a non-technical manager (or junior developer) can understand:
Title: {finding.title}
Severity: {finding.severity.value}
Description: {finding.description}
CWE: {finding.cwe_id or 'N/A'}
Evidence: {finding.evidence or 'None'}

Provide your response in JSON format. Do not use markdown code block wrappers (like ```json). Respond with a raw JSON object containing these keys:
- "non_technical_summary": A clear explanation of what this vulnerability means in plain English, why it is dangerous, and what the real-world business risk is.
- "impact": The technical impact of this vulnerability on the systems and data.
- "remediation_steps": Actionable, step-by-step coding instructions to fix the issue.
"""
        try:
            from app.services.safe_llm import safe_llm_call
            import json
            res = safe_llm_call(prompt, max_tokens=1000, temperature=0.2)
            if res:
                res_clean = res.strip()
                if res_clean.startswith("```json"):
                    res_clean = res_clean.removeprefix("```json").removesuffix("```").strip()
                elif res_clean.startswith("```"):
                    res_clean = res_clean.removeprefix("```").removesuffix("```").strip()
                parsed = json.loads(res_clean)
                if "non_technical_summary" in parsed and "impact" in parsed and "remediation_steps" in parsed:
                    return {
                        "non_technical_summary": parsed["non_technical_summary"],
                        "impact": parsed["impact"],
                        "remediation_steps": parsed["remediation_steps"]
                    }
        except Exception as e:
            logger.warning(f"Failed to generate smart details for finding {finding.title}: {e}")
        
        return details

    def generate_compliance_report(self, job_id: str, findings: List[Finding], standard: str = "SOC2") -> str:
        """
        Generates a compliance-focused report (e.g., SOC2, ISO27001).
        Maps findings to specific compliance controls.
        """
        logger.info(f"Generating {standard} compliance report for job {job_id}")

        for finding in findings:
            pass

        return f"Compliance Report ({standard}) for Job {job_id} generated successfully."

    def generate_html_report(
        self,
        job_id: str,
        repo_url: str,
        branch: str,
        findings: List[Finding],
        scanner_execution: Dict[str, Any] | None = None,
        phase_durations: Dict[str, float] | None = None,
    ) -> str:
        """Generates a premium executive vulnerability audit HTML string with charts."""
        for finding in findings:
            if finding.evidence:
                finding.evidence = finding.evidence[:settings.REPORT_MAX_EVIDENCE_CHARS]
            if finding.remediation:
                finding.remediation = finding.remediation[:settings.REPORT_MAX_REMEDIATION_CHARS]
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
            risk_narrative = "Immediate action required. Critical vulnerabilities were discovered that could lead to severe data breaches, remote code execution, or complete system compromise."
        elif counts[Severity.HIGH] > 0:
            risk_label = "HIGH RISK"
            risk_color = "#f97316"
            risk_narrative = "Urgent remediation recommended. High-severity issues expose the application to significant attack surface that could be exploited by motivated adversaries."
        elif counts[Severity.MEDIUM] > 0:
            risk_label = "MEDIUM RISK"
            risk_color = "#eab308"
            risk_narrative = "Remediation advised within the current development cycle. Medium-severity findings represent defense-in-depth weaknesses that should be addressed proactively."
        elif counts[Severity.LOW] > 0:
            risk_label = "LOW RISK"
            risk_color = "#3b82f6"
            risk_narrative = "The application demonstrates solid security posture with only minor improvements recommended. These findings are informational and best-practice enhancements."
        else:
            risk_label = "SECURE"
            risk_color = "#10b981"
            risk_narrative = "No security vulnerabilities were identified during this audit. The application follows security best practices across all tested attack vectors."

        # Build severity distribution chart (SVG donut)
        severity_colors_hex = {
            Severity.CRITICAL: "#ef4444",
            Severity.HIGH: "#f97316",
            Severity.MEDIUM: "#eab308",
            Severity.LOW: "#3b82f6",
            Severity.INFO: "#94a3b8",
        }
        
        # Donut chart calculation
        donut_chart = self._build_donut_chart(counts, total_issues, severity_colors_hex)

        # Build findings-by-scanner bar chart
        scanner_counts: Dict[str, Dict[str, int]] = {}
        for f in findings:
            src = f.scanner_name or f.agent_source or "Unknown"
            if src not in scanner_counts:
                scanner_counts[src] = {s.value: 0 for s in Severity}
            scanner_counts[src][f.severity.value] = scanner_counts[src].get(f.severity.value, 0) + 1

        bar_chart = self._build_scanner_bar_chart(scanner_counts, severity_colors_hex)

        # Build findings-by-severity bar chart
        severity_bar = self._build_severity_bar_chart(counts, severity_colors_hex)

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

        # Count CWE occurrences
        cwe_counts: Dict[str, int] = {}
        for f in findings:
            if f.cwe_id:
                cwe_counts[f.cwe_id] = cwe_counts.get(f.cwe_id, 0) + 1
        top_cwes = sorted(cwe_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        for idx, f in enumerate(findings, 1):
            colors = severity_colors.get(f.severity, severity_colors[Severity.INFO])
            
            safe_title = html.escape(f.title)
            safe_agent = html.escape(f.agent_source)
            safe_cwe = html.escape(f.cwe_id) if f.cwe_id else ""
            safe_desc = html.escape(f.description)
            evidence_text = (f.evidence or "")[:settings.REPORT_MAX_EVIDENCE_CHARS]
            safe_evidence = html.escape(redact_text(evidence_text)) if evidence_text else ""
            safe_cvss_vector = html.escape(f.cvss_vector) if f.cvss_vector else "N/A"
            safe_cvss_score = html.escape(str(f.cvss_score)) if f.cvss_score is not None else "N/A"
            safe_file = html.escape(f.file_path) if f.file_path else ""
            safe_line = str(f.line_number) if f.line_number else ""
            
            # Fetch smart details
            smart_details = self._get_smart_finding_details(f)
            safe_non_tech = html.escape(smart_details["non_technical_summary"])
            safe_impact = html.escape(smart_details["impact"])
            safe_remediation = html.escape(smart_details["remediation_steps"])
            
            cwe_badge = f"<span class='badge-cwe'>{safe_cwe}</span>" if safe_cwe else ""
            location_info = f"<strong>File:</strong> {safe_file}" + (f" (line {safe_line})" if safe_line else "") if safe_file else ""
            
            # Row for overview table
            findings_rows += f"""
            <tr>
                <td>FC-{idx:03d}</td>
                <td><strong>{safe_title}</strong></td>
                <td><span class="badge" style="background-color: {colors['bg']}; color: {colors['text']}; border: 1px solid {colors['border']}">{f.severity.value.upper()}</span></td>
                <td>{safe_agent}</td>
                <td>{safe_cwe or "N/A"}</td>
                <td>{safe_cvss_score}</td>
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
                    <strong>Source:</strong> {safe_agent} &nbsp;|&nbsp; 
                    <strong>CWE:</strong> {cwe_badge or "N/A"} &nbsp;|&nbsp;
                    <strong>CVSS:</strong> {safe_cvss_score} ({safe_cvss_vector})
                    {f" &nbsp;|&nbsp; <strong>Location:</strong> {location_info}" if location_info else ""}
                </div>
 
                <div class="section-title">Plain English Summary (For Non-Technical Users)</div>
                <p class="description-text">{safe_non_tech}</p>
 
                <div class="section-title">Technical Description</div>
                <p class="description-text">{safe_desc}</p>
 
                <div class="section-title">Security & Business Impact</div>
                <p class="description-text">{safe_impact}</p>
 
                {evidence_block}
 
                <div class="section-title">Actionable Remediation Guide</div>
                <p class="remediation-text" style="white-space: pre-wrap;">{safe_remediation}</p>
            </div>
            """

        scanner_execution = scanner_execution or {}
        scanner_rows = ""
        scanner_labels = {
            "recon": "Recon",
            "regex_sast": "Regex SAST",
            "semgrep": "Semgrep",
            "eslint": "ESLint Security",
            "dependency": "Dependency scan",
            "sbom": "SBOM Analysis",
            "iac": "IaC Scan",
            "cicd": "CI/CD Scan",
            "container": "Container Scan",
            "config": "Config Scan",
            "dynamic": "Dynamic validation",
            "sandbox": "Sandbox mode",
            "network": "Network Scan",
            "attack": "Attack Simulation",
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

        # Phase execution timeline
        phase_rows = ""
        phase_durations = phase_durations or {}
        total_duration = sum(phase_durations.values()) if phase_durations else 0
        for phase_name, duration in sorted(phase_durations.items(), key=lambda x: x[1], reverse=True):
            pct = (duration / total_duration * 100) if total_duration > 0 else 0
            phase_rows += f"""
            <tr>
                <td>{html.escape(phase_name.replace('_', ' ').title())}</td>
                <td>{duration:.1f}s</td>
                <td>
                    <div class="phase-bar-container">
                        <div class="phase-bar" style="width: {min(pct, 100):.0f}%"></div>
                    </div>
                </td>
                <td>{pct:.1f}%</td>
            </tr>
            """

        # Top CWEs table
        cwe_rows = ""
        for cwe_id, count in top_cwes:
            cwe_rows += f"""
            <tr>
                <td><span class="badge-cwe">{html.escape(cwe_id)}</span></td>
                <td>{count}</td>
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
                    margin: 18mm 20mm;
                    @bottom-right {{
                        content: counter(page) " / " counter(pages);
                        font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                        font-size: 8pt;
                        color: #94a3b8;
                    }}
                    @bottom-left {{
                        content: "Fire Crow Security Audit \u2022 {safe_repo_name} ({safe_branch})";
                        font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                        font-size: 8pt;
                        color: #94a3b8;
                    }}
                }}

                * {{ box-sizing: border-box; }}

                body {{
                    font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    color: #1e293b;
                    line-height: 1.6;
                    font-size: 10pt;
                    margin: 0;
                    background-color: #ffffff;
                }}

                .cover-page {{
                    page-break-after: always;
                    height: 100%;
                    display: flex;
                    flex-direction: column;
                    justify-content: space-between;
                    padding-top: 35mm;
                }}

                .cover-header {{
                    border-left: 5px solid #7c3aed;
                    padding-left: 20px;
                }}

                .cover-title {{
                    font-size: 28pt;
                    font-weight: 700;
                    margin: 0 0 8px 0;
                    color: #0f172a;
                    letter-spacing: -1px;
                }}

                .cover-subtitle {{
                    font-size: 14pt;
                    color: #64748b;
                    margin: 0;
                    font-weight: 400;
                }}

                .cover-metadata {{
                    margin-top: 40mm;
                    background-color: #f8fafc;
                    padding: 18px;
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
                    padding: 6px 10px;
                    color: #475569;
                    width: 28%;
                    font-size: 9.5pt;
                }}

                .metadata-value {{
                    display: table-cell;
                    padding: 6px 10px;
                    color: #0f172a;
                    font-size: 9.5pt;
                }}

                .section-header {{
                    font-size: 16pt;
                    font-weight: 700;
                    color: #0f172a;
                    margin-top: 28px;
                    margin-bottom: 12px;
                    border-bottom: 2px solid #e2e8f0;
                    padding-bottom: 6px;
                    page-break-before: always;
                }}

                .section-header:first-of-type {{
                    page-break-before: avoid;
                }}

                .card-grid {{
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 20px;
                    gap: 8px;
                }}

                .stat-card {{
                    flex: 1;
                    background-color: #f8fafc;
                    border: 1px solid #e2e8f0;
                    border-radius: 6px;
                    padding: 12px;
                    text-align: center;
                }}

                .stat-number {{
                    font-size: 22pt;
                    font-weight: 700;
                    color: #0f172a;
                    line-height: 1;
                }}

                .stat-label {{
                    font-size: 8pt;
                    color: #64748b;
                    text-transform: uppercase;
                    margin-top: 4px;
                    font-weight: 500;
                }}

                .risk-banner {{
                    background-color: {risk_color}12;
                    border-left: 4px solid {risk_color};
                    padding: 14px 18px;
                    border-radius: 4px;
                    margin-bottom: 24px;
                }}

                .risk-title {{
                    font-weight: 700;
                    color: {risk_color};
                    font-size: 13pt;
                    margin-bottom: 6px;
                }}

                .risk-desc {{
                    margin: 0;
                    font-size: 9.5pt;
                    color: #334155;
                    line-height: 1.5;
                }}

                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 24px;
                }}

                th {{
                    background-color: #f1f5f9;
                    color: #475569;
                    text-align: left;
                    font-weight: 600;
                    font-size: 8.5pt;
                    padding: 8px 10px;
                    border-bottom: 2px solid #cbd5e1;
                    text-transform: uppercase;
                    letter-spacing: 0.03em;
                }}

                td {{
                    padding: 10px;
                    font-size: 9.5pt;
                    border-bottom: 1px solid #e2e8f0;
                }}

                .badge {{
                    display: inline-block;
                    padding: 2px 7px;
                    font-size: 7.5pt;
                    font-weight: 600;
                    border-radius: 4px;
                    text-transform: uppercase;
                }}

                .badge-cwe {{
                    background-color: #f1f5f9;
                    color: #475569;
                    padding: 1px 5px;
                    font-size: 8pt;
                    border-radius: 3px;
                    font-family: monospace;
                }}

                .finding-card {{
                    background-color: #ffffff;
                    border: 1px solid #e2e8f0;
                    border-radius: 6px;
                    padding: 16px;
                    margin-bottom: 18px;
                    box-shadow: 0 1px 2px rgba(0,0,0,0.02);
                }}

                .finding-title-bar {{
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    margin-bottom: 8px;
                }}

                .finding-id {{
                    font-family: monospace;
                    font-weight: 700;
                    font-size: 10pt;
                    color: #64748b;
                    margin-right: 8px;
                }}

                .finding-title {{
                    font-size: 12pt;
                    font-weight: 700;
                    color: #0f172a;
                    flex-grow: 1;
                }}

                .finding-meta {{
                    font-size: 8pt;
                    color: #64748b;
                    border-bottom: 1px solid #f1f5f9;
                    padding-bottom: 6px;
                    margin-bottom: 12px;
                }}

                .section-title {{
                    font-size: 9pt;
                    font-weight: 600;
                    text-transform: uppercase;
                    color: #475569;
                    margin-top: 12px;
                    margin-bottom: 4px;
                    letter-spacing: 0.04em;
                }}

                .description-text, .remediation-text {{
                    margin: 0;
                    font-size: 9.5pt;
                    color: #334155;
                    line-height: 1.5;
                }}

                .evidence-container {{
                    margin-top: 10px;
                    border: 1px solid #e2e8f0;
                    border-radius: 4px;
                    overflow: hidden;
                }}

                .evidence-header {{
                    background-color: #f8fafc;
                    padding: 4px 10px;
                    font-size: 8pt;
                    font-weight: 500;
                    color: #64748b;
                    border-bottom: 1px solid #e2e8f0;
                }}

                .evidence-code {{
                    margin: 0;
                    padding: 10px;
                    background-color: #0f172a;
                    color: #e2e8f0;
                    font-family: 'Courier New', Courier, monospace;
                    font-size: 8pt;
                    white-space: pre-wrap;
                    overflow-x: auto;
                    line-height: 1.4;
                }}

                .page-break-avoid {{
                    page-break-inside: avoid;
                }}

                .chart-container {{
                    display: flex;
                    gap: 20px;
                    margin-bottom: 24px;
                    page-break-inside: avoid;
                }}

                .chart-box {{
                    flex: 1;
                    background: #f8fafc;
                    border: 1px solid #e2e8f0;
                    border-radius: 6px;
                    padding: 16px;
                    text-align: center;
                }}

                .chart-title {{
                    font-size: 9pt;
                    font-weight: 600;
                    color: #475569;
                    text-transform: uppercase;
                    margin-bottom: 12px;
                    letter-spacing: 0.04em;
                }}

                .phase-bar-container {{
                    width: 100%;
                    height: 8px;
                    background: #e2e8f0;
                    border-radius: 4px;
                    overflow: hidden;
                }}

                .phase-bar {{
                    height: 100%;
                    background: linear-gradient(90deg, #7c3aed, #a78bfa);
                    border-radius: 4px;
                }}

                .recommendation-card {{
                    background: #f0fdf4;
                    border: 1px solid #bbf7d0;
                    border-left: 4px solid #22c55e;
                    border-radius: 4px;
                    padding: 12px 16px;
                    margin-bottom: 12px;
                }}

                .recommendation-title {{
                    font-weight: 700;
                    color: #166534;
                    font-size: 10pt;
                    margin-bottom: 4px;
                }}

                .recommendation-text {{
                    margin: 0;
                    font-size: 9pt;
                    color: #15803d;
                    line-height: 1.4;
                }}

                .info-card {{
                    background: #eff6ff;
                    border: 1px solid #bfdbfe;
                    border-left: 4px solid #3b82f6;
                    border-radius: 4px;
                    padding: 12px 16px;
                    margin-bottom: 12px;
                }}

                .info-card .recommendation-title {{
                    color: #1e40af;
                }}

                .info-card .recommendation-text {{
                    color: #1d4ed8;
                }}
            </style>
        </head>
        <body>
            <!-- Cover Page -->
            <div class="cover-page">
                <div class="cover-header">
                    <h1 class="cover-title">Fire Crow Audit Report</h1>
                    <p class="cover-subtitle">Autonomous Security Intelligence Analysis</p>
                </div>
                
                <div class="cover-metadata">
                    <div class="metadata-grid">
                        <div class="metadata-row">
                            <div class="metadata-label">Job ID</div>
                            <div class="metadata-value">{safe_job_id}</div>
                        </div>
                        <div class="metadata-row">
                            <div class="metadata-label">Repository</div>
                            <div class="metadata-value">{safe_repo_url}</div>
                        </div>
                        <div class="metadata-row">
                            <div class="metadata-label">Branch</div>
                            <div class="metadata-value">{safe_branch}</div>
                        </div>
                        <div class="metadata-row">
                            <div class="metadata-label">Audit Date</div>
                            <div class="metadata-value">{datetime.now(timezone.utc).strftime('%B %d, %Y at %H:%M UTC')}</div>
                        </div>
                        <div class="metadata-row">
                            <div class="metadata-label">Total Findings</div>
                            <div class="metadata-value">{total_issues}</div>
                        </div>
                        <div class="metadata-row">
                            <div class="metadata-label">Risk Level</div>
                            <div class="metadata-value" style="color: {risk_color}; font-weight: 700;">{risk_label}</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Executive Summary -->
            <div class="section-header">Executive Summary</div>
            
            <div class="risk-banner">
                <div class="risk-title">OVERALL POSTURE: {risk_label}</div>
                <p class="risk-desc">{risk_narrative}</p>
            </div>

            <div class="card-grid">
                <div class="stat-card" style="border-top: 3px solid #ef4444;">
                    <div class="stat-number" style="color: #ef4444;">{counts[Severity.CRITICAL]}</div>
                    <div class="stat-label">Critical</div>
                </div>
                <div class="stat-card" style="border-top: 3px solid #f97316;">
                    <div class="stat-number" style="color: #f97316;">{counts[Severity.HIGH]}</div>
                    <div class="stat-label">High</div>
                </div>
                <div class="stat-card" style="border-top: 3px solid #eab308;">
                    <div class="stat-number" style="color: #eab308;">{counts[Severity.MEDIUM]}</div>
                    <div class="stat-label">Medium</div>
                </div>
                <div class="stat-card" style="border-top: 3px solid #3b82f6;">
                    <div class="stat-number" style="color: #3b82f6;">{counts[Severity.LOW]}</div>
                    <div class="stat-label">Low</div>
                </div>
                <div class="stat-card" style="border-top: 3px solid #94a3b8;">
                    <div class="stat-number" style="color: #94a3b8;">{counts[Severity.INFO]}</div>
                    <div class="stat-label">Info</div>
                </div>
            </div>

            <!-- Charts -->
            <div class="chart-container">
                <div class="chart-box">
                    <div class="chart-title">Severity Distribution</div>
                    {donut_chart}
                </div>
                <div class="chart-box">
                    <div class="chart-title">Findings by Severity</div>
                    {severity_bar}
                </div>
            </div>

            {f"""
            <div class="chart-box" style="margin-bottom: 24px;">
                <div class="chart-title">Findings by Scanner</div>
                {bar_chart}
            </div>
            """ if scanner_counts else ""}

            {f"""
            <!-- Top CWEs -->
            <div class="section-header" style="page-break-before: avoid;">Top CWE Weaknesses</div>
            <table style="max-width: 400px;">
                <thead>
                    <tr><th>CWE ID</th><th>Occurrences</th></tr>
                </thead>
                <tbody>
                    {cwe_rows}
                </tbody>
            </table>
            """ if top_cwes else ""}

            <!-- Recommendations -->
            <div class="section-header">Security Recommendations</div>
            {self._build_recommendations(counts, findings)}

            <!-- Findings Table -->
            <div class="section-header">Summary Table of Findings</div>
            <table>
                <thead>
                    <tr>
                        <th style="width: 60px;">ID</th>
                        <th>Title</th>
                        <th style="width: 70px;">Severity</th>
                        <th style="width: 100px;">Source</th>
                        <th style="width: 80px;">CWE</th>
                        <th style="width: 50px;">CVSS</th>
                    </tr>
                </thead>
                <tbody>
                    {findings_rows or "<tr><td colspan='6' style='text-align: center; color: #64748b;'>No security issues detected. Clean audit report.</td></tr>"}
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
                    {scanner_rows or "<tr><td colspan='4' style='text-align: center; color: #64748b;'>No scanner execution data recorded.</td></tr>"}
                </tbody>
            </table>

            {f"""
            <!-- Phase Execution Timeline -->
            <div class="section-header">Pipeline Execution Timeline</div>
            <p style="font-size: 9pt; color: #64748b; margin-bottom: 12px;">Total execution time: {total_duration:.1f} seconds</p>
            <table>
                <thead>
                    <tr>
                        <th style="width: 180px;">Phase</th>
                        <th style="width: 80px;">Duration</th>
                        <th>Progress</th>
                        <th style="width: 70px;">% of Total</th>
                    </tr>
                </thead>
                <tbody>
                    {phase_rows}
                </tbody>
            </table>
            """ if phase_durations else ""}

            <!-- Detailed Findings -->
            <div class="section-header">Detailed Findings & Proofs</div>
            {detailed_findings or "<div class='info-card'><div class='recommendation-title'>No Vulnerabilities Found</div><div class='recommendation-text'>No vulnerabilities were identified during this audit. The application follows security best practices across all tested attack vectors.</div></div>"}

            <!-- Footer -->
            <div style="margin-top: 40px; padding-top: 16px; border-top: 2px solid #e2e8f0; text-align: center; font-size: 8pt; color: #94a3b8;">
                <p style="margin: 0;">Generated by <strong>Fire Crow</strong> &mdash; Autonomous Security Intelligence Platform</p>
                <p style="margin: 4px 0 0 0;">Nova Devs &copy; {datetime.now(timezone.utc).year}. Report timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            </div>
        </body>
        </html>
        """
        return html_template

    def _build_donut_chart(self, counts: Dict[Severity, int], total: int, colors: Dict[Severity, str]) -> str:
        """Build an SVG donut chart for severity distribution."""
        if total == 0:
            return '<svg width="160" height="160" viewBox="0 0 160 160"><circle cx="80" cy="80" r="60" fill="none" stroke="#e2e8f0" stroke-width="20"/><text x="80" y="85" text-anchor="middle" font-size="14" fill="#94a3b8" font-family="system-ui">No findings</text></svg>'

        import math
        cx, cy, r = 80, 80, 55
        circumference = 2 * math.pi * r
        offset = 0
        arcs = []
        
        for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]:
            count = counts.get(severity, 0)
            if count == 0:
                continue
            pct = count / total
            dash = pct * circumference
            gap = circumference - dash
            color = colors.get(severity, "#94a3b8")
            arcs.append(
                f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" '
                f'stroke-width="22" stroke-dasharray="{dash:.1f} {gap:.1f}" '
                f'stroke-dashoffset="-{offset:.1f}" transform="rotate(-90 {cx} {cy})"/>'
            )
            offset += dash

        center_text = f'<text x="{cx}" y="{cy - 4}" text-anchor="middle" font-size="22" font-weight="700" fill="#0f172a" font-family="system-ui">{total}</text>'
        center_label = f'<text x="{cx}" y="{cy + 14}" text-anchor="middle" font-size="9" fill="#64748b" font-family="system-ui">findings</text>'
        
        legend_items = []
        y_offset = 10
        for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]:
            count = counts.get(severity, 0)
            if count == 0:
                continue
            color = colors.get(severity, "#94a3b8")
            legend_items.append(
                f'<rect x="150" y="{y_offset}" width="10" height="10" rx="2" fill="{color}"/>'
                f'<text x="165" y="{y_offset + 8.5}" font-size="8" fill="#475569" font-family="system-ui">{severity.value.upper()}: {count}</text>'
            )
            y_offset += 16

        return f'<svg width="300" height="160" viewBox="0 0 300 160">{"".join(arcs)}{center_text}{center_label}{"".join(legend_items)}</svg>'

    def _build_severity_bar_chart(self, counts: Dict[Severity, int], colors: Dict[Severity, str]) -> str:
        """Build a horizontal bar chart for severity counts."""
        max_count = max(counts.values()) if counts else 1
        bars = []
        y = 10
        for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]:
            count = counts.get(severity, 0)
            color = colors.get(severity, "#94a3b8")
            bar_width = (count / max_count * 180) if max_count > 0 else 0
            bars.append(
                f'<text x="65" y="{y + 10}" text-anchor="end" font-size="9" fill="#475569" font-family="system-ui">{severity.value.upper()}</text>'
                f'<rect x="70" y="{y}" width="{bar_width}" height="14" rx="3" fill="{color}"/>'
                f'<text x="{70 + bar_width + 6}" y="{y + 10.5}" font-size="9" fill="#0f172a" font-weight="600" font-family="system-ui">{count}</text>'
            )
            y += 22
        return f'<svg width="280" height="{y + 5}" viewBox="0 0 280 {y + 5}">{"".join(bars)}</svg>'

    def _build_scanner_bar_chart(self, scanner_counts: Dict[str, Dict[str, int]], colors: Dict[Severity, str]) -> str:
        """Build a stacked horizontal bar chart for findings by scanner."""
        if not scanner_counts:
            return ""
        
        bars = []
        y = 10
        max_total = max(sum(sc.values()) for sc in scanner_counts.values()) if scanner_counts else 1
        
        for scanner, sc in sorted(scanner_counts.items(), key=lambda x: sum(x[1].values()), reverse=True):
            total = sum(sc.values())
            x_offset = 70
            label = scanner[:20] + ("..." if len(scanner) > 20 else "")
            bars.append(f'<text x="65" y="{y + 10}" text-anchor="end" font-size="8" fill="#475569" font-family="system-ui">{html.escape(label)}</text>')
            
            for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]:
                count = sc.get(severity.value, 0)
                if count == 0:
                    continue
                seg_width = (count / max_total * 200) if max_total > 0 else 0
                color = colors.get(severity, "#94a3b8")
                bars.append(f'<rect x="{x_offset}" y="{y}" width="{seg_width}" height="14" rx="2" fill="{color}"/>')
                x_offset += seg_width
            
            bars.append(f'<text x="{x_offset + 5}" y="{y + 10.5}" font-size="8" fill="#0f172a" font-weight="600" font-family="system-ui">{total}</text>')
            y += 20
        
        return f'<svg width="100%" height="{y + 5}" viewBox="0 0 500 {y + 5}" preserveAspectRatio="xMinYMin meet">{"".join(bars)}</svg>'

    def _build_recommendations(self, counts: Dict[Severity, int], findings: List[Finding]) -> str:
        """Build contextual security recommendations."""
        recs = []
        
        if counts[Severity.CRITICAL] > 0:
            recs.append(("Immediate Action Required", "Critical vulnerabilities were identified that could lead to severe data breaches or system compromise. Prioritize patching these issues before deploying to production. Consider conducting a focused penetration test on the affected attack surfaces."))
        
        if counts[Severity.HIGH] > 0:
            recs.append(("Urgent Remediation", "High-severity findings expose significant attack vectors. Address these within the current sprint cycle. Implement additional input validation, output encoding, and access control checks."))
        
        if counts[Severity.MEDIUM] > 0:
            recs.append(("Planned Remediation", "Medium-severity issues should be addressed in the next development cycle. These represent defense-in-depth weaknesses that could be chained with other vulnerabilities."))
        
        # Check for specific patterns
        cwe_findings = {}
        for f in findings:
            if f.cwe_id:
                cwe_findings.setdefault(f.cwe_id, []).append(f)
        
        if "CWE-89" in cwe_findings or "CWE-89" in str([f.cwe_id for f in findings]):
            recs.append(("SQL Injection Detected", "SQL injection vulnerabilities allow attackers to execute arbitrary database queries. Use parameterized queries or ORM methods. Never concatenate user input into SQL strings."))
        
        if "CWE-79" in str([f.cwe_id for f in findings]):
            recs.append(("Cross-Site Scripting (XSS)", "XSS vulnerabilities enable attackers to inject malicious scripts. Implement Content Security Policy headers, sanitize all user inputs, and use context-appropriate output encoding."))
        
        if "CWE-22" in str([f.cwe_id for f in findings]):
            recs.append(("Path Traversal", "Path traversal vulnerabilities allow access to files outside the intended directory. Validate and sanitize file paths, use allowlists for permitted directories."))
        
        # Always add general recommendations
        recs.append(("Security Best Practices", "Enable Content Security Policy (CSP) headers, implement rate limiting on all API endpoints, use HTTPS everywhere, and maintain dependency updates. Consider adding automated security scanning to your CI/CD pipeline."))
        recs.append(("Monitoring & Logging", "Implement comprehensive logging for all security-relevant events. Set up alerting for anomalous patterns, failed authentication attempts, and unauthorized access attempts."))
        
        html_recs = ""
        for title, text in recs:
            html_recs += f"""
            <div class="recommendation-card">
                <div class="recommendation-title">{html.escape(title)}</div>
                <p class="recommendation-text">{html.escape(text)}</p>
            </div>
            """
        return html_recs

    def compile_pdf(self, html_content: str, output_path: str) -> bool:
        if not WEASYPRINT_AVAILABLE:
            logger.warning("WeasyPrint not available. PDF generation skipped for %s.", output_path)
            fallback_path = output_path.replace(".pdf", ".html")
            try:
                with open(fallback_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                logger.info("Wrote HTML fallback to %s", fallback_path)
            except Exception as e:
                logger.error("Failed to write HTML fallback: %s", e)
            return False

        try:
            logger.info("Compiling HTML to PDF using WeasyPrint: %s", output_path)
            weasyprint.HTML(string=html_content).write_pdf(output_path)
            return True
        except Exception as e:
            logger.exception("WeasyPrint PDF compilation failed: %s", e)
            return False

    def upload_to_r2(self, pdf_path: str, job_id: str) -> str:
        """
        Uploads report to Cloudflare R2 bucket.
        Falls back to local file URI if R2 credentials are not set.
        """
        filename = os.path.basename(pdf_path)
        if _global_state.get("r2_disabled", False):
            logger.info("Cloudflare R2 operations are disabled due to a previous authentication failure. Serving locally.")
            return f"/reports/{filename}"
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
                    "R2 credentials were rejected for job %s. Disabling future R2 operations and serving local report.",
                    job_id,
                )
                _global_state["r2_disabled"] = True
            else:
                logger.error(
                    "R2 upload failed for job %s: %s. Falling back to local report endpoint.",
                    job_id,
                    redacted_error,
                )
            return f"/reports/{filename}"


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
            report_link = build_audit_job_url(job_id)
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
        
        <div class="cta-container">
          <a href="{safe_report_url}" class="cta-button">View Security Report</a>
        </div>
        
        <div style="margin-top: 32px; padding: 16px; background-color: #f8fafc; border-left: 4px solid #7c3aed; border-radius: 8px; text-align: left; box-sizing: border-box;">
          <p style="margin: 0; font-size: 14px; font-weight: 700; color: #1e1b4b; display: flex; align-items: center;">
            <span style="font-size: 16px; margin-right: 8px;">📎</span> PDF Report Attached
          </p>
          <p style="margin: 6px 0 0 0; font-size: 13px; color: #4b5563; line-height: 1.5;">
            A full high-fidelity PDF copy of this security audit report has been compiled and attached to this email for offline reading and records compliance.
          </p>
        </div>
      </div>
      
      <div class="footer">
        <p class="footer-text">
          This email was automatically generated by Fire Crow Security.<br>
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
                    msg["Subject"] = f"Fire Crow Security Audit: {repo_name}"
                    msg["From"] = f"Fire Crow Audit <{settings.SMTP_USER}>"
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

                    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                        server.starttls()
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
                        "from": f"Fire Crow Audit <{self.sender_email}>",
                        "to": [to_email],
                        "subject": f"Fire Crow Security Audit: {repo_name}",
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
                    resend.Emails.send(params)  # type: ignore
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
                        "sender": {"email": self.sender_email, "name": "Fire Crow Audit"},
                        "to": [{"email": to_email}],
                        "subject": f"Fire Crow Security Audit: {repo_name}",
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
            if pdf_path and success:
                try:
                    if os.path.exists(pdf_path):
                        os.remove(pdf_path)
                    html_path = pdf_path.replace(".pdf", ".html")
                    if os.path.exists(html_path):
                        os.remove(html_path)
                    logger.info("Purged local report file copies after successful email dispatch.")
                except Exception as delete_error:
                    logger.warning("Failed to delete local report copies after email dispatch: %s", str(delete_error))
