import pytest
import uuid
import os
from dotenv import dotenv_values
from datetime import datetime, timezone
from sqlalchemy import or_, and_
from neo4j import GraphDatabase
from backend.app.models.database import Neo4jSession
from backend.app.models.user import User
from backend.app.models.audit_job import AuditJob, AgentLog, FindingModel
from backend.app.models.security_log import SecurityLog
from backend.app.schemas.audit_state import JobStatus, Severity

# Load credentials directly from .env.local to bypass conftest.py override
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env.local")
config = dotenv_values(env_path)
NEO4J_URI = config.get("NEO4J_URI")
NEO4J_USERNAME = config.get("NEO4J_USERNAME")
NEO4J_PASSWORD = config.get("NEO4J_PASSWORD")

# Skip all tests in this file if Neo4j is not configured in .env.local
pytestmark = pytest.mark.skipif(
    not NEO4J_URI,
    reason="Neo4j is not configured in .env.local"
)

@pytest.fixture(scope="module")
def neo4j_driver():
    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
    )
    driver.verify_connectivity()
    yield driver
    driver.close()

@pytest.fixture(scope="module")
def db_session(neo4j_driver):
    db = Neo4jSession(neo4j_driver)
    yield db
    # Clean up created test nodes
    with neo4j_driver.session() as session:
        session.run("MATCH (n:User) WHERE n.username STARTS WITH 'test_neo4j_user_' DETACH DELETE n")
        session.run("MATCH (j:AuditJob) WHERE j.id STARTS WITH 'test_neo4j_job_' DETACH DELETE j")
        session.run("MATCH (f:FindingModel) WHERE f.id STARTS WITH 'test_neo4j_finding_' DETACH DELETE f")
        session.run("MATCH (l:AgentLog) WHERE l.job_id STARTS WITH 'test_neo4j_job_' DETACH DELETE l")
        session.run("MATCH (s:SecurityLog) WHERE s.user_id STARTS WITH 'test_neo4j_user_' DETACH DELETE s")

def test_neo4j_crud_operations(db_session, neo4j_driver):
    # 1. Create a user
    user_id = f"test_neo4j_user_{uuid.uuid4().hex[:6]}"
    username = f"test_neo4j_user_{uuid.uuid4().hex[:6]}"
    user = User(
        id=user_id,
        username=username,
        email="test_neo4j@example.com",
        password_hash="hashedpassword",
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(user)
    db_session.commit()

    # 2. Query the user back
    retrieved = db_session.query(User).filter(User.username == username).first()
    assert retrieved is not None
    assert retrieved.id == user_id
    assert retrieved.email == "test_neo4j@example.com"
    assert isinstance(retrieved.created_at, datetime)

    # 2b. Add a SecurityLog without setting id or timestamp (test default resolution)
    sec_log = SecurityLog(
        user_id=user_id,
        action="login_success",
        ip_address="127.0.0.1",
        user_agent="pytest"
    )
    db_session.add(sec_log)
    db_session.commit()

    assert sec_log.id is not None
    assert sec_log.timestamp is not None

    # 3. Add an AuditJob owned by the user
    job_id = f"test_neo4j_job_{uuid.uuid4().hex[:6]}"
    job = AuditJob(
        id=job_id,
        user_id=user_id,
        repo_url="https://github.com/example/repo",
        repo_branch="main",
        status=JobStatus.QUEUED,
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(job)
    db_session.commit()

    # Verify job node and relationship [:OWNED_BY]
    retrieved_job = db_session.query(AuditJob).filter(AuditJob.id == job_id).first()
    assert retrieved_job is not None
    assert retrieved_job.user_id == user_id

    # Test setting attributes on retrieved models (descriptor check)
    retrieved_job.status = JobStatus.RUNNING
    db_session.add(retrieved_job)
    db_session.commit()

    # Verify it updated in database
    updated_job = db_session.query(AuditJob).filter(AuditJob.id == job_id).first()
    assert updated_job.status == JobStatus.RUNNING

    with neo4j_driver.session() as session:
        res = session.run(
            "MATCH (j:AuditJob {id: $job_id})-[:OWNED_BY]->(u:User {id: $user_id}) RETURN j, u",
            job_id=job_id, user_id=user_id
        )
        record = res.single()
        assert record is not None

    # 4. Add AgentLog and FindingModel related to the job
    log = AgentLog(
        job_id=job_id,
        agent_name="ReconAgent",
        log_level="INFO",
        message="Running initial repository scan",
        timestamp=datetime.now(timezone.utc)
    )
    finding_id = f"test_neo4j_finding_{uuid.uuid4().hex[:6]}"
    finding = FindingModel(
        id=finding_id,
        job_id=job_id,
        agent_source="ReconAgent",
        title="Hardcoded API Key",
        description="A secret key was found in source code.",
        severity=Severity.HIGH,
        created_at=datetime.now(timezone.utc)
    )

    db_session.add(log)
    db_session.add(finding)
    db_session.commit()

    # Verify AgentLog monotonic ID assignment and relationship
    assert log.id is not None
    assert log.id > 0

    with neo4j_driver.session() as session:
        # Check logs and findings relationships
        res_log = session.run(
            "MATCH (l:AgentLog {id: $log_id})-[:LOGGED_FOR]->(j:AuditJob {id: $job_id}) RETURN l, j",
            log_id=log.id, job_id=job_id
        )
        assert res_log.single() is not None

        res_finding = session.run(
            "MATCH (f:FindingModel {id: $finding_id})-[:BELONGS_TO]->(j:AuditJob {id: $job_id}) RETURN f, j",
            finding_id=finding_id, job_id=job_id
        )
        assert res_finding.single() is not None

    # 5. Test Filters and Queries
    # Test query count
    cnt = db_session.query(User).filter(User.username == username).count()
    assert cnt == 1

    # Test ordering
    jobs = db_session.query(AuditJob).filter(AuditJob.user_id == user_id).order_by(AuditJob.created_at).all()
    assert len(jobs) == 1
    assert jobs[0].id == job_id

    # Test limit and offset
    users = db_session.query(User).filter(User.username == username).limit(1).offset(0).all()
    assert len(users) == 1
    assert users[0].id == user_id

    # Test SQLAlchemy in_ operator
    retrieved_in = db_session.query(User).filter(User.id.in_([user_id, "other_id"])).all()
    assert len(retrieved_in) == 1

    # Test SQLAlchemy ne (not equal) operator
    retrieved_ne = db_session.query(User).filter(User.id != "some_other_random_id", User.username == username).all()
    assert len(retrieved_ne) == 1

    # Test pattern matching (like)
    substring = username[5:10]
    retrieved_like = db_session.query(User).filter(User.username.like(f"%{substring}%")).all()
    assert len(retrieved_like) > 0

    # Test logical operators or_ and and_
    retrieved_logical = db_session.query(User).filter(
        or_(
            User.username == username,
            User.email == "nonexistent@example.com"
        )
    ).all()
    assert len(retrieved_logical) == 1

    retrieved_and = db_session.query(User).filter(
        and_(
            User.username == username,
            User.email == "test_neo4j@example.com"
        )
    ).all()
    assert len(retrieved_and) == 1

    # 6. Delete nodes and verify
    db_session.delete(finding)
    db_session.delete(log)
    db_session.delete(job)
    db_session.delete(sec_log)
    db_session.delete(user)
    db_session.commit()

    # Verify they are gone
    assert db_session.query(User).filter(User.username == username).first() is None
    assert db_session.query(AuditJob).filter(AuditJob.id == job_id).first() is None
