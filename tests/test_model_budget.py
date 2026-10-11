"""The paid-call allowance is durable, atomic and fails closed."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import subprocess
import sys

import pytest

from game.ai import budget


@pytest.fixture
def allowance(monkeypatch, tmp_path):
    monkeypatch.setenv("CABIN_MODEL_DAILY_CALL_LIMIT", "3")
    monkeypatch.setenv("CABIN_MODEL_BUDGET_PATH", str(tmp_path / "budget.sqlite3"))


def test_concurrent_attempts_cannot_exceed_shared_allowance(allowance):
    def reserve(_):
        try:
            budget.reserve_model_call()
            return True
        except budget.ModelBudgetUnavailable:
            return False

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(reserve, range(20))) == 3


def test_reservation_survives_a_new_process(allowance):
    subprocess.run(
        [sys.executable, "-c", "from game.ai.budget import reserve_model_call; reserve_model_call()"],
        check=True,
    )
    budget.reserve_model_call()
    budget.reserve_model_call()
    with pytest.raises(budget.ModelBudgetUnavailable):
        budget.reserve_model_call()


def test_allowance_renews_at_utc_midnight_without_erasing_previous_day(allowance, monkeypatch):
    class Clock:
        day = 11

        @classmethod
        def now(cls, tz):
            assert tz == timezone.utc
            return datetime(2026, 10, cls.day, tzinfo=tz)

    monkeypatch.setattr(budget, "datetime", Clock)
    for _ in range(3):
        budget.reserve_model_call()
    Clock.day = 12
    budget.reserve_model_call()
    Clock.day = 11
    with pytest.raises(budget.ModelBudgetUnavailable):
        budget.reserve_model_call()


@pytest.mark.parametrize("limit", ["0", "-1", "nonsense", ""])
def test_zero_or_invalid_allowance_never_permits_a_request(allowance, monkeypatch, limit):
    monkeypatch.setenv("CABIN_MODEL_DAILY_CALL_LIMIT", limit)
    with pytest.raises(budget.ModelBudgetUnavailable):
        budget.reserve_model_call()


@pytest.mark.parametrize("missing", ["CABIN_MODEL_DAILY_CALL_LIMIT", "CABIN_MODEL_BUDGET_PATH"])
def test_partial_configuration_fails_closed(allowance, monkeypatch, missing):
    monkeypatch.delenv(missing)
    with pytest.raises(budget.ModelBudgetUnavailable):
        budget.reserve_model_call()


def test_corrupt_storage_does_not_reset_allowance(allowance, monkeypatch, tmp_path):
    path = tmp_path / "broken.sqlite3"
    path.write_bytes(b"not a database")
    monkeypatch.setenv("CABIN_MODEL_BUDGET_PATH", str(path))
    with pytest.raises(budget.ModelBudgetUnavailable):
        budget.reserve_model_call()


def test_local_play_without_budget_settings_needs_no_storage():
    budget.reserve_model_call()
