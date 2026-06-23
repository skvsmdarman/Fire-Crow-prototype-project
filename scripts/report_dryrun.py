import os
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "backend"
sys.path.append(str(BASE))

from app.services.reporter import ReportGenerator
from app.schemas import Finding, Severity

def main():
    job_id = "dryrun-001"
    repo_url = "https://github.com/example/demo-repo"
    branch = "main"
    
    findings = [
        Finding(
            id="f-1",
            title="Hardcoded AWS Access Key",
            description="An AWS Access Key ID was found in source code.",
            severity=Severity.CRITICAL,
            agent_source="SAST",
            file_path="src/config.js",
            line_number=12,
            evidence="AKIAIOSFODNN7EXAMPLE",
            remediation="Rotate the AWS credentials immediately and use environment variables."
        ),
        Finding(
            id="f-2",
            title="SQL Injection Vulnerability",
            description="Raw SQL query construction with user inputs.",
            severity=Severity.HIGH,
            agent_source="Semgrep",
            file_path="src/db.py",
            line_number=45,
            evidence="db.execute('SELECT * FROM users WHERE name = ' + user_input)",
            remediation="Use parameterized queries instead."
        )
    ]
    
    print("Initializing ReportGenerator...")
    generator = ReportGenerator()
    
    print("Generating HTML report...")
    html_content = generator.generate_html_report(
        job_id=job_id,
        repo_url=repo_url,
        branch=branch,
        findings=findings
    )
    print(f"HTML generation complete (size={len(html_content)} chars)")
    
    temp_pdf_path = os.path.join(BASE, "workspace", "temp", "dryrun_report.pdf")
    os.makedirs(os.path.dirname(temp_pdf_path), exist_ok=True)
    
    print("Compiling PDF report...")
    success = generator.compile_pdf(html_content, temp_pdf_path)
    if success:
        print(f"✅ PDF report compiled successfully at: {temp_pdf_path}")
        # Clean up if generated
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
    else:
        print("❌ PDF compilation failed (expected if WeasyPrint dependencies are not installed on host)")

if __name__ == "__main__":
    main()
