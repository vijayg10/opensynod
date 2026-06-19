"""Tests for the circuit breaker."""

import time

import pytest
from app.llm.circuit_breaker import CircuitBreaker, CircuitState


def test_starts_closed():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)
    assert cb.state == CircuitState.CLOSED
    assert not cb.is_open()


def test_trips_after_threshold():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.is_open()


def test_success_resets_failure_count():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)
    cb.record_failure()
    cb.record_failure()
    cb.record_success()
    # Success resets count, so 2 more failures should not trip
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED


def test_transitions_to_half_open_after_timeout():
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.001)
    cb.record_failure()
    assert cb.state == CircuitState.OPEN

    # Backdate the failure time so the recovery timeout has elapsed
    cb._last_failure_time = time.monotonic() - 1.0
    assert cb.state == CircuitState.HALF_OPEN


def test_reset():
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60.0)
    cb.record_failure()
    assert cb.is_open()
    cb.reset()
    assert cb.state == CircuitState.CLOSED
    assert not cb.is_open()


def test_success_in_half_open_closes_breaker(monkeypatch):
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.0)
    cb.record_failure()
    # Force half-open
    cb._last_failure_time = time.monotonic() - 100.0
    assert cb.state == CircuitState.HALF_OPEN
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
