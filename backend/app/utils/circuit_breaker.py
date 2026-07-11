from __future__ import annotations

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger("firecrow.utils.circuit_breaker")

T = TypeVar("T")


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_retries: int = 3,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_retries = half_open_max_retries

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.half_open_retries = 0
        self.last_failure_time: Optional[float] = None
        self.last_success_time: Optional[float] = None

    async def call(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        if self.state == CircuitState.OPEN:
            if self._recovery_timeout_elapsed():
                logger.info("Circuit %s transitioning from OPEN to HALF_OPEN", self.name)
                self.state = CircuitState.HALF_OPEN
                self.half_open_retries = 0
            else:
                raise CircuitBreakerOpenError(f"Circuit {self.name} is OPEN")

        try:
            result = await fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        self.last_success_time = time.monotonic()
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_retries += 1
            if self.half_open_retries >= self.half_open_max_retries:
                logger.info("Circuit %s transitioning from HALF_OPEN to CLOSED", self.name)
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.half_open_retries = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def _on_failure(self) -> None:
        self.last_failure_time = time.monotonic()
        self.failure_count += 1
        if self.state == CircuitState.HALF_OPEN:
            logger.warning("Circuit %s HALF_OPEN retry failed. Returning to OPEN", self.name)
            self.state = CircuitState.OPEN
            self.half_open_retries = 0
        elif self.failure_count >= self.failure_threshold:
            logger.warning(
                "Circuit %s OPEN (failures=%d/%d)",
                self.name, self.failure_count, self.failure_threshold,
            )
            self.state = CircuitState.OPEN

    def _recovery_timeout_elapsed(self) -> bool:
        if self.last_failure_time is None:
            return True
        return (time.monotonic() - self.last_failure_time) >= self.recovery_timeout

    def reset(self) -> None:
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.half_open_retries = 0
        self.last_failure_time = None

    @property
    def is_available(self) -> bool:
        return self.state != CircuitState.OPEN

    def stats(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "last_failure_time": self.last_failure_time,
            "last_success_time": self.last_success_time,
        }


class CircuitBreakerOpenError(Exception):
    pass


# Global circuit breaker registry
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str) -> CircuitBreaker:
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name=name)
    return _circuit_breakers[name]


def circuit_breaker(name: str):
    cb = get_circuit_breaker(name)
    return cb
