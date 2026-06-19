"""Simple circuit breaker for LLM provider clients."""

from __future__ import annotations

import time
from enum import Enum


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Tripped: fast-fail
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """Per-provider circuit breaker.

    Trips after `failure_threshold` consecutive failures.
    After `recovery_timeout` seconds, allows one probe request (HALF_OPEN).
    Resets to CLOSED on success; re-trips on failure in HALF_OPEN.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float | None = None

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if (
                self._last_failure_time is not None
                and time.monotonic() - self._last_failure_time >= self.recovery_timeout
            ):
                self._state = CircuitState.HALF_OPEN
        return self._state

    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN

    def record_success(self) -> None:
        self._failure_count = 0
        self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN

    def reset(self) -> None:
        self._failure_count = 0
        self._state = CircuitState.CLOSED
        self._last_failure_time = None
