"""Tests for the rate limiter."""

import time
from unittest.mock import patch

from server.rate_limiter import RateLimiter


class TestRateLimiter:
    def test_allows_first_connection(self):
        rl = RateLimiter()
        assert rl.can_connect("1.2.3.4") is True

    def test_blocks_after_max_connections(self):
        rl = RateLimiter(max_connections_per_min=2)
        rl.register_connection("1.2.3.4")
        rl.register_connection("1.2.3.4")
        assert rl.can_connect("1.2.3.4") is False

    def test_blocks_after_max_sessions(self):
        rl = RateLimiter(max_sessions=2)
        rl.register_connection("1.1.1.1")
        rl.register_connection("2.2.2.2")
        assert rl.can_connect("3.3.3.3") is False

    def test_release_allows_new_sessions(self):
        rl = RateLimiter(max_sessions=1)
        rl.register_connection("1.1.1.1")
        assert rl.can_connect("2.2.2.2") is False
        rl.release_connection("1.1.1.1")
        assert rl.can_connect("2.2.2.2") is True

    def test_allows_messages_within_limit(self):
        rl = RateLimiter(max_messages_per_min=3)
        ip = "1.2.3.4"
        for _ in range(3):
            assert rl.can_send_message(ip) is True
            rl.register_message(ip)
        assert rl.can_send_message(ip) is False

    def test_validate_input_length(self):
        rl = RateLimiter(max_input_length=10)
        assert rl.validate_input("short") is None
        assert rl.validate_input("a" * 11) == "The thought comes too crowded. Narrow it."

    def test_active_sessions_counter(self):
        rl = RateLimiter()
        assert rl.active_sessions == 0
        rl.register_connection("1.1.1.1")
        assert rl.active_sessions == 1
        rl.release_connection("1.1.1.1")
        assert rl.active_sessions == 0

    def test_release_does_not_go_negative(self):
        rl = RateLimiter()
        rl.release_connection("1.1.1.1")
        assert rl.active_sessions == 0


class TestBucketEviction:
    def test_idle_bucket_is_dropped_after_window(self):
        with patch("time.monotonic") as clock:
            clock.return_value = 0.0
            rl = RateLimiter()
            rl.register_connection("1.2.3.4")
            assert "1.2.3.4" in rl._buckets

            clock.return_value = 121.0
            rl.can_send_message("9.9.9.9")
            assert "1.2.3.4" not in rl._buckets

    def test_active_bucket_survives_prune(self):
        with patch("time.monotonic") as clock:
            clock.return_value = 0.0
            rl = RateLimiter()
            clock.return_value = 100.0
            rl.register_message("1.2.3.4")

            clock.return_value = 125.0
            rl.can_connect("9.9.9.9")
            assert "1.2.3.4" in rl._buckets

    def test_recently_blocked_ip_stays_blocked_through_prune(self):
        with patch("time.monotonic") as clock:
            clock.return_value = 0.0
            rl = RateLimiter(max_messages_per_min=2)
            clock.return_value = 100.0
            rl.register_message("1.2.3.4")
            rl.register_message("1.2.3.4")

            clock.return_value = 125.0
            rl.can_connect("9.9.9.9")
            assert rl.can_send_message("1.2.3.4") is False
