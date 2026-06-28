import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from app.services.neo4j_migration import (
    create_constraints_and_indexes,
    migrate_users,
    migrate_audit_jobs,
    migrate_security_logs,
)
from app.models.user import User
from app.models.audit_job import AuditJob, FindingModel, AgentLog
from app.models.security_log import SecurityLog


@patch("app.services.neo4j_migration.execute_query")
def test_create_constraints_and_indexes(mock_execute):
    create_constraints_and_indexes()
    assert mock_execute.call_count == 7


def make_mock_db():
    db_mock = MagicMock(spec=Session)
    
    # We will build a helper that returns different mocks depending on the model query.
    def mock_query(model):
        query_mock = MagicMock()
        if model == User:
            user_mock = MagicMock(spec=User)
            user_mock.id = "usr_1"
            user_mock.username = "test_user"
            user_mock.email = "test@example.com"
            user_mock.created_at = None
            query_mock.all.return_value = [user_mock]
        elif model == AuditJob:
            job_mock = MagicMock(spec=AuditJob)
            job_mock.id = "job_1"
            job_mock.repo_url = "https://github.com/test/repo"
            job_mock.status = "completed"
            job_mock.created_at = None
            job_mock.finished_at = None
            job_mock.user_id = "usr_1"
            query_mock.all.return_value = [job_mock]
            query_mock.filter.return_value.all.return_value = [job_mock]
        elif model == FindingModel:
            finding_mock = MagicMock(spec=FindingModel)
            finding_mock.id = "find_1"
            finding_mock.title = "XSS Vulnerability"
            finding_mock.severity = "high"
            finding_mock.cwe_id = "CWE-79"
            finding_mock.agent_source = "semgrep"
            finding_mock.evidence = "alert(1)"
            finding_mock.job_id = "job_1"
            query_mock.filter.return_value.all.return_value = [finding_mock]
            query_mock.all.return_value = [finding_mock]
        elif model == AgentLog:
            log_mock = MagicMock(spec=AgentLog)
            log_mock.id = "log_1"
            log_mock.agent_name = "MAESTRO"
            log_mock.message = "started"
            log_mock.timestamp = None
            log_mock.job_id = "job_1"
            query_mock.filter.return_value.all.return_value = [log_mock]
            query_mock.all.return_value = [log_mock]
        elif model == SecurityLog:
            sec_mock = MagicMock(spec=SecurityLog)
            sec_mock.id = "sec_1"
            sec_mock.action = "login"
            sec_mock.ip_address = "127.0.0.1"
            sec_mock.timestamp = None
            sec_mock.details = "successful login"
            sec_mock.user_id = "usr_1"
            query_mock.all.return_value = [sec_mock]
            query_mock.filter.return_value.all.return_value = [sec_mock]
        return query_mock

    db_mock.query.side_effect = mock_query
    return db_mock


@patch("app.services.neo4j_migration.execute_query")
def test_migrate_users(mock_execute):
    db_mock = make_mock_db()
    count = migrate_users(db_mock)
    assert count == 1
    assert mock_execute.called


@patch("app.services.neo4j_migration.execute_query")
def test_migrate_audit_jobs(mock_execute):
    db_mock = make_mock_db()
    count = migrate_audit_jobs(db_mock)
    assert count == 1
    assert mock_execute.called


@patch("app.services.neo4j_migration.execute_query")
def test_migrate_security_logs(mock_execute):
    db_mock = make_mock_db()
    count = migrate_security_logs(db_mock)
    assert count == 1
    assert mock_execute.called
