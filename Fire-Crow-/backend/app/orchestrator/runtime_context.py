from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Any

from app.schemas import AuditState

import operator
from typing import get_args, get_origin, Annotated

def _resolve_additive_fields() -> set[str]:
    additive = set()
    for name, field in AuditState.model_fields.items():
        ann = field.annotation
        if ann is not None and get_origin(ann) is Annotated:
            for arg in get_args(ann)[1:]:
                if arg is operator.add:
                    additive.add(name)
    return additive

ADDITIVE_LIST_FIELDS = _resolve_additive_fields()


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
