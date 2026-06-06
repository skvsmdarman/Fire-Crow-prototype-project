import os
import shutil
import logging
from backend.app.agents.recon import run_recon, detect_tech_stack
from backend.app.agents.sast import run_sast, scan_for_secrets, scan_for_unsafe_code
from backend.app.agents.dependency_scan import run_dependency_scan
from backend.app.agents.sast_semgrep import run_semgrep_scan
from backend.app.services.sandbox import SandboxManager
from backend.app.config import settings


def test_recon_mock_path():
    res = run_recon("job-test-1", "https://github.com/example/standard-repo", "main")
    assert res["error"] is None
    assert "Python" in res["tech_stack"]
    assert "main.py" in res["entry_points"]


def test_tech_stack_detection(tmp_path):
    # Setup dummy directory structure
    d = tmp_path / "src"
    d.mkdir()
    (d / "package.json").write_text('{"name": "test"}')
    (d / "requirements.txt").write_text("fastapi\nuvicorn")
    (d / "Dockerfile").write_text("FROM python:3.12")
    (d / "server.js").write_text("console.log('hello')")
    
    tech_stack, dependency_manifests, entry_points = detect_tech_stack(str(tmp_path))
    
    assert "NodeJS" in tech_stack
    assert "Python" in tech_stack
    assert "Docker" in tech_stack
    assert any("package.json" in m for m in dependency_manifests)
    assert any("requirements.txt" in m for m in dependency_manifests)
    assert any("Dockerfile" in e for e in entry_points)
    assert any("server.js" in e for e in entry_points)


def test_sast_secrets_leak_detection(tmp_path):
    # Create file with GitHub OAuth secret signature and a AWS key signature
    leak_file = tmp_path / "secrets_leak.py"
    leak_file.write_text(
        "github_token = 'ghp_AbCdEfGhIjKlMnOpQrStUvWxYz0123456789aBcD'\n"
        "aws_id = 'AKIAIOSFODNN7EXAMPLE'\n"
    )
    
    findings = scan_for_secrets(str(tmp_path))
    assert len(findings) == 2
    
    github_finding = next(f for f in findings if "GitHub" in f.title)
    aws_finding = next(f for f in findings if "AWS" in f.title)
    
    assert github_finding.severity.value == "critical"
    assert aws_finding.severity.value == "critical"
    assert "ghp_AbCdEf" not in (github_finding.evidence or "")
    assert "AKIAIOSFODNN7EXAMPLE" not in (aws_finding.evidence or "")
    assert "redacted_fingerprint=sha256:" in (github_finding.evidence or "")


def test_sast_unsafe_code_detection(tmp_path):
    # Create file with eval and SQL Injection queries
    unsafe_file = tmp_path / "unsafe.py"
    unsafe_file.write_text(
        "def run_command(user_input):\n"
        "    eval(user_input)\n"
        "    query = f\"SELECT * FROM users WHERE username = '{user_input}'\"\n"
        "    db.execute(query)\n"
    )
    
    findings = scan_for_unsafe_code(str(tmp_path))
    assert len(findings) == 2
    
    eval_finding = next(f for f in findings if "eval()" in f.title)
    sql_finding = next(f for f in findings if "SQL Injection" in f.title)
    
    assert eval_finding.severity.value == "high"
    assert sql_finding.severity.value == "critical"


def test_github_mcp_url_parsing():
    from backend.app.agents.github_mcp import parse_repo_url
    
    res = parse_repo_url("https://github.com/owner/repo-name")
    assert res == ("owner", "repo-name")
    
    res_git = parse_repo_url("git@github.com:another-owner/project.git")
    assert res_git == ("another-owner", "project")


def test_github_mcp_run_mock():
    from backend.app.agents.github_mcp import run_github_mcp
    from backend.app.schemas import Finding, Severity

    findings = [
        Finding(
            id="f-1",
            agent_source="SAST",
            title="SQL Injection",
            description="Vulnerable to SQL Injection",
            severity=Severity.CRITICAL
        )
    ]
    
    res = run_github_mcp("job-test-mcp", "https://github.com/example/standard-repo", findings)
    assert res["github_issue_created"] is True
    assert res["github_pr_created"] is False
    assert any("Simulating GitHub Issue creation" in log for log in res["github_mcp_logs"])


def test_github_mcp_markdown_escapes_content_and_safe_fences():
    from backend.app.agents.github_mcp import format_findings_markdown
    from backend.app.schemas import Finding, Severity

    findings = [
        Finding(
            id="f-escape",
            agent_source="SAST|scanner",
            title="[Critical](https://attacker.example) *boom*",
            description="Description with # heading and > quote",
            severity=Severity.CRITICAL,
            evidence="before\n```\nmalicious fence\n```\nafter",
            remediation="Patch [now](https://attacker.example).",
        )
    ]

    body = format_findings_markdown("https://github.com/example/repo", findings)

    assert "\\[Critical\\]" in body
    assert "\\*boom\\*" in body
    assert "\\> quote" in body
    assert "````\nbefore\n```\nmalicious fence\n```\nafter\n````" in body


def test_google_agent_run_mock():
    from backend.app.agents.google_agent import run_google_agent
    from backend.app.schemas import Finding, Severity

    findings = [
        Finding(
            id="f-1",
            agent_source="SAST",
            title="SQL Injection",
            description="Vulnerable to SQL Injection",
            severity=Severity.CRITICAL
        )
    ]
    remediations = [
        {
            "finding_id": "f-1",
            "file": "app.py",
            "original_code": "query = f'SELECT * FROM users WHERE id = {id}'",
            "fixed_code": "cursor.execute('SELECT * FROM users WHERE id = %s', (id,))"
        }
    ]

    res = run_google_agent(
        job_id="job-test-google",
        repo_url="https://github.com/example/standard-repo",
        findings=findings,
        remediations=remediations,
        recipient_email="test-recipient@firecrow.dev"
    )

    assert res["google_agent_pr_risks_analyzed"] is True
    assert "overall_pr_risk" in res["google_agent_risk_report"]
    assert "key_risk_factors" in res["google_agent_risk_report"]
    assert "merge_recommendation" in res["google_agent_risk_report"]
    assert any("Started Google Agent" in log for log in res["google_agent_logs"])


def test_mock_scanners_do_not_create_findings_in_production(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "DEBUG", False)
    monkeypatch.setattr("backend.app.agents.dependency_scan.shutil.which", lambda _name: None)
    monkeypatch.setattr("backend.app.agents.sast_semgrep.shutil.which", lambda _name: None)

    assert run_dependency_scan(str(tmp_path), ["requirements.txt"]) == []
    assert run_semgrep_scan(str(tmp_path), ["Python"]) == []
    assert run_sast(str(tmp_path), "https://github.com/example/standard-repo") == []


def test_sandbox_dockerfile_build_disabled_by_default():
    manager = SandboxManager()
    assert manager._allow_user_dockerfile_build() is False


def test_report_upload_logging_does_not_include_presigned_url(monkeypatch, caplog, tmp_path):
    import sys
    import types
    from backend.app.services.reporter import ReportGenerator

    class FakeS3:
        def upload_file(self, *_args, **_kwargs):
            return None

        def generate_presigned_url(self, *_args, **_kwargs):
            return "https://r2.example/reports/job.pdf?X-Amz-Signature=secret-signature"

    fake_boto3 = types.SimpleNamespace(client=lambda *args, **kwargs: FakeS3())
    fake_botocore_client = types.SimpleNamespace(Config=lambda **kwargs: object())
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    monkeypatch.setitem(sys.modules, "botocore.client", fake_botocore_client)

    generator = ReportGenerator()
    generator.r2_endpoint = "https://r2.example"
    generator.r2_access_key = "access"
    generator.r2_secret_key = "secret"
    pdf_path = tmp_path / "job.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    with caplog.at_level(logging.INFO):
        url = generator.upload_to_r2(str(pdf_path), "job-report-log")

    assert "X-Amz-Signature=secret-signature" in url
    assert "X-Amz-Signature=secret-signature" not in caplog.text
