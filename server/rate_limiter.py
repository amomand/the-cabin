"""Per-IP rate limiting for The Cabin web server."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class _IPBucket:
    """Sliding-window counters for a single IP address."""
    message_timestamps: list = field(default_factory=list)
    connection_timestamps: list = field(default_factory=list)


class RateLimiter:
    """Rate limiter with per-IP message and connection limits.

    Limits:
      - ``max_messages_per_min`` messages per IP per minute (default 20)
      - ``max_connections_per_min`` new WebSocket connections per IP per minute (default 3)
      - ``max_sessions`` total concurrent sessions globally (default 50)
      - ``max_input_length`` maximum characters in a single message (default 200)
      - ``session_timeout`` seconds of idle before a session is considered expired (default 3600)
    """

    def __init__(
        self,
        *,
        max_messages_per_min: int = 20,
        max_connections_per_min: int = 3,
        max_sessions: int = 50,
        max_input_length: int = 200,
        session_timeout: int = 3600,
    ) -> None:
        self.max_messages_per_min = max_messages_per_min
        self.max_connections_per_min = max_connections_per_min
        self.max_sessions = max_sessions
        self.max_input_length = max_input_length
        self.session_timeout = session_timeout

        self._buckets: Dict[str, _IPBucket] = defaultdict(_IPBucket)
        self._active_sessions: int = 0

    # -- Connection limits ----------------------------------------------------

    def can_connect(self, ip: str) -> bool:
        """Check whether a new WebSocket connection from *ip* is allowed."""
        if self._active_sessions >= self.max_sessions:
            return False

        now = time.monotonic()
        bucket = self._buckets[ip]
        cutoff = now - 60
        bucket.connection_timestamps = [
            t for t in bucket.connection_timestamps if t > cutoff
        ]
        return len(bucket.connection_timestamps) < self.max_connections_per_min

    def register_connection(self, ip: str) -> None:
        """Record a new connection from *ip*."""
        self._buckets[ip].connection_timestamps.append(time.monotonic())
        self._active_sessions += 1

    def release_connection(self, ip: str) -> None:
        """Record that a connection from *ip* has closed."""
        self._active_sessions = max(0, self._active_sessions - 1)

    # -- Message limits -------------------------------------------------------

    def can_send_message(self, ip: str) -> bool:
        """Check whether *ip* is allowed to send another message."""
        now = time.monotonic()
        bucket = self._buckets[ip]
        cutoff = now - 60
        bucket.message_timestamps = [
            t for t in bucket.message_timestamps if t > cutoff
        ]
        return len(bucket.message_timestamps) < self.max_messages_per_min

    def register_message(self, ip: str) -> None:
        """Record a message from *ip*."""
        self._buckets[ip].message_timestamps.append(time.monotonic())

    # -- Input validation -----------------------------------------------------

    def validate_input(self, text: str) -> str | None:
        """Return an error string if *text* is invalid, else None."""
        if len(text) > self.max_input_length:
            return f"Input too long (max {self.max_input_length} characters)."
        return None

    # -- Housekeeping ---------------------------------------------------------

    @property
    def active_sessions(self) -> int:
        return self._active_sessions
