from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Any

from backend.app.schemas import AuditState

ADDITIVE_LIST_FIELDS = {
    "phase_history",
    "static_findings",
    "secrets_detected",
    "cve_matches",
    "open_ports",
    "api_endpoints",
    "tls_issues",
    "dynamic_findings",
    "exploit_proofs",
    "scored_findings",
    "errors",
}


class JobCancellationRequested(Exception):
    """Raised when a job has a persisted cancel request and should finalize cleanly."""


@dataclass
class RuntimeTracker:
    state: dict[str, Any]
    cleanup_completed: bool = False


_runtime_tracker: ContextVar[RuntimeTracker | None] = ContextVar("firecrow_runtime_tracker", default=None)


def initialize_runtime_tracker(initial_state: AuditState) -> Token:
    tracker = RuntimeTracker(state=initial_state.model_dump(mode="python"))
    return _runtime_tracker.set(tracker)


def reset_runtime_tracker(token: Token) -> None:
    _runtime_tracker.reset(token)


def get_runtime_tracker() -> RuntimeTracker | None:
    return _runtime_tracker.get()


def sync_runtime_state(state: AuditState | dict[str, Any]) -> None:
    tracker = get_runtime_tracker()
    if tracker is None:
        return

    if isinstance(state, AuditState):
        tracker.state = state.model_dump(mode="python")
    else:
        tracker.state = AuditState.model_validate(state).model_dump(mode="python")


def apply_runtime_updates(updates: dict[str, Any]) -> None:
    tracker = get_runtime_tracker()
    if tracker is None:
        return

    for key, value in updates.items():
        if key in ADDITIVE_LIST_FIELDS and isinstance(value, list):
            existing = tracker.state.get(key) or []
            tracker.state[key] = [*existing, *value]
        elif key == "scanner_execution" and isinstance(value, dict):
            existing = tracker.state.get(key) or {}
            tracker.state[key] = {**existing, **value}
        else:
            tracker.state[key] = value


def get_runtime_state() -> AuditState:
    tracker = get_runtime_tracker()
    if tracker is None:
        raise RuntimeError("Runtime tracker is not initialized.")
    return AuditState.model_validate(tracker.state)


def mark_cleanup_completed() -> None:
    tracker = get_runtime_tracker()
    if tracker is None:
        return
    tracker.cleanup_completed = True
