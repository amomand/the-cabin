"""Unit tests for the token-keyed session store and save retention."""

import os
import time
from pathlib import Path

import pytest

from server import session_store as store_module
from server.session_store import (
    SessionStore,
    durable_save_dir,
    is_valid_client_id,
    prune_expired_saves,
)


class _StubSaveManager:
    def __init__(self, save_dir: Path) -> None:
        self.save_dir = save_dir


class _StubSession:
    """Stands in for WebGameSession; the store only touches save_manager."""

    def __init__(self, save_dir: Path) -> None:
        self.save_manager = _StubSaveManager(save_dir)


@pytest.fixture(autouse=True)
def _isolated_saves(tmp_path, monkeypatch):
    """Keep every test's save writes inside tmp_path.

    CABIN_SAVE_ROOT covers the durable per-client directories, but a
    throwaway session's directory is a relative path chosen by
    WebGameSession, so the working directory has to move too.
    """
    monkeypatch.setenv("CABIN_SAVE_ROOT", str(tmp_path / "saves"))
    monkeypatch.chdir(tmp_path)


def _store(**kwargs) -> SessionStore:
    kwargs.setdefault("idle_timeout", 3600)
    return SessionStore(**kwargs)


class TestClientIdValidation:
    @pytest.mark.parametrize(
        "value",
        ["a" * 16, "a" * 128, "AB-cd_ef.0123456789", "0123456789abcdef"],
    )
    def test_accepts_well_formed_identities(self, value):
        assert is_valid_client_id(value)

    @pytest.mark.parametrize(
        "value",
        [
            "",
            "a" * 15,
            "a" * 129,
            "../../../etc/passwd0000",
            "has spaces in it here",
            "slash/inside/here00000",
            "null\x00byte0000000000",
            "newline\nsneaks000000",
        ],
    )
    def test_rejects_malformed_identities(self, value):
        assert not is_valid_client_id(value)

    def test_newline_cannot_smuggle_a_valid_prefix(self):
        """fullmatch, not match: a trailing newline must not pass."""
        assert not is_valid_client_id("a" * 20 + "\n")


class TestDurableSaveDir:
    def test_identity_is_hashed_not_embedded(self, tmp_path):
        path = durable_save_dir("a" * 32)
        assert "a" * 32 not in str(path)
        assert path.parent.name == "clients"
        assert len(path.name) == 64  # sha256 hex

    def test_same_identity_maps_to_the_same_dir(self):
        assert durable_save_dir("z" * 20) == durable_save_dir("z" * 20)

    def test_different_identities_map_to_different_dirs(self):
        assert durable_save_dir("y" * 20) != durable_save_dir("z" * 20)

    def test_honours_the_save_root_override(self, tmp_path):
        assert str(durable_save_dir("q" * 20)).startswith(str(tmp_path / "saves"))


class TestSessionLifecycle:
    def test_create_returns_a_token_and_registers_the_session(self, tmp_path):
        store = _store()
        stored = store.create(ip="1.2.3.4", session=_StubSession(tmp_path / "one"))
        assert stored.token
        assert len(store) == 1
        assert store.get(stored.token) is stored

    def test_tokens_are_long_enough_to_resist_guessing(self, tmp_path):
        store = _store()
        stored = store.create(ip="1.2.3.4", session=_StubSession(tmp_path / "one"))
        assert len(stored.token) >= 32

    def test_unknown_token_returns_none(self):
        assert _store().get("nope") is None

    def test_release_is_idempotent(self, tmp_path):
        store = _store()
        stored = store.create(ip="1.2.3.4", session=_StubSession(tmp_path / "one"))
        assert store.release(stored.token) is stored
        assert store.release(stored.token) is None

    def test_release_notifies_the_callback_once(self, tmp_path):
        released = []
        store = _store(on_release=released.append)
        stored = store.create(ip="1.2.3.4", session=_StubSession(tmp_path / "one"))
        store.release(stored.token)
        store.release(stored.token)
        assert released == [stored]


class TestExpiry:
    def test_get_releases_an_idle_session(self, tmp_path):
        released = []
        store = _store(idle_timeout=-1, on_release=released.append)
        stored = store.create(ip="1.2.3.4", session=_StubSession(tmp_path / "one"))
        assert store.get(stored.token) is None
        assert released == [stored]
        assert len(store) == 0

    def test_sweep_releases_only_idle_sessions(self, tmp_path):
        store = _store(idle_timeout=60)
        stale = store.create(ip="1.2.3.4", session=_StubSession(tmp_path / "one"))
        fresh = store.create(ip="1.2.3.4", session=_StubSession(tmp_path / "two"))
        stale.last_activity = time.monotonic() - 3600

        assert store.sweep() == [stale]
        assert store.get(fresh.token) is fresh

    def test_touch_defers_expiry(self, tmp_path):
        store = _store(idle_timeout=60)
        stored = store.create(ip="1.2.3.4", session=_StubSession(tmp_path / "one"))
        stored.last_activity = time.monotonic() - 3600
        stored.touch()
        assert store.sweep() == []

    def test_in_flight_request_defers_expiry(self, tmp_path):
        """A running turn must not have its session swept out from under it."""
        store = _store(idle_timeout=-1)
        stored = store.create(ip="1.2.3.4", session=_StubSession(tmp_path / "one"))
        stored.in_flight = 1
        assert store.sweep() == []
        assert store.get(stored.token) is stored

        stored.in_flight = 0
        assert store.get(stored.token) is None

    def test_in_flight_throwaway_dir_is_not_deleted_by_a_sweep(self, tmp_path):
        save_dir = tmp_path / "throwaway"
        save_dir.mkdir()
        store = _store(idle_timeout=-1)
        stored = store.create(ip="1.2.3.4", session=_StubSession(save_dir))
        stored.in_flight = 1
        store.sweep()
        assert save_dir.exists()


class TestIdentityExclusivity:
    def test_a_second_session_retires_the_first(self, tmp_path):
        released = []
        store = _store(on_release=released.append)
        first = store.create(
            ip="1.2.3.4", client_id="k" * 32, session=_StubSession(tmp_path / "one")
        )
        second = store.create(
            ip="1.2.3.4", client_id="k" * 32, session=_StubSession(tmp_path / "two")
        )
        assert released == [first]
        assert store.get(first.token) is None
        assert store.get(second.token) is second
        assert len(store) == 1

    def test_different_identities_coexist(self, tmp_path):
        store = _store()
        first = store.create(
            ip="1.2.3.4", client_id="k" * 32, session=_StubSession(tmp_path / "one")
        )
        second = store.create(
            ip="1.2.3.4", client_id="j" * 32, session=_StubSession(tmp_path / "two")
        )
        assert store.get(first.token) is first
        assert store.get(second.token) is second

    def test_anonymous_sessions_coexist(self, tmp_path):
        store = _store()
        first = store.create(ip="1.2.3.4", session=_StubSession(tmp_path / "one"))
        second = store.create(ip="1.2.3.4", session=_StubSession(tmp_path / "two"))
        assert store.get(first.token) is first
        assert store.get(second.token) is second

    def test_retiring_a_session_keeps_its_durable_saves(self, tmp_path):
        store = _store()
        first = store.create(
            ip="1.2.3.4", client_id="k" * 32, session=_StubSession(tmp_path / "one")
        )
        first.session.save_manager.save_dir.mkdir(parents=True)
        save_dir = first.session.save_manager.save_dir
        store.create(
            ip="1.2.3.4", client_id="k" * 32, session=_StubSession(tmp_path / "two")
        )
        assert save_dir.exists()


class TestLiveSaveDirs:
    def test_reports_every_live_session_dir(self, tmp_path):
        store = _store()
        first = store.create(ip="1.2.3.4", session=_StubSession(tmp_path / "one"))
        second = store.create(ip="1.2.3.4", session=_StubSession(tmp_path / "two"))
        live = store.live_save_dirs()
        assert first.session.save_manager.save_dir in live
        assert second.session.save_manager.save_dir in live

    def test_released_dirs_drop_out(self, tmp_path):
        store = _store()
        stored = store.create(ip="1.2.3.4", session=_StubSession(tmp_path / "one"))
        store.release(stored.token)
        assert store.live_save_dirs() == set()


class TestSaveCleanupOnRelease:
    def test_throwaway_dir_is_deleted(self, tmp_path):
        save_dir = tmp_path / "throwaway"
        save_dir.mkdir()
        store = _store()
        stored = store.create(ip="1.2.3.4", session=_StubSession(save_dir))
        store.release(stored.token)
        assert not save_dir.exists()

    def test_durable_dir_is_kept(self, tmp_path):
        store = _store()
        stored = store.create(
            ip="1.2.3.4",
            client_id="d" * 32,
            session=_StubSession(tmp_path / "unused"),
        )
        save_dir = stored.session.save_manager.save_dir
        save_dir.mkdir(parents=True)
        store.release(stored.token)
        assert save_dir.exists()

    def test_missing_dir_does_not_raise(self, tmp_path):
        store = _store()
        stored = store.create(ip="1.2.3.4", session=_StubSession(tmp_path / "never-made"))
        store.release(stored.token)


class TestSaveRetention:
    def _make_client_dir(self, name: str, age_seconds: float) -> Path:
        path = durable_save_dir(name)
        path.mkdir(parents=True)
        (path / "autosave.json").write_text("{}")
        when = time.time() - age_seconds
        os.utime(path / "autosave.json", (when, when))
        os.utime(path, (when, when))
        return path

    def test_stale_dirs_are_pruned(self, monkeypatch):
        monkeypatch.setenv("CABIN_SAVE_RETENTION_DAYS", "30")
        stale = self._make_client_dir("s" * 20, age_seconds=40 * 86400)
        assert prune_expired_saves() == [stale]
        assert not stale.exists()

    def test_recent_dirs_are_kept(self, monkeypatch):
        monkeypatch.setenv("CABIN_SAVE_RETENTION_DAYS", "30")
        fresh = self._make_client_dir("f" * 20, age_seconds=86400)
        assert prune_expired_saves() == []
        assert fresh.exists()

    def test_recent_file_keeps_an_old_dir(self, monkeypatch):
        """Retention follows the newest save, not the directory's own mtime."""
        monkeypatch.setenv("CABIN_SAVE_RETENTION_DAYS", "30")
        path = self._make_client_dir("m" * 20, age_seconds=40 * 86400)
        (path / "recent.json").write_text("{}")
        assert prune_expired_saves() == []
        assert path.exists()

    def test_zero_days_disables_pruning(self, monkeypatch):
        monkeypatch.setenv("CABIN_SAVE_RETENTION_DAYS", "0")
        ancient = self._make_client_dir("z" * 20, age_seconds=3650 * 86400)
        assert prune_expired_saves() == []
        assert ancient.exists()

    def test_non_integer_retention_falls_back_to_the_default(self, monkeypatch):
        monkeypatch.setenv("CABIN_SAVE_RETENTION_DAYS", "thirty")
        stale = self._make_client_dir("n" * 20, age_seconds=40 * 86400)
        assert prune_expired_saves() == [stale]

    def test_missing_root_is_a_noop(self, monkeypatch):
        monkeypatch.setenv("CABIN_SAVE_RETENTION_DAYS", "30")
        assert prune_expired_saves() == []

    def test_live_dirs_are_never_pruned(self, monkeypatch):
        """A long run that has not saved recently must not lose its history."""
        monkeypatch.setenv("CABIN_SAVE_RETENTION_DAYS", "30")
        live = self._make_client_dir("l" * 20, age_seconds=40 * 86400)
        assert prune_expired_saves([live]) == []
        assert live.exists()

    def test_live_protection_does_not_spare_other_dirs(self, monkeypatch):
        monkeypatch.setenv("CABIN_SAVE_RETENTION_DAYS", "30")
        live = self._make_client_dir("l" * 20, age_seconds=40 * 86400)
        stale = self._make_client_dir("o" * 20, age_seconds=40 * 86400)
        assert prune_expired_saves([live]) == [stale]
        assert live.exists()
        assert not stale.exists()

    def test_stray_files_in_the_root_are_left_alone(self, monkeypatch):
        monkeypatch.setenv("CABIN_SAVE_RETENTION_DAYS", "30")
        clients = Path(os.environ["CABIN_SAVE_ROOT"]) / "clients"
        clients.mkdir(parents=True)
        stray = clients / "README"
        stray.write_text("not a save dir")
        old = time.time() - 3650 * 86400
        os.utime(stray, (old, old))
        assert prune_expired_saves() == []
        assert stray.exists()

    def test_unreadable_dir_is_treated_as_fresh(self, monkeypatch, tmp_path):
        """A stat failure must never be mistaken for staleness."""
        monkeypatch.setenv("CABIN_SAVE_RETENTION_DAYS", "30")
        self._make_client_dir("u" * 20, age_seconds=40 * 86400)
        monkeypatch.setattr(store_module, "_latest_mtime", lambda p: time.time())
        assert prune_expired_saves() == []

    def test_latest_mtime_reports_now_when_stat_fails(self, tmp_path):
        missing = tmp_path / "gone"
        assert store_module._latest_mtime(missing) == pytest.approx(
            time.time(), abs=5
        )


class TestCreateValidatesIdentity:
    """The identity decides a filesystem path, so the store checks it itself
    rather than trusting every call site to have done so."""

    @pytest.mark.parametrize(
        "bad",
        ["short", "a" * 129, "has spaces in it", "../../etc/passwd", "a" * 16 + "\n"],
        ids=["too-short", "too-long", "spaces", "traversal", "trailing-newline"],
    )
    def test_malformed_client_id_is_refused(self, tmp_path, monkeypatch, bad):
        monkeypatch.setenv("CABIN_SAVE_ROOT", str(tmp_path / "saves"))
        store = SessionStore(idle_timeout=60)
        with pytest.raises(ValueError):
            store.create(ip="1.2.3.4", client_id=bad)
        assert len(store) == 0

    def test_valid_client_id_is_accepted(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CABIN_SAVE_ROOT", str(tmp_path / "saves"))
        store = SessionStore(idle_timeout=60)
        stored = store.create(ip="1.2.3.4", client_id="a" * 32)
        assert stored.durable
