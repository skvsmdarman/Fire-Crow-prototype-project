from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Iterable, Optional

from app.graph.database import neo4j_session
from app.schemas.audit_state import JobStatus, Severity


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_now() -> str:
    return _utc_now().isoformat()


def _parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if hasattr(value, "iso_format"):
        return datetime.fromisoformat(value.iso_format())
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _coerce_job_status(value: Any) -> JobStatus:
    if isinstance(value, JobStatus):
        return value
    return JobStatus(str(value).lower())


def _coerce_severity(value: Any) -> Severity:
    if isinstance(value, Severity):
        return value
    return Severity(str(value).lower())


def _node_props(node: Any) -> dict[str, Any]:
    if node is None:
        return {}
    return dict(node.items()) if hasattr(node, "items") else dict(node)


def _json_loads(value: str | None) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


@dataclass
class GraphUser:
    id: str
    username: str
    password_hash: str | None = None
    credit_balance: float = 10.0
    email: str | None = None
    tenant_id: str | None = None
    role_id: str | None = None
    role_name: str | None = None
    is_active: bool = True
    github_id: str | None = None
    github_access_token: str | None = None
    github_token_scopes: str | None = None
    github_token_updated_at: datetime | None = None
    privacy_policy_version: str | None = None
    privacy_policy_accepted_at: datetime | None = None
    terms_version: str | None = None
    terms_accepted_at: datetime | None = None
    first_login_at: datetime | None = None
    last_login_at: datetime | None = None
    last_logout_at: datetime | None = None
    region: str | None = None
    timezone: str | None = None
    created_at: datetime | None = None

    @property
    def is_admin(self) -> bool:
        return (self.role_name or "").lower() in {"admin", "owner", "security_admin", "platform_admin", "superadmin"}


@dataclass
class GraphAgentLog:
    id: str
    job_id: str
    agent_name: str
    log_level: str
    message: str
    timestamp: datetime | None = None


@dataclass
class GraphPhaseLedger:
    id: str
    job_id: str
    phase_name: str
    status: str
    mode: str | None = None
    duration_sec: float | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None


@dataclass
class GraphFinding:
    id: str
    job_id: str
    agent_source: str
    title: str
    description: str
    severity: Severity
    cvss_vector: str | None = None
    cvss_score: float | None = None
    evidence: str | None = None
    remediation: str | None = None
    cwe_id: str | None = None
    owasp_category: str | None = None
    confidence: str | None = None
    scanner_name: str | None = None
    scanner_mode: str | None = None
    file_path: str | None = None
    line_number: int | None = None
    route: str | None = None
    metadata_json: str | None = None
    created_at: datetime | None = None


@dataclass
class GraphArtifact:
    id: str
    job_id: str
    artifact_type: str
    name: str
    data_json: str | None = None
    data_text: str | None = None
    created_at: datetime | None = None


@dataclass
class GraphAuditJob:
    id: str
    user_id: str
    repo_url: str
    repo_branch: str
    status: JobStatus
    created_at: datetime
    tenant_id: str | None = None
    finished_at: datetime | None = None
    cancel_requested: bool = False
    cancel_requested_at: datetime | None = None
    report_pdf_url: str | None = None
    report_id: str | None = None
    error_message: str | None = None
    security_score: float | None = None
    legal_hold: bool = False
    phase_ledger: list[GraphPhaseLedger] = field(default_factory=list)
    logs: list[GraphAgentLog] = field(default_factory=list)


def _build_user(props: dict[str, Any], role_name: str | None = None) -> GraphUser:
    return GraphUser(
        id=props["id"],
        username=props["username"],
        password_hash=props.get("passwordHash"),
        credit_balance=float(props.get("creditBalance") or 10.0),
        email=props.get("email"),
        tenant_id=props.get("tenantId"),
        role_id=props.get("roleId"),
        role_name=role_name,
        is_active=bool(props.get("isActive", True)),
        github_id=props.get("githubId"),
        github_access_token=props.get("githubAccessToken"),
        github_token_scopes=props.get("githubTokenScopes"),
        github_token_updated_at=_parse_datetime(props.get("githubTokenUpdatedAt")),
        privacy_policy_version=props.get("privacyPolicyVersion"),
        privacy_policy_accepted_at=_parse_datetime(props.get("privacyPolicyAcceptedAt")),
        terms_version=props.get("termsVersion"),
        terms_accepted_at=_parse_datetime(props.get("termsAcceptedAt")),
        first_login_at=_parse_datetime(props.get("firstLoginAt")),
        last_login_at=_parse_datetime(props.get("lastLoginAt")),
        last_logout_at=_parse_datetime(props.get("lastLogoutAt")),
        region=props.get("region"),
        timezone=props.get("timezone"),
        created_at=_parse_datetime(props.get("createdAt")),
    )


def _build_agent_log(props: dict[str, Any]) -> GraphAgentLog:
    return GraphAgentLog(
        id=str(props.get("id") or ""),
        job_id=props["jobId"],
        agent_name=props.get("agentName", ""),
        log_level=props.get("logLevel", "INFO"),
        message=props.get("message", ""),
        timestamp=_parse_datetime(props.get("timestamp")),
    )


def _build_phase(props: dict[str, Any]) -> GraphPhaseLedger:
    return GraphPhaseLedger(
        id=props["id"],
        job_id=props["jobId"],
        phase_name=props.get("phaseName", ""),
        status=props.get("status", ""),
        mode=props.get("mode"),
        duration_sec=props.get("durationSec"),
        error_message=props.get("errorMessage"),
        started_at=_parse_datetime(props.get("startedAt")),
        ended_at=_parse_datetime(props.get("endedAt")),
    )


def _build_job(props: dict[str, Any], phases: Iterable[dict[str, Any]] | None = None, logs: Iterable[dict[str, Any]] | None = None) -> GraphAuditJob:
    return GraphAuditJob(
        id=props["id"],
        user_id=props["userId"],
        tenant_id=props.get("tenantId"),
        repo_url=props["repoUrl"],
        repo_branch=props.get("repoBranch") or "main",
        status=_coerce_job_status(props.get("status") or JobStatus.QUEUED),
        created_at=_parse_datetime(props.get("createdAt")) or _utc_now(),
        finished_at=_parse_datetime(props.get("finishedAt")),
        cancel_requested=bool(props.get("cancelRequested", False)),
        cancel_requested_at=_parse_datetime(props.get("cancelRequestedAt")),
        report_pdf_url=props.get("reportPdfUrl"),
        report_id=props.get("reportId"),
        error_message=props.get("errorMessage"),
        security_score=props.get("securityScore"),
        legal_hold=bool(props.get("legalHold", False)),
        phase_ledger=[_build_phase(p) for p in phases or [] if p and p.get("id")],
        logs=[_build_agent_log(l) for l in logs or [] if l and l.get("jobId")],
    )


def _build_finding(props: dict[str, Any]) -> GraphFinding:
    return GraphFinding(
        id=props["id"],
        job_id=props["jobId"],
        agent_source=props.get("agentSource", ""),
        title=props.get("title", ""),
        description=props.get("description", ""),
        severity=_coerce_severity(props.get("severity") or Severity.INFO),
        cvss_vector=props.get("cvssVector"),
        cvss_score=props.get("cvssScore"),
        evidence=props.get("evidence"),
        remediation=props.get("remediation"),
        cwe_id=props.get("cweId"),
        owasp_category=props.get("owaspCategory"),
        confidence=props.get("confidence"),
        scanner_name=props.get("scannerName"),
        scanner_mode=props.get("scannerMode"),
        file_path=props.get("filePath"),
        line_number=props.get("lineNumber"),
        route=props.get("route"),
        metadata_json=props.get("metadataJson"),
        created_at=_parse_datetime(props.get("createdAt")),
    )


def _build_artifact(props: dict[str, Any]) -> GraphArtifact:
    return GraphArtifact(
        id=props["id"],
        job_id=props["jobId"],
        artifact_type=props.get("artifactType", ""),
        name=props.get("name", ""),
        data_json=props.get("dataJson"),
        data_text=props.get("dataText"),
        created_at=_parse_datetime(props.get("createdAt")),
    )


class GraphStore:
    def get_user_by_id(self, user_id: str) -> GraphUser | None:
        query = """
        MATCH (u:User {id: $user_id})
        OPTIONAL MATCH (u)-[:HAS_ROLE]->(r:Role)
        RETURN u, r.name AS role_name
        LIMIT 1
        """
        with neo4j_session() as session:
            record = session.run(query, user_id=user_id).single()
        if not record:
            return None
        return _build_user(_node_props(record["u"]), record["role_name"])

    def get_user_by_username(self, username: str) -> GraphUser | None:
        query = """
        MATCH (u:User {username: $username})
        OPTIONAL MATCH (u)-[:HAS_ROLE]->(r:Role)
        RETURN u, r.name AS role_name
        LIMIT 1
        """
        with neo4j_session() as session:
            record = session.run(query, username=username).single()
        if not record:
            return None
        return _build_user(_node_props(record["u"]), record["role_name"])

    def get_user_by_github_id(self, github_id: str) -> GraphUser | None:
        with neo4j_session() as session:
            record = session.run(
                """
                MATCH (u:User {githubId: $github_id})
                OPTIONAL MATCH (u)-[:HAS_ROLE]->(r:Role)
                RETURN u, r.name AS role_name
                LIMIT 1
                """,
                github_id=github_id,
            ).single()
        if not record:
            return None
        return _build_user(_node_props(record["u"]), record["role_name"])

    def find_users_by_email(self, email: str) -> list[GraphUser]:
        with neo4j_session() as session:
            records = session.run(
                """
                MATCH (u:User)
                OPTIONAL MATCH (u)-[:HAS_ROLE]->(r:Role)
                WHERE toLower(u.email) = toLower($email)
                RETURN u, r.name AS role_name
                """,
                email=email,
            )
            return [_build_user(_node_props(record["u"]), record["role_name"]) for record in records]

    def username_exists(self, username: str) -> bool:
        with neo4j_session() as session:
            record = session.run("MATCH (u:User {username: $username}) RETURN count(u) AS count", username=username).single()
        return bool(record and record["count"] > 0)

    def email_exists(self, email: str) -> bool:
        with neo4j_session() as session:
            record = session.run(
                "MATCH (u:User) WHERE toLower(u.email) = toLower($email) RETURN count(u) AS count",
                email=email,
            ).single()
        return bool(record and record["count"] > 0)

    def persist_user(self, user: GraphUser) -> GraphUser:
        props = {
            "username": user.username,
            "passwordHash": user.password_hash,
            "creditBalance": user.credit_balance,
            "email": user.email,
            "tenantId": user.tenant_id,
            "roleId": user.role_id,
            "isActive": user.is_active,
            "githubId": user.github_id,
            "githubAccessToken": user.github_access_token,
            "githubTokenScopes": user.github_token_scopes,
            "githubTokenUpdatedAt": user.github_token_updated_at.isoformat() if user.github_token_updated_at else None,
            "privacyPolicyVersion": user.privacy_policy_version,
            "privacyPolicyAcceptedAt": user.privacy_policy_accepted_at.isoformat() if user.privacy_policy_accepted_at else None,
            "termsVersion": user.terms_version,
            "termsAcceptedAt": user.terms_accepted_at.isoformat() if user.terms_accepted_at else None,
            "firstLoginAt": user.first_login_at.isoformat() if user.first_login_at else None,
            "lastLoginAt": user.last_login_at.isoformat() if user.last_login_at else None,
            "lastLogoutAt": user.last_logout_at.isoformat() if user.last_logout_at else None,
            "region": user.region,
            "timezone": user.timezone,
            "createdAt": user.created_at.isoformat() if user.created_at else _iso_now(),
        }
        with neo4j_session() as session:
            session.run(
                """
                MERGE (u:User {id: $id})
                SET u += $props
                """,
                id=user.id,
                props=props,
            )
        return user

    def create_user_activity(self, user_id: str, action: str, details_json: str | None) -> None:
        with neo4j_session() as session:
            session.run(
                """
                MATCH (u:User {id: $user_id})
                CREATE (e:UserActivityEvent {
                    id: $id,
                    userId: $user_id,
                    action: $action,
                    detailsJson: $details_json,
                    createdAt: $created_at
                })
                MERGE (u)-[:HAS_ACTIVITY]->(e)
                """,
                id=str(uuid.uuid4()),
                user_id=user_id,
                action=action,
                details_json=details_json,
                created_at=_iso_now(),
            )

    def list_user_activities(self, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        with neo4j_session() as session:
            records = session.run(
                """
                MATCH (:User {id: $user_id})-[:HAS_ACTIVITY]->(e:UserActivityEvent)
                RETURN e
                ORDER BY e.createdAt DESC
                LIMIT $limit
                """,
                user_id=user_id,
                limit=limit,
            )
            results: list[dict[str, Any]] = []
            for record in records:
                props = _node_props(record["e"])
                item = {
                    "action": props.get("action"),
                    "timestamp": props.get("createdAt"),
                }
                payload = _json_loads(props.get("detailsJson"))
                if payload is not None:
                    item["details"] = payload
                results.append(item)
            return results

    def create_security_log(self, user_id: str | None, action: str, ip_address: str | None, user_agent: str | None, details: str | None) -> None:
        with neo4j_session() as session:
            session.run(
                """
                CREATE (s:SecurityLog {
                    id: $id,
                    userId: $user_id,
                    action: $action,
                    ipAddress: $ip_address,
                    userAgent: $user_agent,
                    timestamp: $timestamp,
                    details: $details
                })
                """,
                id=str(uuid.uuid4()),
                user_id=user_id,
                action=action,
                ip_address=ip_address,
                user_agent=user_agent,
                timestamp=_iso_now(),
                details=details,
            )

    def create_user_session(self, *, session_id: str, user_id: str, token_family: str, ip_hash: str, user_agent_hash: str, expires_at: datetime) -> None:
        with neo4j_session() as session:
            session.run(
                """
                MATCH (u:User {id: $user_id})
                MERGE (s:UserSession {id: $session_id})
                SET s.userId = $user_id,
                    s.tokenFamily = $token_family,
                    s.ipHash = $ip_hash,
                    s.userAgentHash = $user_agent_hash,
                    s.createdAt = $created_at,
                    s.expiresAt = $expires_at,
                    s.isRevoked = false
                MERGE (u)-[:HAS_SESSION]->(s)
                """,
                session_id=session_id,
                user_id=user_id,
                token_family=token_family,
                ip_hash=ip_hash,
                user_agent_hash=user_agent_hash,
                created_at=_iso_now(),
                expires_at=expires_at.isoformat(),
            )

    def get_user_session(self, session_id: str) -> SimpleNamespace | None:
        with neo4j_session() as session:
            record = session.run("MATCH (s:UserSession {id: $session_id}) RETURN s LIMIT 1", session_id=session_id).single()
        if not record:
            return None
        props = _node_props(record["s"])
        return SimpleNamespace(
            id=props["id"],
            user_id=props.get("userId"),
            token_family=props.get("tokenFamily"),
            expires_at=_parse_datetime(props.get("expiresAt")) or _utc_now(),
            is_revoked=bool(props.get("isRevoked", False)),
            revocation_reason=props.get("revocationReason"),
        )

    def set_session_revoked(self, session_id: str, reason: str) -> bool:
        with neo4j_session() as session:
            record = session.run(
                """
                MATCH (s:UserSession {id: $session_id})
                SET s.isRevoked = true, s.revocationReason = $reason
                RETURN count(s) AS count
                """,
                session_id=session_id,
                reason=reason,
            ).single()
        return bool(record and record["count"] > 0)

    def get_active_sessions_by_family(self, token_family: str) -> list[SimpleNamespace]:
        with neo4j_session() as session:
            records = session.run(
                """
                MATCH (s:UserSession {tokenFamily: $token_family})
                WHERE coalesce(s.isRevoked, false) = false
                RETURN s
                """,
                token_family=token_family,
            )
            sessions: list[SimpleNamespace] = []
            for record in records:
                props = _node_props(record["s"])
                sessions.append(
                    SimpleNamespace(
                        id=props["id"],
                        expires_at=_parse_datetime(props.get("expiresAt")) or _utc_now(),
                    )
                )
            return sessions

    def revoke_token_family(self, token_family: str, reason: str) -> int:
        with neo4j_session() as session:
            record = session.run(
                """
                MATCH (s:UserSession {tokenFamily: $token_family})
                WHERE coalesce(s.isRevoked, false) = false
                SET s.isRevoked = true, s.revocationReason = $reason
                RETURN count(s) AS count
                """,
                token_family=token_family,
                reason=reason,
            ).single()
        return int(record["count"]) if record else 0

    def delete_expired_exchange_codes(self, now: datetime) -> None:
        with neo4j_session() as session:
            session.run(
                """
                MATCH (c:AuthExchangeCode)
                WHERE c.expiresAt <= $now
                DETACH DELETE c
                """,
                now=now.isoformat(),
            )

    def create_exchange_code(self, code: str, user_id: str, username: str, access_token: str, expires_at: datetime) -> None:
        with neo4j_session() as session:
            session.run(
                """
                CREATE (c:AuthExchangeCode {
                    code: $code,
                    userId: $user_id,
                    username: $username,
                    accessToken: $access_token,
                    createdAt: $created_at,
                    expiresAt: $expires_at
                })
                """,
                code=code,
                user_id=user_id,
                username=username,
                access_token=access_token,
                created_at=_iso_now(),
                expires_at=expires_at.isoformat(),
            )

    def consume_exchange_code(self, code: str, now: datetime) -> dict[str, Any] | None:
        with neo4j_session() as session:
            session.run(
                """
                MATCH (c:AuthExchangeCode)
                WHERE c.expiresAt <= $now
                DETACH DELETE c
                """,
                now=now.isoformat(),
            )
            record = session.run(
                """
                MATCH (c:AuthExchangeCode {code: $code})
                RETURN c
                LIMIT 1
                """,
                code=code,
            ).single()
            if not record:
                return None
            props = _node_props(record["c"])
            expires_at = _parse_datetime(props.get("expiresAt"))
            if not expires_at or expires_at <= now:
                session.run("MATCH (c:AuthExchangeCode {code: $code}) DETACH DELETE c", code=code)
                return None
            payload = {
                "user_id": props.get("userId"),
                "username": props.get("username"),
                "access_token": props.get("accessToken"),
            }
            session.run("MATCH (c:AuthExchangeCode {code: $code}) DETACH DELETE c", code=code)
            return payload

    def record_login_failure(self, key_hash: str, attempted_at: datetime) -> None:
        with neo4j_session() as session:
            session.run(
                """
                CREATE (l:LoginFailure {
                    id: $id,
                    keyHash: $key_hash,
                    attemptedAt: $attempted_at
                })
                """,
                id=str(uuid.uuid4()),
                key_hash=key_hash,
                attempted_at=attempted_at.isoformat(),
            )

    def count_recent_login_failures(self, key_hash: str, window_start: datetime) -> int:
        with neo4j_session() as session:
            session.run(
                """
                MATCH (l:LoginFailure)
                WHERE l.attemptedAt < $window_start
                DETACH DELETE l
                """,
                window_start=window_start.isoformat(),
            )
            record = session.run(
                """
                MATCH (l:LoginFailure {keyHash: $key_hash})
                WHERE l.attemptedAt >= $window_start
                RETURN count(l) AS count
                """,
                key_hash=key_hash,
                window_start=window_start.isoformat(),
            ).single()
        return int(record["count"]) if record else 0

    def clear_login_failures(self, key_hash: str) -> None:
        with neo4j_session() as session:
            session.run("MATCH (l:LoginFailure {keyHash: $key_hash}) DETACH DELETE l", key_hash=key_hash)

    def get_tenant_by_slug(self, slug: str) -> SimpleNamespace | None:
        with neo4j_session() as session:
            record = session.run(
                "MATCH (t:Tenant {slug: $slug}) WHERE coalesce(t.isActive, true) = true RETURN t LIMIT 1",
                slug=slug,
            ).single()
        if not record:
            return None
        props = _node_props(record["t"])
        return SimpleNamespace(id=props["id"], slug=props.get("slug"), is_active=bool(props.get("isActive", True)))

    def list_jobs_for_user(self, user_id: str) -> list[GraphAuditJob]:
        query = """
        MATCH (u:User {id: $user_id})
        OPTIONAL MATCH (m:Membership)-[:ASSIGNED_TO_USER]->(u)
        WITH u, collect(DISTINCT m.organizationId) + CASE WHEN u.tenantId IS NULL THEN [] ELSE [u.tenantId] END AS org_ids
        MATCH (j:AuditJob)
        WHERE j.userId = $user_id OR (j.tenantId IS NOT NULL AND j.tenantId IN org_ids)
        OPTIONAL MATCH (j)<-[:PART_OF]-(p:PhaseLedger)
        OPTIONAL MATCH (j)<-[:LOGGED_IN]-(l:AgentLog)
        RETURN j, collect(DISTINCT p) AS phases, collect(DISTINCT l) AS logs
        ORDER BY j.createdAt DESC
        """
        with neo4j_session() as session:
            records = session.run(query, user_id=user_id)
            return [
                _build_job(_node_props(record["j"]), [_node_props(p) for p in record["phases"]], [_node_props(l) for l in record["logs"]])
                for record in records
            ]

    def get_owned_job(self, user_id: str, job_id: str) -> GraphAuditJob | None:
        query = """
        MATCH (u:User {id: $user_id})
        OPTIONAL MATCH (m:Membership)-[:ASSIGNED_TO_USER]->(u)
        WITH u, collect(DISTINCT m.organizationId) + CASE WHEN u.tenantId IS NULL THEN [] ELSE [u.tenantId] END AS org_ids
        MATCH (j:AuditJob {id: $job_id})
        WHERE j.userId = $user_id OR (j.tenantId IS NOT NULL AND j.tenantId IN org_ids)
        OPTIONAL MATCH (j)<-[:PART_OF]-(p:PhaseLedger)
        OPTIONAL MATCH (j)<-[:LOGGED_IN]-(l:AgentLog)
        RETURN j, collect(DISTINCT p) AS phases, collect(DISTINCT l) AS logs
        LIMIT 1
        """
        with neo4j_session() as session:
            record = session.run(query, user_id=user_id, job_id=job_id).single()
        if not record:
            return None
        return _build_job(_node_props(record["j"]), [_node_props(p) for p in record["phases"]], [_node_props(l) for l in record["logs"]])

    def list_findings_for_job(self, job_id: str) -> list[GraphFinding]:
        with neo4j_session() as session:
            records = session.run(
                """
                MATCH (f:Finding)-[:FOUND_IN]->(:AuditJob {id: $job_id})
                RETURN f
                ORDER BY f.createdAt ASC
                """,
                job_id=job_id,
            )
            return [_build_finding(_node_props(record["f"])) for record in records]

    def get_artifact_for_job(self, job_id: str, artifact_type: str) -> GraphArtifact | None:
        with neo4j_session() as session:
            record = session.run(
                """
                MATCH (a:AuditArtifact {artifactType: $artifact_type})-[:BELONGS_TO_JOB]->(:AuditJob {id: $job_id})
                RETURN a
                ORDER BY a.createdAt DESC
                LIMIT 1
                """,
                job_id=job_id,
                artifact_type=artifact_type,
            ).single()
        if not record:
            return None
        return _build_artifact(_node_props(record["a"]))


graph_store = GraphStore()
