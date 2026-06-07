from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Literal, Sequence

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.orm import Session

from backend.app.agents import (
    run_dynamic_attack,
    run_exploit_validation,
    run_network_scan,
    run_recon,
    run_sast,
)
from backend.app.agents.api_surface import api_surface_body
from backend.app.agents.secret_history import secret_history_body
from backend.app.agents.sbom_graph import sbom_graph_body
from backend.app.agents.cicd_scan import cicd_scan_body
from backend.app.agents.container_scan import container_scan_body
from backend.app.agents.authz_idor import authz_idor_body
from backend.app.services.attack_graph import attack_graph_body
from backend.app.services.remediation_planner import remediation_planner_body

from backend.app.agents.github_mcp import run_github_mcp
from backend.app.agents.sast_semgrep import run_semgrep_scan
from backend.app.agents.dependency_scan import run_dependency_scan
from backend.app.agents.iac_scan import run_iac_scan
from backend.app.agents.ai_analyzer import run_ai_analyzer
from backend.app.agents.google_agent import run_google_agent
from backend.app.models import AgentLog, AuditJob, FindingModel, SessionLocal, PhaseLedgerModel, AuthorizationAttestation, AuditArtifact
from backend.app.orchestrator.runtime_context import (
    JobCancellationRequested,
    apply_runtime_updates,
    mark_cleanup_completed,
    sync_runtime_state,
)
from backend.app.schemas import AuditState, Finding, JobStatus, Severity
from backend.app.config import WORKSPACE_DIR
from backend.app.services.reporter import ReportGenerator, get_clean_repo_name
from backend.app.services.sandbox import SandboxManager
from backend.app.services.redaction import redact_text

logger = logging.getLogger("firecrow.maestro")

PhaseBody = Callable[[Session, AuditState], Dict[str, Any]]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def build_phase_history_entry(phase: str, started_at: datetime, outcome: str) -> dict[str, Any]:
    ended_at = utc_now()
    return {
        "phase": phase,
        "started_at": started_at.isoformat(),
        "ended_at": ended_at.isoformat(),
        "duration_sec": round((ended_at - started_at).total_seconds(), 3),
        "outcome": outcome,
    }


def log_agent_message(db: Session, job_id: str, agent_name: str, message: str, level: str = "INFO") -> None:
    safe_message = redact_text(message, max_length=2048)
    logger.info("[%s] %s", agent_name, safe_message)
    db.add(
        AgentLog(
            job_id=job_id,
            agent_name=agent_name,
            log_level=level,
            message=safe_message,
        )
    )
    db.commit()


def _write_ledger_entry(
    db: Session,
    job_id: str,
    phase_name: str,
    status: str,
    mode: str,
    duration_sec: float | None = None,
    error_message: str | None = None,
    started_at: datetime | None = None,
    ended_at: datetime | None = None,
):
    try:
        ledger = PhaseLedgerModel(
            job_id=job_id,
            phase_name=phase_name,
            status=status,
            mode=mode,
            duration_sec=duration_sec,
            error_message=error_message,
            started_at=started_at or utc_now(),
            ended_at=ended_at,
        )
        db.add(ledger)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to write phase ledger entry for {phase_name}: {str(e)}")


def persist_findings(db: Session, job_id: str, findings: Sequence[Finding]) -> None:
    from backend.app.services.storage import storage_service
    from backend.app.services.redaction import redact_text

    # Retrieve job details for tenant scoping
    job = db.query(AuditJob).filter(AuditJob.id == job_id).first()
    tenant_id = job.tenant_id if job and job.tenant_id else "default-tenant"
    user_id = job.user_id if job else None

    for finding in findings:
        # Redact secrets in description and remediation
        redacted_desc = redact_text(finding.description or "")
        redacted_remediation = redact_text(finding.remediation or "") if finding.remediation else None

        # Redact secrets in evidence
        raw_evidence = finding.evidence or ""
        redacted_evidence = redact_text(raw_evidence) if raw_evidence else None

        db_evidence = redacted_evidence
        if redacted_evidence and len(redacted_evidence) > 1000:
            try:
                # Upload full redacted evidence as a private artifact
                artifact = storage_service.upload_artifact(
                    db=db,
                    file_data=redacted_evidence.encode("utf-8"),
                    organization_id=tenant_id,
                    artifact_type="finding_evidence",
                    file_name=f"finding-{finding.id}-evidence.txt",
                    user_id=user_id,
                    job_id=job_id,
                    sensitivity_level="restricted",
                )
                db_evidence = f"{redacted_evidence[:1000]}\n\n[Full evidence stored securely as private artifact ID: {artifact.id}]"
            except Exception as e:
                logger.error(f"Failed to upload large evidence for finding {finding.id} to object storage: {str(e)}")
                db_evidence = redacted_evidence[:1000] + "\n\n[Full evidence could not be uploaded; truncated for database safety]"

        db.add(
            FindingModel(
                id=finding.id,
                job_id=job_id,
                agent_source=finding.agent_source,
                title=finding.title,
                description=redacted_desc,
                severity=finding.severity,
                cvss_vector=finding.cvss_vector,
                cvss_score=finding.cvss_score,
                evidence=db_evidence,
                remediation=redacted_remediation,
                cwe_id=finding.cwe_id,
                owasp_category=finding.owasp_category,
                confidence=finding.confidence,
                scanner_name=finding.scanner_name,
                scanner_mode=finding.scanner_mode,
                file_path=finding.file_path,
                line_number=finding.line_number,
                route=finding.route,
                metadata_json=finding.metadata_json,
            )
        )
    db.commit()


def _finding_fingerprint(finding: Finding) -> tuple[str, str, str, str]:
    return (
        finding.id,
        finding.agent_source,
        finding.title,
        finding.evidence or "",
    )


def _dedupe_findings(findings: Sequence[Finding]) -> list[Finding]:
    seen: set[tuple[str, str, str, str]] = set()
    unique_findings: list[Finding] = []
    for finding in findings:
        fingerprint = _finding_fingerprint(finding)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        unique_findings.append(finding)
    return unique_findings


def get_reportable_findings(state: AuditState) -> list[Finding]:
    """Return the tenant-visible finding set used by reports and external agent handoffs."""
    if state.deduplicated_findings:
        return _dedupe_findings([*state.deduplicated_findings, *state.exploit_proofs])
    if state.scored_findings:
        return _dedupe_findings(state.scored_findings)

    return _dedupe_findings(
        [
            *state.static_findings,
            *state.semgrep_findings,
            *state.dependency_vulns,
            *state.iac_findings,
            *state.dynamic_findings,
            *state.exploit_proofs,
        ]
    )


def check_cancel_requested(db: Session, job_id: str, phase_name: str) -> None:
    db.expire_all()
    job = db.query(AuditJob).filter(AuditJob.id == job_id).first()
    if job and job.cancel_requested:
        log_agent_message(
            db,
            job_id,
            "MAESTRO",
            f"Cancellation request acknowledged during {phase_name}. Finalizing job cleanup.",
            "WARNING",
        )
        raise JobCancellationRequested(f"Cancellation requested during {phase_name}.")


def cleanup_resources(state: AuditState) -> None:
    if state.job_id:
        manager = SandboxManager()
        network_name = f"fc-net-{state.job_id}"
        target_container_id = f"fc-target-{state.job_id}"
        manager.cleanup_sandbox(
            network_name=network_name,
            target_container_id=target_container_id,
            kali_container_id=state.sandbox_container_id,
        )

    if state.clone_path and os.path.exists(state.clone_path):
        shutil.rmtree(state.clone_path, ignore_errors=True)


def execute_phase(
    state: AuditState,
    *,
    phase_name: str,
    agent_name: str,
    start_message: str,
    body: PhaseBody,
    check_cancel_before: bool = True,
    check_cancel_after: bool = True,
) -> Dict[str, Any]:
    db = SessionLocal()
    started_at = utc_now()
    sync_runtime_state(state)

    PHASE_TO_SCANNER_MAP = {
        "recon": "recon",
        "api_surface": "api_surface",
        "secret_history": "secret_history",
        "dependency_scan": "dependency",
        "sbom_graph": "sbom_graph",
        "iac_scan": "iac",
        "cicd_scan": "cicd_scan",
        "container_scan": "container_scan",
        "sast": "sast",
        "semgrep_scan": "semgrep",
        "authz_idor": "authz_idor",
        "sandbox": "sandbox",
        "network": "network",
        "attack": "attack",
        "exploit": "exploit",
    }

    NON_CRITICAL_PHASES = {
        "api_surface",
        "secret_history",
        "dependency_scan",
        "sbom_graph",
        "iac_scan",
        "cicd_scan",
        "container_scan",
        "semgrep_scan",
        "authz_idor",
        "sandbox",
        "network",
        "attack",
        "exploit",
        "github_mcp",
        "google_agent",
    }

    scanner_key = PHASE_TO_SCANNER_MAP.get(phase_name)

    if state.scan_plan and scanner_key:
        enabled_scanners = state.scan_plan.get("enabled_scanners", [])
        if scanner_key not in enabled_scanners:
            log_agent_message(db, state.job_id, agent_name, f"Skipping phase {phase_name} per ScanPlan.")
            _write_ledger_entry(
                db=db,
                job_id=state.job_id,
                phase_name=phase_name,
                status="skipped",
                mode="skipped",
                duration_sec=0.0,
                started_at=started_at,
                ended_at=started_at,
            )
            updates = {
                "scanner_execution": {
                    scanner_key: {
                        "status": "skipped",
                        "mode": "skipped",
                        "tool": "none"
                    }
                }
            }
            apply_runtime_updates(updates)
            db.close()
            return updates

    try:
        if check_cancel_before:
            check_cancel_requested(db, state.job_id, phase_name)

        log_agent_message(db, state.job_id, agent_name, start_message)
        updates = body(db, state)
        updates = {"current_phase": phase_name, **updates}
        apply_runtime_updates(updates)

        if check_cancel_after:
            check_cancel_requested(db, state.job_id, phase_name)

        ended_at = utc_now()
        duration_sec = round((ended_at - started_at).total_seconds(), 3)

        mode = "real"
        scanner_exec = updates.get("scanner_execution", {})
        if scanner_key and scanner_key in scanner_exec:
            mode = scanner_exec[scanner_key].get("mode", "real")
        elif scanner_exec:
            for k, val in scanner_exec.items():
                if isinstance(val, dict) and "mode" in val:
                    mode = val["mode"]

        if "example/" in state.repo_url:
            mode = "simulated"

        history_list = updates.get("phase_history")
        if not history_list or not isinstance(history_list, list) or len(history_list) == 0:
            updates["phase_history"] = [build_phase_history_entry(phase_name, started_at, "completed")]
        else:
            first_entry = history_list[0]
            if isinstance(first_entry, dict):
                updates["phase_history"] = [
                    {
                        **first_entry,
                        "started_at": first_entry.get("started_at", started_at.isoformat()),
                        "ended_at": first_entry.get("ended_at", ended_at.isoformat()),
                        "duration_sec": first_entry.get("duration_sec", duration_sec),
                        "outcome": first_entry.get("outcome", "completed"),
                    }
                ]
            else:
                updates["phase_history"] = [build_phase_history_entry(phase_name, started_at, "completed")]
        
        apply_runtime_updates({"phase_history": updates["phase_history"]})
        log_agent_message(db, state.job_id, agent_name, f"{phase_name.capitalize()} phase completed.")

        _write_ledger_entry(
            db=db,
            job_id=state.job_id,
            phase_name=phase_name,
            status="completed",
            mode=mode,
            duration_sec=duration_sec,
            started_at=started_at,
            ended_at=ended_at,
        )
        return updates
    except JobCancellationRequested:
        ended_at = utc_now()
        duration_sec = round((ended_at - started_at).total_seconds(), 3)
        apply_runtime_updates(
            {
                "current_phase": phase_name,
                "phase_history": [build_phase_history_entry(phase_name, started_at, "cancelled")],
            }
        )
        _write_ledger_entry(
            db=db,
            job_id=state.job_id,
            phase_name=phase_name,
            status="cancelled",
            mode="skipped",
            duration_sec=duration_sec,
            started_at=started_at,
            ended_at=ended_at,
        )
        raise
    except Exception as exc:
        ended_at = utc_now()
        duration_sec = round((ended_at - started_at).total_seconds(), 3)
        error_msg = str(exc)
        log_agent_message(db, state.job_id, agent_name, f"{phase_name.capitalize()} phase failed: {error_msg}", "ERROR")
        
        if phase_name in NON_CRITICAL_PHASES:
            updates = {
                "current_phase": phase_name,
                "errors": [{"phase": phase_name, "message": error_msg, "timestamp": ended_at.isoformat()}],
                "phase_history": [build_phase_history_entry(phase_name, started_at, "failed")],
                "status": JobStatus.PARTIAL,
            }
            apply_runtime_updates(updates)
            
            _write_ledger_entry(
                db=db,
                job_id=state.job_id,
                phase_name=phase_name,
                status="failed",
                mode="degraded",
                duration_sec=duration_sec,
                error_message=error_msg,
                started_at=started_at,
                ended_at=ended_at,
            )
            db.close()
            return updates
        else:
            apply_runtime_updates(
                {
                    "current_phase": phase_name,
                    "errors": [{"phase": phase_name, "message": error_msg, "timestamp": ended_at.isoformat()}],
                    "phase_history": [build_phase_history_entry(phase_name, started_at, "failed")],
                }
            )
            _write_ledger_entry(
                db=db,
                job_id=state.job_id,
                phase_name=phase_name,
                status="failed",
                mode="real",
                duration_sec=duration_sec,
                error_message=error_msg,
                started_at=started_at,
                ended_at=ended_at,
            )
            raise
    finally:
        db.close()


def recon_body(db: Session, state: AuditState) -> Dict[str, Any]:
    recon_result = run_recon(
        job_id=state.job_id,
        repo_url=state.repo_url,
        branch=state.repo_branch,
        github_token=state.github_access_token or None,
    )
    if recon_result.get("error"):
        raise ValueError(recon_result["error"])

    # Query database for AuthorizationAttestation for current job
    attestation = db.query(AuthorizationAttestation).filter(AuthorizationAttestation.job_id == state.job_id).first()
    attestation_accepted = attestation is not None
    authorization_scope = attestation.authorization_scope if attestation else "passive-only"

    # Check docker availability
    manager = SandboxManager()
    docker_available = (manager.client is not None)

    # Generate ScanPlan
    from backend.app.orchestrator.scan_plan import generate_scan_plan
    plan = generate_scan_plan(
        clone_path=recon_result["clone_path"],
        attestation_accepted=attestation_accepted,
        authorization_scope=authorization_scope,
        docker_available=docker_available
    )

    updates = {
        "clone_path": recon_result["clone_path"],
        "tech_stack": recon_result["tech_stack"],
        "entry_points": recon_result["entry_points"],
        "dependency_manifests": recon_result["dependency_manifests"],
        "scan_plan": plan.model_dump(),
        "scanner_execution": {
            "recon": {"status": "executed", "mode": "real" if "example/" not in state.repo_url else "simulated", "tool": "git"}
        },
    }
    apply_runtime_updates(updates)
    log_agent_message(
        db,
        state.job_id,
        "RECON",
        f"Cloned repository. Tech stack detected: {recon_result['tech_stack']}. Scan plan resolved: {plan.execution_depth}",
    )
    return updates


def recon_node(state: AuditState) -> Dict[str, Any]:
    return execute_phase(
        state,
        phase_name="recon",
        agent_name="RECON",
        start_message="Starting code clone and structure analysis...",
        body=recon_body,
    )


def sast_body(db: Session, state: AuditState) -> Dict[str, Any]:
    if not state.clone_path:
        raise ValueError("No clone path found in AuditState")

    findings = run_sast(state.clone_path, state.repo_url)
    persist_findings(db, state.job_id, findings)
    log_agent_message(db, state.job_id, "SAST", f"Static analysis complete. Found {len(findings)} issues.")
    return {
        "static_findings": findings,
        "scanner_execution": {"regex_sast": {"status": "executed", "mode": "regex", "tool": "built-in regex"}},
    }


def sast_node(state: AuditState) -> Dict[str, Any]:
    return execute_phase(
        state,
        phase_name="sast",
        agent_name="SAST",
        start_message="Starting static security analysis (Semgrep, Gitleaks, regex scanners)...",
        body=sast_body,
    )


def sandbox_body(db: Session, state: AuditState) -> Dict[str, Any]:
    manager = SandboxManager()
    success, _, _, kali_container_id, target_ip = manager.provision_sandbox(
        job_id=state.job_id,
        clone_path=state.clone_path,
        entry_points=state.entry_points,
    )
    if not success:
        raise RuntimeError("Sandbox provisioning failed")

    updates = {
        "sandbox_container_id": kali_container_id,
        "sandbox_target_ip": target_ip,
        "sandbox_ready": True,
        "scanner_execution": {
            "sandbox": {"status": "executed", "mode": "simulation" if manager.mock_mode else "docker", "tool": "docker"}
        },
    }
    apply_runtime_updates(updates)
    log_agent_message(db, state.job_id, "SANDBOX", f"Sandbox ready. Target host: {target_ip}, Kali Container: {kali_container_id}")
    return updates


def sandbox_node(state: AuditState) -> Dict[str, Any]:
    return execute_phase(
        state,
        phase_name="sandbox",
        agent_name="SANDBOX",
        start_message="Provisioning Kali pentesting pod and target app container...",
        body=sandbox_body,
    )


def network_body(db: Session, state: AuditState) -> Dict[str, Any]:
    open_ports = run_network_scan(state.sandbox_container_id, state.sandbox_target_ip)
    log_agent_message(db, state.job_id, "NETWORK", f"Port scan completed. Active ports: {[p['port'] for p in open_ports]}")

    from backend.app.config import settings
    if state.api_surface:
        api_endpoints = [ep["path"] for ep in state.api_surface if ep.get("path")][:settings.API_DISCOVERY_LIMIT]
    else:
        if any("fastapi" in stack.lower() or "python" in stack.lower() for stack in state.tech_stack):
            api_endpoints = ["/api/v1/profile", "/api/v1/users"]
        elif any("node" in stack.lower() for stack in state.tech_stack):
            api_endpoints = ["/api/profile", "/api/users"]
        else:
            api_endpoints = ["/"]

    return {
        "open_ports": open_ports,
        "api_endpoints": api_endpoints,
        "scanner_execution": {
            "network": {"status": "executed", "mode": "simulated" if "fc-kali-" in state.sandbox_container_id else "real", "tool": "nmap"}
        },
    }


def network_node(state: AuditState) -> Dict[str, Any]:
    return execute_phase(
        state,
        phase_name="network",
        agent_name="NETWORK",
        start_message=f"Scanning sandbox target IP ({state.sandbox_target_ip}) ports...",
        body=network_body,
    )


def attack_body(db: Session, state: AuditState) -> Dict[str, Any]:
    findings = run_dynamic_attack(
        kali_container_id=state.sandbox_container_id,
        target_host=state.sandbox_target_ip,
        open_ports=state.open_ports,
        repo_url=state.repo_url,
    )
    persist_findings(db, state.job_id, findings)

    if findings:
        log_agent_message(db, state.job_id, "ATTACK", f"Dynamic attack completed. Found {len(findings)} vulnerability alerts.", "WARNING")
    else:
        log_agent_message(db, state.job_id, "ATTACK", "Completed active tests. No dynamic vulnerabilities detected.")

    return {
        "dynamic_findings": findings,
        "scanner_execution": {
            "dynamic": {"status": "executed" if state.open_ports else "skipped", "mode": "simulated" if "fc-kali-" in state.sandbox_container_id else "real", "tool": "sqlmap/nuclei"}
        },
    }


def attack_node(state: AuditState) -> Dict[str, Any]:
    return execute_phase(
        state,
        phase_name="attack",
        agent_name="ATTACK",
        start_message="Launching active OWASP Top 10 vulnerability checks inside sandbox...",
        body=attack_body,
    )


def exploit_body(db: Session, state: AuditState) -> Dict[str, Any]:
    proofs = run_exploit_validation(
        kali_container_id=state.sandbox_container_id,
        target_host=state.sandbox_target_ip,
        dynamic_findings=state.dynamic_findings,
        repo_url=state.repo_url,
    )
    persist_findings(db, state.job_id, proofs)

    if proofs:
        log_agent_message(db, state.job_id, "EXPLOIT", f"Controlled validation evidence collected for {len(proofs)} issues.", "WARNING")
    else:
        log_agent_message(db, state.job_id, "EXPLOIT", "No exploits could be verified.")

    return {"exploit_proofs": proofs}


def exploit_node(state: AuditState) -> Dict[str, Any]:
    return execute_phase(
        state,
        phase_name="exploit",
        agent_name="EXPLOIT",
        start_message="Attempting safe verification of dynamic vulnerabilities...",
        body=exploit_body,
    )


def scoring_body(db: Session, state: AuditState) -> Dict[str, Any]:
    scored_findings: list[Finding] = []
    total_score = 0.0

    db_findings = db.query(FindingModel).filter(FindingModel.job_id == state.job_id).all()
    for db_finding in db_findings:
        score = 9.8 if db_finding.severity == Severity.CRITICAL else (8.5 if db_finding.severity == Severity.HIGH else 5.0)
        vector = (
            "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
            if db_finding.severity == Severity.CRITICAL
            else "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N"
        )
        db_finding.cvss_score = score
        db_finding.cvss_vector = vector
        scored_findings.append(
            Finding(
                id=db_finding.id,
                agent_source=db_finding.agent_source,
                title=db_finding.title,
                description=db_finding.description,
                severity=db_finding.severity,
                cvss_score=score,
                cvss_vector=vector,
                evidence=db_finding.evidence,
                remediation=db_finding.remediation,
                cwe_id=db_finding.cwe_id,
                owasp_category=db_finding.owasp_category,
            )
        )
        total_score += score

    db.commit()
    risk_summary = {
        "cve_count": len(scored_findings),
        "max_cvss_score": max((finding.cvss_score or 0.0) for finding in scored_findings) if scored_findings else 0.0,
        "average_risk_rating": total_score / len(scored_findings) if scored_findings else 0.0,
    }
    log_agent_message(db, state.job_id, "SCORING", f"Calculated scores. Max CVSS detected: {risk_summary['max_cvss_score']}")
    return {"scored_findings": scored_findings, "risk_summary": risk_summary}


def scoring_node(state: AuditState) -> Dict[str, Any]:
    return execute_phase(
        state,
        phase_name="scoring",
        agent_name="SCORING",
        start_message="Computing CVSS v3.1 vector strings and business risk scores...",
        body=scoring_body,
    )


def reporter_body(db: Session, state: AuditState) -> Dict[str, Any]:
    all_findings = get_reportable_findings(state)

    repo_name = get_clean_repo_name(state.repo_url)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_filename = f"{repo_name}_audit_{timestamp}.pdf"

    reports_dir = os.path.join(WORKSPACE_DIR, "workspace", "reports")
    os.makedirs(reports_dir, exist_ok=True)
    pdf_path = os.path.join(reports_dir, pdf_filename)

    generator = ReportGenerator()
    html_content = generator.generate_html_report(
        job_id=state.job_id,
        repo_url=state.repo_url,
        branch=state.repo_branch,
        findings=all_findings,
        scanner_execution=state.scanner_execution,
    )

    db.add(
        AuditArtifact(
            job_id=state.job_id,
            artifact_type="report_html",
            name=pdf_filename.replace(".pdf", ".html"),
            data_text=html_content,
        )
    )
    db.commit()

    success = generator.compile_pdf(html_content, pdf_path)
    if not success:
        raise RuntimeError("Failed to compile report PDF.")

    # Upload report as a private artifact
    from backend.app.services.storage import storage_service
    db_job = db.query(AuditJob).filter(AuditJob.id == state.job_id).first()
    tenant_id = db_job.tenant_id if db_job and db_job.tenant_id else "default-tenant"
    user_id = db_job.user_id if db_job else None

    artifact = storage_service.upload_artifact(
        db=db,
        file_data=Path(pdf_path),
        organization_id=tenant_id,
        artifact_type="report_pdf",
        file_name=pdf_filename,
        user_id=user_id,
        job_id=state.job_id,
        sensitivity_level="restricted",
    )
    pdf_url = f"artifact://{artifact.id}"

    user_email = "audit-recipient@firecrow.dev"
    if db_job:
        from backend.app.models.user import User
        user = db.query(User).filter(User.id == db_job.user_id).first()
        if user and user.email:
            user_email = user.email

    # Generate a presigned URL specifically for the email link (valid for 7 days)
    email_url = pdf_url
    if storage_service.is_s3_active():
        try:
            email_url = storage_service.get_presigned_url(db, artifact.id, user_id or "system", expires_in=604800)
        except Exception:
            email_url = f"/api/v1/audit/job/{state.job_id}/report"
    else:
        email_url = f"/api/v1/audit/job/{state.job_id}/report"

    counts = {
        Severity.CRITICAL: len([finding for finding in all_findings if finding.severity == Severity.CRITICAL]),
        Severity.HIGH: len([finding for finding in all_findings if finding.severity == Severity.HIGH]),
        Severity.MEDIUM: len([finding for finding in all_findings if finding.severity == Severity.MEDIUM]),
        Severity.LOW: len([finding for finding in all_findings if finding.severity == Severity.LOW]),
        Severity.INFO: len([finding for finding in all_findings if finding.severity == Severity.INFO]),
    }
    generator.send_email_report(user_email, email_url, state.job_id, counts, repo_url=state.repo_url, pdf_path=pdf_path)
    log_agent_message(db, state.job_id, "REPORTER", "Audit report successfully generated.")

    return {
        "report_pdf_url": pdf_url,
        "report_delivered": True,
        "status": JobStatus.COMPLETED,
    }


def reporter_node(state: AuditState) -> Dict[str, Any]:
    return execute_phase(
        state,
        phase_name="reporter",
        agent_name="REPORTER",
        start_message="Generating premium PDF report and transmitting notification emails...",
        body=reporter_body,
    )


def github_mcp_body(db: Session, state: AuditState) -> Dict[str, Any]:
    all_findings = get_reportable_findings(state)
        
    result = run_github_mcp(
        job_id=state.job_id,
        repo_url=state.repo_url,
        findings=all_findings,
        remediations=state.remediations,
        github_token=state.github_access_token or None,
    )
    for log_msg in result.get("github_mcp_logs", []):
        log_agent_message(db, state.job_id, "GITHUB_MCP", log_msg)
    return result


def github_mcp_node(state: AuditState) -> Dict[str, Any]:
    return execute_phase(
        state,
        phase_name="github_mcp",
        agent_name="GITHUB_MCP",
        start_message="Connecting to GitMCP remote server to raise security report issue...",
        body=github_mcp_body,
    )


def google_agent_body(db: Session, state: AuditState) -> Dict[str, Any]:
    all_findings = get_reportable_findings(state)
        
    db_job = db.query(AuditJob).filter(AuditJob.id == state.job_id).first()
    recipient_email = "audit-recipient@firecrow.dev"
    if db_job:
        from backend.app.models.user import User
        user = db.query(User).filter(User.id == db_job.user_id).first()
        if user and user.email:
            recipient_email = user.email

    result = run_google_agent(
        job_id=state.job_id,
        repo_url=state.repo_url,
        findings=all_findings,
        remediations=state.remediations,
        recipient_email=recipient_email
    )
    for log_msg in result.get("google_agent_logs", []):
        log_agent_message(db, state.job_id, "GOOGLE_AGENT", log_msg)
    return result


def google_agent_node(state: AuditState) -> Dict[str, Any]:
    return execute_phase(
        state,
        phase_name="google_agent",
        agent_name="GOOGLE_AGENT",
        start_message="Running Google AI Security Agent to evaluate PR/merge risks and transmit alert notifications...",
        body=google_agent_body,
    )

def dependency_body(db: Session, state: AuditState) -> Dict[str, Any]:
    findings = run_dependency_scan(state.clone_path, state.dependency_manifests)
    persist_findings(db, state.job_id, findings)
    log_agent_message(db, state.job_id, "DEPENDENCY", f"Dependency scan complete. Found {len(findings)} issues.")
    simulated = any("scanner_mode=simulated" in (finding.evidence or "") for finding in findings)
    return {
        "dependency_vulns": findings,
        "scanner_execution": {
            "dependency": {
                "status": "executed" if findings else "unavailable or no findings",
                "mode": "simulated" if simulated else "real" if findings else "unavailable",
                "tool": "osv-scanner/trivy",
            }
        },
    }

def dependency_node(state: AuditState) -> Dict[str, Any]:
    return execute_phase(state, phase_name="dependency_scan", agent_name="DEPENDENCY", start_message="Scanning dependencies...", body=dependency_body)

def iac_body(db: Session, state: AuditState) -> Dict[str, Any]:
    findings = run_iac_scan(state.clone_path)
    persist_findings(db, state.job_id, findings)
    log_agent_message(db, state.job_id, "IAC", f"IaC scan complete. Found {len(findings)} issues.")
    return {"iac_findings": findings}

def iac_node(state: AuditState) -> Dict[str, Any]:
    return execute_phase(state, phase_name="iac_scan", agent_name="IAC", start_message="Scanning IaC...", body=iac_body)

def semgrep_body(db: Session, state: AuditState) -> Dict[str, Any]:
    findings = run_semgrep_scan(state.clone_path, state.tech_stack)
    persist_findings(db, state.job_id, findings)
    log_agent_message(db, state.job_id, "SEMGREP", f"Semgrep scan complete. Found {len(findings)} issues.")
    simulated = any("scanner_mode=simulated" in (finding.evidence or "") for finding in findings)
    return {
        "semgrep_findings": findings,
        "scanner_execution": {
            "semgrep": {
                "status": "executed" if findings else "unavailable or no findings",
                "mode": "simulated" if simulated else "real" if findings else "unavailable",
                "tool": "semgrep",
            }
        },
    }

def semgrep_node(state: AuditState) -> Dict[str, Any]:
    return execute_phase(state, phase_name="semgrep_scan", agent_name="SEMGREP", start_message="Running Semgrep...", body=semgrep_body)

def ai_analyzer_body(db: Session, state: AuditState) -> Dict[str, Any]:
    dedup, fps, chains, rems = run_ai_analyzer(
        state.static_findings,
        state.dynamic_findings,
        state.dependency_vulns,
        state.iac_findings,
        state.semgrep_findings
    )
    log_agent_message(db, state.job_id, "AI_ANALYZER", f"AI Analyzer complete. {len(dedup)} findings retained.")
    return {
        "deduplicated_findings": dedup,
        "false_positives": fps,
        "attack_chains": chains,
        "remediations": rems
    }

def ai_analyzer_node(state: AuditState) -> Dict[str, Any]:
    return execute_phase(state, phase_name="ai_analyzer", agent_name="AI_ANALYZER", start_message="AI brain analyzing...", body=ai_analyzer_body)


def cleanup_body(db: Session, state: AuditState) -> Dict[str, Any]:
    cleanup_resources(state)
    
    # Run a persistent scan to remove non-PDF clutter from the R2 bucket to preserve space
    try:
        from backend.app.services.reporter import ReportGenerator
        generator = ReportGenerator()
        generator.clean_r2_bucket_clutter()
    except Exception as e:
        logger.error(f"Failed to run R2 bucket clutter cleanup: {str(e)}")

    mark_cleanup_completed()
    if state.clone_path:
        log_agent_message(db, state.job_id, "CLEANUP", f"Purged temporary workspace clone directory: {state.clone_path}")
    log_agent_message(db, state.job_id, "CLEANUP", "Resources cleanly deprovisioned.")
    return {}



def cleanup_node(state: AuditState) -> Dict[str, Any]:
    return execute_phase(
        state,
        phase_name="cleanup",
        agent_name="CLEANUP",
        start_message="Tearing down Docker network sandboxes and purging temporary files...",
        body=cleanup_body,
        check_cancel_before=False,
        check_cancel_after=False,
    )


def route_after_semgrep(state: AuditState) -> Literal["ai_analyzer", "sandbox"]:
    if state.scan_plan:
        enabled = state.scan_plan.get("enabled_scanners", [])
        if "sandbox" not in enabled:
            return "ai_analyzer"

    for finding in state.static_findings + state.semgrep_findings:
        if finding.severity == Severity.CRITICAL and "secret" in finding.title.lower():
            return "ai_analyzer"
    return "sandbox"


def route_after_attack(state: AuditState) -> Literal["exploit", "ai_analyzer"]:
    if state.scan_plan:
        enabled = state.scan_plan.get("enabled_scanners", [])
        if "exploit" not in enabled:
            return "ai_analyzer"

    if len(state.dynamic_findings) == 0:
        return "ai_analyzer"
    return "exploit"



def api_surface_node(state: AuditState) -> Dict[str, Any]:
    return execute_phase(state, phase_name="api_surface", agent_name="API_SURFACE", start_message="Mapping API surface...", body=api_surface_body)

def secret_history_node(state: AuditState) -> Dict[str, Any]:
    return execute_phase(state, phase_name="secret_history", agent_name="SECRET_HISTORY", start_message="Scanning git history for secrets...", body=secret_history_body)

def sbom_graph_node(state: AuditState) -> Dict[str, Any]:
    return execute_phase(state, phase_name="sbom_graph", agent_name="SBOM_GRAPH", start_message="Building dependency graph...", body=sbom_graph_body)

def cicd_scan_node(state: AuditState) -> Dict[str, Any]:
    return execute_phase(state, phase_name="cicd_scan", agent_name="CICD_SCAN", start_message="Scanning CI/CD pipelines...", body=cicd_scan_body)

def container_scan_node(state: AuditState) -> Dict[str, Any]:
    return execute_phase(state, phase_name="container_scan", agent_name="CONTAINER_SCAN", start_message="Scanning container configurations...", body=container_scan_body)

def authz_idor_node(state: AuditState) -> Dict[str, Any]:
    return execute_phase(state, phase_name="authz_idor", agent_name="AUTHZ_IDOR", start_message="Analyzing authorization and IDOR risks...", body=authz_idor_body)

def attack_graph_node(state: AuditState) -> Dict[str, Any]:
    return execute_phase(state, phase_name="attack_graph", agent_name="ATTACK_GRAPH", start_message="Building correlated attack graph...", body=attack_graph_body)

def remediation_planner_node(state: AuditState) -> Dict[str, Any]:
    return execute_phase(state, phase_name="remediation_planner", agent_name="REMEDIATION_PLANNER", start_message="Generating remediation plans...", body=remediation_planner_body)

def create_maestro_graph() -> CompiledStateGraph:
    builder = StateGraph(AuditState)

    builder.add_node("recon", recon_node)
    builder.add_node("api_surface", api_surface_node)
    builder.add_node("secret_history", secret_history_node)
    builder.add_node("dependency", dependency_node)
    builder.add_node("sbom_graph", sbom_graph_node)
    builder.add_node("iac", iac_node)
    builder.add_node("cicd_scan", cicd_scan_node)
    builder.add_node("container_scan", container_scan_node)
    builder.add_node("sast", sast_node)
    builder.add_node("semgrep", semgrep_node)
    builder.add_node("authz_idor", authz_idor_node)
    builder.add_node("sandbox", sandbox_node)
    builder.add_node("network", network_node)
    builder.add_node("attack", attack_node)
    builder.add_node("exploit", exploit_node)
    builder.add_node("ai_analyzer", ai_analyzer_node)
    builder.add_node("scoring", scoring_node)
    builder.add_node("attack_graph", attack_graph_node)
    builder.add_node("remediation_planner", remediation_planner_node)
    builder.add_node("reporter", reporter_node)
    builder.add_node("github_mcp", github_mcp_node)
    builder.add_node("google_agent", google_agent_node)
    builder.add_node("cleanup", cleanup_node)

    builder.add_edge(START, "recon")
    builder.add_edge("recon", "api_surface")
    builder.add_edge("api_surface", "secret_history")
    builder.add_edge("secret_history", "dependency")
    builder.add_edge("dependency", "sbom_graph")
    builder.add_edge("sbom_graph", "iac")
    builder.add_edge("iac", "cicd_scan")
    builder.add_edge("cicd_scan", "container_scan")
    builder.add_edge("container_scan", "sast")
    builder.add_edge("sast", "semgrep")
    builder.add_edge("semgrep", "authz_idor")

    # After authz_idor, conditionally route to ai_analyzer or sandbox
    builder.add_conditional_edges("authz_idor", route_after_semgrep, {"ai_analyzer": "ai_analyzer", "sandbox": "sandbox"})

    builder.add_edge("sandbox", "network")
    builder.add_edge("network", "attack")
    builder.add_conditional_edges("attack", route_after_attack, {"exploit": "exploit", "ai_analyzer": "ai_analyzer"})
    builder.add_edge("exploit", "ai_analyzer")
    builder.add_edge("ai_analyzer", "scoring")
    builder.add_edge("scoring", "attack_graph")
    builder.add_edge("attack_graph", "remediation_planner")
    builder.add_edge("remediation_planner", "reporter")
    builder.add_edge("reporter", "github_mcp")
    builder.add_edge("github_mcp", "google_agent")
    builder.add_edge("google_agent", "cleanup")
    builder.add_edge("cleanup", END)

    return builder.compile()


maestro_graph = create_maestro_graph()
