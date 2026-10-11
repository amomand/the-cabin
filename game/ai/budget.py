"""Durable daily request allowance for a deployment's paid model traffic."""

from __future__ import annotations

import os
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


class ModelBudgetUnavailable(RuntimeError):
    """The allowance is exhausted or cannot be safely recorded."""


def reserve_model_call() -> None:
    """Reserve one attempt before contacting a provider, or fail closed.

    Both variables absent leaves local/embedded play unchanged. Deployments
    set both explicitly. SQLite serialises reservations across threads and
    processes; committing before the request also counts crashes and retries.
    Nothing is refunded, even when the provider rejects the request.
    """
    raw_limit = os.getenv("CABIN_MODEL_DAILY_CALL_LIMIT")
    raw_path = os.getenv("CABIN_MODEL_BUDGET_PATH")
    if raw_limit is None and raw_path is None:
        return
    try:
        limit = int(raw_limit) if raw_limit is not None else -1
        if limit < 0 or not raw_path:
            raise ValueError("both budget settings are required")
        # Embedded clients without a server budget need not ship sqlite3.
        import sqlite3

        # An absolute filesystem path also prevents SQLite's ':memory:'
        # special name from silently resetting the allowance on every call.
        path = Path(raw_path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(path, timeout=1.0)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "CREATE TABLE IF NOT EXISTS model_calls "
                "(day TEXT PRIMARY KEY, calls INTEGER NOT NULL CHECK(calls >= 0))"
            )
            day = datetime.now(timezone.utc).date().isoformat()
            db.execute("INSERT OR IGNORE INTO model_calls VALUES (?, 0)", (day,))
            result = db.execute(
                "UPDATE model_calls SET calls = calls + 1 WHERE day = ? AND calls < ?",
                (day, limit),
            )
            if result.rowcount != 1:
                raise ModelBudgetUnavailable("daily model allowance exhausted")
    except ModelBudgetUnavailable:
        raise
    except Exception as error:
        # Storage/configuration failures must never turn the guard off.
        raise ModelBudgetUnavailable("model allowance could not be reserved") from error
