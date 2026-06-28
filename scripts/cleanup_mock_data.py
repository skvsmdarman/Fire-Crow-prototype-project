from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Iterable


WORKSPACE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = WORKSPACE_DIR / "firecrow.db"

USER_PREDICATES = (
    "lower(username) like 'mock_%'",
    "lower(username) like 'smoke_%'",
    "lower(username) like 'stress_%'",
    "lower(username) like 'demo_%'",
    "lower(email) like 'mock-%@firecrow.dev'",
    "lower(email) like 'smoke-%@firecrow.dev'",
    "lower(email) like 'stress-%@firecrow.dev'",
    "lower(email) like '%@example.com'",
)

JOB_PREDICATES = (
    "lower(repo_url) like '%octocat/%'",
    "lower(repo_url) like '%hello-world%'",
    "lower(repo_url) like '%github.com/example/%'",
    "lower(repo_url) like '%example.com%'",
    "lower(repo_url) like '%/demo%'",
)


def table_exists(cursor: sqlite3.Cursor, table_name: str) -> bool:
    row = cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def fetch_ids(cursor: sqlite3.Cursor, sql: str, params: Iterable[str] = ()) -> list[str]:
    return [row[0] for row in cursor.execute(sql, tuple(params)).fetchall()]


def delete_matching(cursor: sqlite3.Cursor, summary: dict[str, int], table: str, column: str, ids: list[str]) -> None:
    if not ids or not table_exists(cursor, table):
        return
    placeholders = ",".join("?" for _ in ids)
    sql = f"DELETE FROM {table} WHERE {column} IN ({placeholders})"
    cursor.execute(sql, ids)
    summary[table] = summary.get(table, 0) + cursor.rowcount


def main() -> int:
    parser = argparse.ArgumentParser(description="Remove local smoke/mock/demo Fire Crow records from SQLite.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db_path = Path(args.db_path).expanduser().resolve()
    if not db_path.exists():
        print(f"[FAIL] database not found: {db_path}")
        return 1

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    summary: dict[str, int] = {}

    user_where = " OR ".join(USER_PREDICATES)
    user_ids = fetch_ids(cursor, f"SELECT id FROM users WHERE {user_where}") if table_exists(cursor, "users") else []

    job_where = " OR ".join(JOB_PREDICATES)
    job_ids = fetch_ids(cursor, f"SELECT id FROM audit_jobs WHERE {job_where}") if table_exists(cursor, "audit_jobs") else []
    if user_ids and table_exists(cursor, "audit_jobs"):
        placeholders = ",".join("?" for _ in user_ids)
        job_ids.extend(fetch_ids(cursor, f"SELECT id FROM audit_jobs WHERE user_id IN ({placeholders})", user_ids))
    job_ids = sorted(set(job_ids))

    if args.dry_run:
        print(f"users={len(user_ids)} jobs={len(job_ids)} db={db_path}")
        conn.close()
        return 0

    try:
        cursor.execute("BEGIN")

        for table_name in (
            "audit_reports",
            "findings",
            "agent_logs",
            "audit_artifacts",
            "phase_ledger",
            "secret_redaction_events",
        ):
            delete_matching(cursor, summary, table_name, "job_id", job_ids)

        if table_exists(cursor, "artifact_objects") and job_ids:
            delete_matching(cursor, summary, "artifact_objects", "job_id", job_ids)

        if table_exists(cursor, "authorization_attestations"):
            delete_matching(cursor, summary, "authorization_attestations", "job_id", job_ids)
            delete_matching(cursor, summary, "authorization_attestations", "user_id", user_ids)

        if table_exists(cursor, "compliance_events"):
            delete_matching(cursor, summary, "compliance_events", "job_id", job_ids)
            delete_matching(cursor, summary, "compliance_events", "actor_user_id", user_ids)
            delete_matching(cursor, summary, "compliance_events", "subject_user_id", user_ids)

        for table_name in (
            "user_sessions",
            "auth_exchange_codes",
            "push_subscriptions",
            "memberships",
            "security_logs",
            "data_processing_records",
            "privacy_requests",
        ):
            column_name = {
                "privacy_requests": "requester_user_id",
            }.get(table_name, "user_id")
            delete_matching(cursor, summary, table_name, column_name, user_ids)

        delete_matching(cursor, summary, "audit_jobs", "id", job_ids)
        delete_matching(cursor, summary, "users", "id", user_ids)

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print(f"database={db_path}")
    if not summary:
        print("No smoke/mock/demo rows matched cleanup rules.")
        return 0

    for table_name in sorted(summary):
        print(f"{table_name}={summary[table_name]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
