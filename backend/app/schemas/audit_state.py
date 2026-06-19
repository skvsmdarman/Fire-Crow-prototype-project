from enum import Enum
from typing import Optional, Annotated, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field as PydanticField
import operator


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


def merge_dicts(dict1: dict[str, Any] | None, dict2: dict[str, Any] | None) -> dict[str, Any]:
    """Reducer function to merge dictionaries in LangGraph state."""
    d1 = dict1 or {}
    d2 = dict2 or {}
    return {**d1, **d2}


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Finding(BaseModel):
    id: str
    agent_source: str
    title: str
    description: str
    severity: Severity
    cvss_vector: Optional[str] = None
    cvss_score: Optional[float] = None
    evidence: Optional[str] = None
    remediation: Optional[str] = None
    cwe_id: Optional[str] = None
    owasp_category: Optional[str] = None
    confidence: Optional[str] = None
    scanner_name: Optional[str] = None
    scanner_mode: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    route: Optional[str] = None
    metadata_json: Optional[str] = None


class AuditState(BaseModel):
    # --- Job Identity ---
    job_id: str = ""
    user_id: str = ""
    repo_url: str = ""
    repo_branch: str = "main"
    repo_owner: str = ""
    repo_name: str = ""
    github_access_token: str = ""
    github_token_scopes: list[str] = []
    created_at: datetime = PydanticField(default_factory=get_utc_now)
    custom_email: str = ""

    # --- Phase Tracking ---
    current_phase: str = "intake"
    status: JobStatus = JobStatus.QUEUED
    phase_history: Annotated[list[dict], operator.add] = []

    # --- RECON outputs ---
    clone_path: str = ""
    tech_stack: list[str] = []
    entry_points: list[str] = []
    dependency_manifests: list[str] = []
    repo_security: dict[str, Any] = {}
    threat_model: dict[str, Any] = {}
    sbom: dict[str, Any] = {}
    dependency_vulns: Annotated[list[Finding], operator.add] = []
    iac_findings: Annotated[list[Finding], operator.add] = []

    # --- API SURFACE outputs ---
    api_surface: list[dict[str, Any]] = []
    route_risk_summary: dict[str, Any] = {}

    # --- SBOM outputs ---
    sbom_components: list[dict[str, Any]] = []
    dependency_graph: dict[str, Any] = {}
    vulnerable_components: list[dict[str, Any]] = []

    # --- CI/CD outputs ---
    cicd_findings: Annotated[list[Finding], operator.add] = []

    # --- CONTAINER outputs ---
    container_findings: Annotated[list[Finding], operator.add] = []

    # --- AUTHZ outputs ---
    authz_findings: Annotated[list[Finding], operator.add] = []

    # --- SAST outputs ---
    static_findings: Annotated[list[Finding], operator.add] = []
    semgrep_findings: Annotated[list[Finding], operator.add] = []
    secret_findings: Annotated[list[Finding], operator.add] = []
    secret_history_findings: Annotated[list[Finding], operator.add] = []
    bandit_findings: Annotated[list[Finding], operator.add] = []
    cve_matches: Annotated[list[dict], operator.add] = []
    normalized_findings: Annotated[list[dict[str, Any]], operator.add] = []

    # --- SANDBOX ---
    sandbox_container_id: str = ""
    sandbox_target_ip: str = ""
    sandbox_ready: bool = False

    # --- NETWORK outputs ---
    open_ports: Annotated[list[dict], operator.add] = []
    api_endpoints: Annotated[list[str], operator.add] = []
    tls_issues: Annotated[list[dict], operator.add] = []

    # --- ATTACK outputs ---
    dynamic_findings: Annotated[list[Finding], operator.add] = []

    # --- EXPLOIT outputs ---
    exploit_proofs: Annotated[list[Finding], operator.add] = []

    # --- AI ANALYZER outputs ---
    deduplicated_findings: Annotated[list[Finding], operator.add] = []
    false_positives: Annotated[list[str], operator.add] = []
    attack_chains: Annotated[list[dict[str, Any]], operator.add] = []
    remediations: Annotated[list[dict[str, Any]], operator.add] = []

    # --- ATTACK GRAPH outputs ---
    attack_graph: dict[str, Any] = {}

    # --- REMEDIATION outputs ---
    remediation_plan: dict[str, Any] = {}
    remediation_tasks: list[dict[str, Any]] = []

    # --- CROSS-VALIDATION outputs ---
    validated_findings: Annotated[list[Finding], operator.add] = []
    correlation_report: list[dict[str, Any]] = []

    # --- SCORING outputs ---
    scored_findings: Annotated[list[Finding], operator.add] = []
    risk_summary: dict[str, Any] = {}
    confidence_summary: dict[str, Any] = {}

    # --- REPORTER outputs ---
    report_pdf_url: str = ""
    report_delivered: bool = False

    # --- GITHUB MCP outputs ---
    github_issue_created: bool = False
    github_pr_created: bool = False
    github_pr_url: str = ""
    github_branch: str = ""
    github_mcp_logs: list[str] = []

    # --- GOOGLE AGENT outputs ---
    google_agent_delivered: bool = False
    google_agent_pr_risks_analyzed: bool = False
    google_agent_logs: Annotated[list[str], operator.add] = []
    google_agent_risk_report: dict[str, Any] = {}

    # --- Error Tracking ---
    errors: Annotated[list[dict], operator.add] = []
    retry_counts: Annotated[dict[str, int], merge_dicts] = {}
    scanner_execution: Annotated[dict[str, Any], merge_dicts] = {}

    # --- Scan Plan ---
    scan_plan: Optional[dict] = None

    # --- Resource Budget ---
    max_scan_duration_sec: int = 2700
    budget_remaining_usd: float = 5.0
