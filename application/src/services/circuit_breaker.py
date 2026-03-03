"""Simple in-memory circuit breaker for GenAI calls.

States:
    CLOSED    — normal operation
    OPEN      — blocking calls after N failures in window
    HALF_OPEN — testing recovery after circuit_timeout expires

Environment variables:
    GENAI_FAILURE_THRESHOLD  — int, default 5
    GENAI_CIRCUIT_TIMEOUT    — seconds before OPEN → HALF_OPEN, default 300
"""
import logging
import os
import time
from collections import deque

log = logging.getLogger(__name__)


class CircuitBreaker:
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

    def __init__(
        self,
        failure_threshold: int | None = None,
        window_seconds: int = 60,
        circuit_timeout_seconds: int | None = None,
    ) -> None:
        self.failure_threshold = failure_threshold or int(
            os.environ.get("GENAI_FAILURE_THRESHOLD", "5")
        )
        self.window_seconds = window_seconds
        self.circuit_timeout_seconds = circuit_timeout_seconds or int(
            os.environ.get("GENAI_CIRCUIT_TIMEOUT", "300")
        )
        self._state = self.CLOSED
        self._failure_times: deque[float] = deque()
        self._opened_at: float = 0.0
        log.debug(
            "CircuitBreaker ready: threshold=%d window=%ds timeout=%ds",
            self.failure_threshold,
            self.window_seconds,
            self.circuit_timeout_seconds,
        )

    def is_open(self) -> bool:
        """True → caller should skip the protected operation."""
        if self._state == self.CLOSED:
            return False
        if self._state == self.OPEN:
            elapsed = time.monotonic() - self._opened_at
            if elapsed >= self.circuit_timeout_seconds:
                self._state = self.HALF_OPEN
                log.info("CircuitBreaker → HALF_OPEN after %ds", int(elapsed))
                return False  # allow one test request
            return True
        # HALF_OPEN — allow the test request through
        return False

    def record_success(self) -> None:
        if self._state in (self.HALF_OPEN, self.OPEN):
            self._state = self.CLOSED
            self._failure_times.clear()
            log.info("CircuitBreaker → CLOSED (recovery successful)")

    def record_failure(self) -> None:
        now = time.monotonic()
        if self._state == self.HALF_OPEN:
            self._state = self.OPEN
            self._opened_at = now
            log.warning("CircuitBreaker → OPEN (HALF_OPEN test failed)")
            return
        # Prune failures outside the sliding window
        cutoff = now - self.window_seconds
        while self._failure_times and self._failure_times[0] < cutoff:
            self._failure_times.popleft()
        self._failure_times.append(now)
        if len(self._failure_times) >= self.failure_threshold:
            self._state = self.OPEN
            self._opened_at = now
            log.warning(
                "CircuitBreaker → OPEN (%d failures in last %ds)",
                len(self._failure_times),
                self.window_seconds,
            )

    @property
    def state(self) -> str:
        return self._state

    def reset(self) -> None:
        """Manually reset — useful for tests."""
        self._state = self.CLOSED
        self._failure_times.clear()
        self._opened_at = 0.0
