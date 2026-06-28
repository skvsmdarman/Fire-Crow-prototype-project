import logging
from typing import Any
from sqlalchemy.orm import Session as SASession
from app.services.neo4j_client import execute_query, verify_connectivity
from app.models.audit_job import AuditJob, FindingModel, AgentLog
from app.models.user import User
from app.models.security_log import SecurityLog

logger = logging.getLogger("firecrow.services.neo4j_migration")

GRAPH_SCHEMA = """
Graph Database Schema — Fire Crow (PostgreSQL → Neo4j Migration)

Nodes:
- User        (id, username, email, created_at)
- AuditJob    (id, repo_url, status, created_at, completed_at)
- Finding     (id, title, severity, cwe_id, agent_source, evidence)
- AgentLog    (id, agent_name, message, created_at)
- SecurityLog (id, action, ip_address, timestamp)
- Organization (id, name)

Relationships:
- (:User)-[:OWNS]->(:AuditJob)
- (:User)-[:HAS_LOG]->(:SecurityLog)
- (:AuditJob)-[:HAS_FINDING]->(:Finding)
- (:AuditJob)-[:HAS_AGENT_LOG]->(:AgentLog)
- (:User)-[:MEMBER_OF]->(:Organization)
"""


def create_constraints_and_indexes():
    constraints = [
        "CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE",
        "CREATE CONSTRAINT audit_job_id IF NOT EXISTS FOR (j:AuditJob) REQUIRE j.id IS UNIQUE",
        "CREATE CONSTRAINT finding_id IF NOT EXISTS FOR (f:Finding) REQUIRE f.id IS UNIQUE",
        "CREATE CONSTRAINT security_log_id IF NOT EXISTS FOR (s:SecurityLog) REQUIRE s.id IS UNIQUE",
        "CREATE INDEX user_email IF NOT EXISTS FOR (u:User) ON (u.email)",
        "CREATE INDEX audit_job_status IF NOT EXISTS FOR (j:AuditJob) ON (j.status)",
        "CREATE INDEX finding_severity IF NOT EXISTS FOR (f:Finding) ON (f.severity)",
    ]
    for cql in constraints:
        try:
            execute_query(cql)
        except Exception as e:
            logger.warning("Constraint/index creation skipped: %s", e)
    logger.info("Neo4j constraints and indexes applied.")


def migrate_users(db: SASession) -> int:
    users = db.query(User).all()
    count = 0
    for user in users:
        cql = """
        MERGE (u:User {id: $id})
        SET u.username = $username,
            u.email = $email,
            u.created_at = $created_at
        """
        execute_query(cql, {
            "id": user.id,
            "username": user.username,
            "email": user.email or "",
            "created_at": str(user.created_at) if user.created_at is not None else None,
        })
        count += 1
    logger.info("Migrated %d users to Neo4j.", count)
    return count


def migrate_audit_jobs(db: SASession, user_id: str | None = None) -> int:
    query = db.query(AuditJob)
    if user_id:
        query = query.filter(AuditJob.user_id == user_id)

    jobs = query.all()
    count = 0
    for job in jobs:
        cql = """
        MERGE (j:AuditJob {id: $id})
        SET j.repo_url = $repo_url,
            j.status = $status,
            j.created_at = $created_at,
            j.completed_at = $completed_at
        WITH j
        MATCH (u:User {id: $user_id})
        MERGE (u)-[:OWNS]->(j)
        """
        execute_query(cql, {
            "id": job.id,
            "repo_url": job.repo_url or "",
            "status": job.status or "",
            "created_at": str(job.created_at) if job.created_at is not None else None,
            "completed_at": str(job.finished_at) if job.finished_at is not None else None,
            "user_id": job.user_id,
        })

        findings = db.query(FindingModel).filter(FindingModel.job_id == job.id).all()
        for finding in findings:
            f_cql = """
            MERGE (f:Finding {id: $id})
            SET f.title = $title,
                f.severity = $severity,
                f.cwe_id = $cwe_id,
                f.agent_source = $agent_source,
                f.evidence = $evidence
            WITH f
            MATCH (j:AuditJob {id: $job_id})
            MERGE (j)-[:HAS_FINDING]->(f)
            """
            execute_query(f_cql, {
                "id": finding.id,
                "title": finding.title or "",
                "severity": str(finding.severity) if finding.severity else "",
                "cwe_id": finding.cwe_id or "",
                "agent_source": finding.agent_source or "",
                "evidence": finding.evidence or "",
                "job_id": job.id,
            })

        agent_logs = db.query(AgentLog).filter(AgentLog.job_id == job.id).all()
        for log in agent_logs:
            l_cql = """
            MERGE (l:AgentLog {id: $id})
            SET l.agent_name = $agent_name,
                l.message = $message,
                l.created_at = $created_at
            WITH l
            MATCH (j:AuditJob {id: $job_id})
            MERGE (j)-[:HAS_AGENT_LOG]->(l)
            """
            execute_query(l_cql, {
                "id": log.id,
                "agent_name": log.agent_name or "",
                "message": log.message or "",
                "created_at": str(log.timestamp) if log.timestamp is not None else None,
                "job_id": job.id,
            })
        count += 1
    logger.info("Migrated %d audit jobs (with findings and logs) to Neo4j.", count)
    return count


def migrate_security_logs(db: SASession) -> int:
    logs = db.query(SecurityLog).all()
    count = 0
    for log in logs:
        cql = """
        MERGE (s:SecurityLog {id: $id})
        SET s.action = $action,
            s.ip_address = $ip_address,
            s.timestamp = $timestamp,
            s.details = $details
        """
        execute_query(cql, {
            "id": log.id,
            "action": log.action,
            "ip_address": log.ip_address or "",
            "timestamp": str(log.timestamp) if log.timestamp is not None else None,
            "details": log.details or "",
        })

        if log.user_id is not None:
            rel_cql = """
            MATCH (s:SecurityLog {id: $log_id})
            MATCH (u:User {id: $user_id})
            MERGE (u)-[:HAS_LOG]->(s)
            """
            execute_query(rel_cql, {"log_id": log.id, "user_id": log.user_id})
        count += 1
    logger.info("Migrated %d security logs to Neo4j.", count)
    return count


def run_full_migration(db: SASession) -> dict[str, Any]:
    if not verify_connectivity():
        return {"success": False, "error": "Neo4j connectivity check failed."}

    create_constraints_and_indexes()

    stats = {
        "users": migrate_users(db),
        "audit_jobs": migrate_audit_jobs(db),
        "security_logs": migrate_security_logs(db),
    }

    logger.info("Full migration completed: %s", stats)
    return {"success": True, "stats": stats}


def find_jobs_by_user(user_id: str) -> list[dict]:
    cql = """
    MATCH (u:User {id: $user_id})-[:OWNS]->(j:AuditJob)
    OPTIONAL MATCH (j)-[:HAS_FINDING]->(f:Finding)
    RETURN j.id AS job_id, j.repo_url AS repo_url, j.status AS status,
           j.created_at AS created_at, count(f) AS finding_count
    ORDER BY j.created_at DESC
    """
    return execute_query(cql, {"user_id": user_id})
