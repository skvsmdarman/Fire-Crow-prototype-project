from backend.app.schemas import AuditState, Finding, JobStatus, Severity
from backend.app.orchestrator.maestro import get_reportable_findings, maestro_graph
from backend.app.models import SessionLocal, AuditJob


def test_maestro_default_path():
    # Setup a mock job in the database
    db = SessionLocal()
    job = AuditJob(
        id="job-default",
        user_id="usr_tester",
        repo_url="https://github.com/example/standard-repo",
        repo_branch="main",
        status=JobStatus.RUNNING
    )
    db.add(job)
    db.commit()
    db.close()

    # Create initial state
    initial_state = AuditState(
        job_id="job-default",
        user_id="usr_tester",
        repo_url="https://github.com/example/standard-repo",
        repo_branch="main"
    )

    # Run the graph
    final_state = maestro_graph.invoke(initial_state)

    # Assert correct transitions and outputs
    # Standard repository has no secrets or vulnerabilities in mock logic
    assert final_state["current_phase"] == "cleanup"
    assert final_state["status"] == JobStatus.COMPLETED
    assert len(final_state["static_findings"]) == 1
    assert final_state["static_findings"][0].title == "Outdated dependency package PyYAML"
    assert len(final_state["dynamic_findings"]) == 0
    assert len(final_state["exploit_proofs"]) == 0
    assert "job-default.pdf" in final_state["report_pdf_url"]


def test_maestro_secrets_leak_path():
    # Setup a mock job with "leak" in repo_url
    db = SessionLocal()
    job = AuditJob(
        id="job-leak",
        user_id="usr_tester",
        repo_url="https://github.com/example/leaky-secrets-repo",
        repo_branch="main",
        status=JobStatus.RUNNING
    )
    db.add(job)
    db.commit()
    db.close()

    # Create initial state
    initial_state = AuditState(
        job_id="job-leak",
        user_id="usr_tester",
        repo_url="https://github.com/example/leaky-secrets-repo",
        repo_branch="main"
    )

    # Run the graph
    final_state = maestro_graph.invoke(initial_state)

    # Secrets leak path should skip sandbox, network, attack, exploit phases and route straight to scoring
    assert final_state["current_phase"] == "cleanup"
    assert final_state["status"] == JobStatus.COMPLETED
    assert len(final_state["static_findings"]) == 1
    assert final_state["static_findings"][0].title == "Hardcoded GitHub OAuth Secret Leak"
    
    # Verify sandbox did not run (sandbox_ready is default False)
    assert final_state["sandbox_ready"] is False
    assert final_state["sandbox_container_id"] == ""


def test_maestro_vuln_exploit_path():
    # Setup a mock job with "vuln" in repo_url
    db = SessionLocal()
    job = AuditJob(
        id="job-vuln",
        user_id="usr_tester",
        repo_url="https://github.com/example/vulnerable-app",
        repo_branch="main",
        status=JobStatus.RUNNING
    )
    db.add(job)
    db.commit()
    db.close()

    initial_state = AuditState(
        job_id="job-vuln",
        user_id="usr_tester",
        repo_url="https://github.com/example/vulnerable-app",
        repo_branch="main"
    )

    final_state = maestro_graph.invoke(initial_state)

    # Vulnerability path should run sandbox, attack, and execute exploit
    assert final_state["current_phase"] == "cleanup"
    assert final_state["status"] == JobStatus.COMPLETED
    assert len(final_state["dynamic_findings"]) == 2
    titles = [f.title for f in final_state["dynamic_findings"]]
    assert "SQL Injection in user profile parameters" in titles
    assert "Outdated Web Component Vulnerability" in titles
    assert len(final_state["exploit_proofs"]) == 1
    assert final_state["exploit_proofs"][0].title == "Exploitable SQL Injection Proof"


def test_reportable_findings_include_all_agent_classes():
    state = AuditState(
        job_id="job-reportable",
        user_id="usr_tester",
        repo_url="https://github.com/example/repo",
        static_findings=[
            Finding(id="static-1", agent_source="SAST", title="Static", description="Static issue", severity=Severity.HIGH)
        ],
        semgrep_findings=[
            Finding(id="semgrep-1", agent_source="SEMGREP", title="Semgrep", description="Semgrep issue", severity=Severity.HIGH)
        ],
        dependency_vulns=[
            Finding(id="dep-1", agent_source="DEPENDENCY", title="Dependency", description="Dependency issue", severity=Severity.MEDIUM)
        ],
        iac_findings=[
            Finding(id="iac-1", agent_source="IAC", title="IaC", description="IaC issue", severity=Severity.LOW)
        ],
        dynamic_findings=[
            Finding(id="dynamic-1", agent_source="ATTACK", title="Dynamic", description="Dynamic issue", severity=Severity.CRITICAL)
        ],
        exploit_proofs=[
            Finding(id="exploit-1", agent_source="EXPLOIT", title="Exploit", description="Exploit proof", severity=Severity.CRITICAL)
        ],
    )

    titles = {finding.title for finding in get_reportable_findings(state)}

    assert titles == {"Static", "Semgrep", "Dependency", "IaC", "Dynamic", "Exploit"}


def test_reportable_findings_keep_ai_dedupe_and_exploit_proofs():
    state = AuditState(
        job_id="job-reportable",
        user_id="usr_tester",
        repo_url="https://github.com/example/repo",
        static_findings=[
            Finding(id="static-1", agent_source="SAST", title="Static", description="Static issue", severity=Severity.HIGH)
        ],
        deduplicated_findings=[
            Finding(id="dedupe-1", agent_source="AI_ANALYZER", title="Deduped", description="Retained issue", severity=Severity.HIGH)
        ],
        exploit_proofs=[
            Finding(id="exploit-1", agent_source="EXPLOIT", title="Exploit", description="Exploit proof", severity=Severity.CRITICAL)
        ],
    )

    titles = [finding.title for finding in get_reportable_findings(state)]

    assert titles == ["Deduped", "Exploit"]
