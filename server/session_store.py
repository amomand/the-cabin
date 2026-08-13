"""Token-keyed store for HTTP game sessions.

The WebSocket surface ties a session's life to a socket: the connection drops,
the session dies. Mobile clients cannot live with that — iOS suspends an app
within seconds of backgrounding and kills its sockets, so every phone lock
would end the run.

This store decouples session lifetime from transport. A session is created with
a token, lives in memory keyed by that token, and is dropped only when it goes
idle past a grace period (or the game ends). Save directories follow the same
rule: throwaway dirs are cleaned at expiry rather than at disconnect, and a
client that supplies a stable identity gets a durable dir that outlives the
session entirely.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import re
import secrets
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

from server.session import WebGameSession

logger = logging.getLogger("the-cabin")

# A client identity is a bearer secret: anyone holding it can read and overwrite
# that client's saves. Require enough length to be unguessable and restrict the
# charset so malformed identities are rejected before they reach the filesystem.
CLIENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{16,128}$")

DEFAULT_SAVE_RETENTION_DAYS = 30


class IdentityBusy(Exception):
    """Raised when an identity's live session is midway through a turn.

    Retiring a session while its executor is still running would leave two
    writers on one save directory. Refusing is the safe answer: the turn is a
    single model call, so the client can simply try again.
    """

    def __init__(self, identity: str) -> None:
        super().__init__(f"identity {identity[:12]}… is mid-turn")
        self.identity = identity


def _save_root() -> Path:
    """Root directory for all server-side saves."""
    return Path(os.getenv("CABIN_SAVE_ROOT", "saves"))


def _retention_seconds() -> float:
    """Age past which an untouched durable save directory is deleted."""
    raw = os.getenv("CABIN_SAVE_RETENTION_DAYS")
    days = DEFAULT_SAVE_RETENTION_DAYS
    if raw:
        try:
            days = int(raw)
        except ValueError:
            logger.warning("Ignoring non-integer CABIN_SAVE_RETENTION_DAYS: %r", raw)
    return max(0, days) * 86400.0


def _identity_of(client_id: str) -> str:
    """Hash a client identity into an opaque, filesystem-safe key.

    Hashing rather than using the identity as a path segment means no client
    string ever reaches the filesystem: traversal, casing collisions on
    case-insensitive volumes, and reserved names are all designed out. It also
    keeps the raw secret out of the process's long-lived state.
    """
    return hashlib.sha256(client_id.encode("utf-8")).hexdigest()


def _client_dir(identity: str) -> Path:
    return _save_root() / "clients" / identity


def durable_save_dir(client_id: str) -> Path:
    """Return the durable save directory for *client_id*."""
    return _client_dir(_identity_of(client_id))


def is_valid_client_id(client_id: str) -> bool:
    """True if *client_id* is well-formed enough to key a durable save dir."""
    return bool(CLIENT_ID_PATTERN.fullmatch(client_id))


@dataclass
class StoredSession:
    """A live game session plus the bookkeeping the store needs."""

    token: str
    session: WebGameSession
    ip: str
    identity: Optional[str]
    last_activity: float
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    in_flight: int = 0
    last_turn_id: Optional[int] = None
    last_turn_type: Optional[str] = None
    last_turn_text: Optional[str] = None
    last_turn_frame: Optional[Dict[str, Any]] = None

    @property
    def durable(self) -> bool:
        """True if this session's saves outlive it."""
        return self.identity is not None

    def touch(self, now: Optional[float] = None) -> None:
        self.last_activity = time.monotonic() if now is None else now


@dataclass(frozen=True)
class TerminalReplay:
    """The last idempotent game-over frame after its session is released."""

    turn_id: int
    turn_type: str
    text: str
    frame: Dict[str, Any]
    expires_at: float


class SessionStore:
    """In-memory session registry with idle expiry.

    Not thread-safe by design: every caller is a coroutine on the same event
    loop, and the only blocking work (a game turn) happens in an executor while
    holding the per-session lock.
    """

    def __init__(
        self,
        *,
        idle_timeout: float,
        on_release: Optional[Callable[[StoredSession], None]] = None,
    ) -> None:
        self.idle_timeout = idle_timeout
        self._on_release = on_release
        self._sessions: Dict[str, StoredSession] = {}
        self._terminal_replays: Dict[str, TerminalReplay] = {}

    # -- Lifecycle ------------------------------------------------------------

    def create(
        self,
        *,
        ip: str,
        client_id: Optional[str] = None,
        session: Optional[WebGameSession] = None,
    ) -> StoredSession:
        """Register a new session and return it.

        With a *client_id*, saves land in a durable directory that survives
        expiry. Without one, the session keeps the throwaway directory
        ``WebGameSession`` gives itself, deleted when the session is released.

        An identity holds at most one live session: starting a second run from
        the same client retires the first, so two sessions can never write the
        same save files at once.

        Raises ``IdentityBusy`` if the identity's existing session is midway
        through a turn. Retiring it there would leave its executor writing the
        save directory the new session is about to claim, which is the very
        corruption exclusivity exists to prevent. The caller narrates the
        refusal and the client retries once the turn lands.

        Raises ``ValueError`` for a malformed *client_id*. The identity decides
        a filesystem path, so the check belongs here rather than resting on
        every call site remembering to make it.
        """
        if client_id is not None and not is_valid_client_id(client_id):
            raise ValueError("malformed client_id")

        identity = _identity_of(client_id) if client_id is not None else None
        superseded: List[str] = []
        if identity is not None:
            superseded = [
                t for t, s in self._sessions.items() if s.identity == identity
            ]
            # Check before building anything, so a refusal costs nothing.
            if any(self._sessions[t].in_flight for t in superseded):
                raise IdentityBusy(identity)

        game = session if session is not None else WebGameSession()
        if identity is not None:
            game.save_manager.save_dir = _client_dir(identity)
            for token in superseded:
                self.release(token)

        stored = StoredSession(
            token=secrets.token_urlsafe(32),
            session=game,
            ip=ip,
            identity=identity,
            last_activity=time.monotonic(),
        )
        self._sessions[stored.token] = stored
        return stored

    def get(self, token: str) -> Optional[StoredSession]:
        """Return the live session for *token*, or None if unknown or expired.

        Expiry is checked here rather than only in the sweep so a token cannot
        be revived by arriving between sweeps.
        """
        stored = self._sessions.get(token)
        if stored is None:
            return None
        if self._is_expired(stored, time.monotonic()):
            self.release(token)
            return None
        return stored

    def release(
        self, token: str, *, preserve_terminal_replay: bool = False
    ) -> Optional[StoredSession]:
        """Drop a session, cleaning up its throwaway save dir if it had one."""
        stored = self._sessions.pop(token, None)
        if stored is None:
            return None
        if (
            preserve_terminal_replay
            and stored.last_turn_id is not None
            and stored.last_turn_type is not None
            and stored.last_turn_text is not None
            and stored.last_turn_frame is not None
        ):
            self._terminal_replays[token] = TerminalReplay(
                turn_id=stored.last_turn_id,
                turn_type=stored.last_turn_type,
                text=stored.last_turn_text,
                frame=stored.last_turn_frame,
                expires_at=time.monotonic() + max(0, self.idle_timeout),
            )
        if not stored.durable:
            _remove_dir(_save_dir_of(stored.session))
        if self._on_release is not None:
            self._on_release(stored)
        return stored

    def sweep(self) -> List[StoredSession]:
        """Release every session idle past the timeout. Returns the released."""
        now = time.monotonic()
        expired = [
            token
            for token, stored in self._sessions.items()
            if self._is_expired(stored, now)
        ]
        released = [self.release(token) for token in expired]
        self._prune_terminal_replays(time.monotonic())
        return [s for s in released if s is not None]

    def terminal_replay(self, token: str) -> Optional[TerminalReplay]:
        """Return a live terminal replay tombstone without retaining the session."""
        now = time.monotonic()
        self._prune_terminal_replays(now)
        return self._terminal_replays.get(token)

    def _prune_terminal_replays(self, now: float) -> None:
        expired = [
            token
            for token, replay in self._terminal_replays.items()
            if replay.expires_at <= now
        ]
        for token in expired:
            self._terminal_replays.pop(token, None)

    def _is_expired(self, stored: StoredSession, now: float) -> bool:
        # A request in flight is activity, whatever the clock says. Without
        # this, a sweep could delete a throwaway save directory out from under
        # a turn that is still running in the executor.
        if stored.in_flight > 0:
            return False
        return now - stored.last_activity > self.idle_timeout

    # -- Introspection --------------------------------------------------------

    def live_save_dirs(self) -> set[Path]:
        """Save directories belonging to live sessions, which must not be pruned."""
        dirs = set()
        for stored in self._sessions.values():
            save_dir = _save_dir_of(stored.session)
            if save_dir is not None:
                dirs.add(save_dir.resolve() if save_dir.exists() else save_dir)
        return dirs

    def __len__(self) -> int:
        return len(self._sessions)

    def tokens(self) -> Iterable[str]:
        return tuple(self._sessions)


def _save_dir_of(session: WebGameSession) -> Optional[Path]:
    save_manager = getattr(session, "save_manager", None)
    return getattr(save_manager, "save_dir", None)


def _remove_dir(path: Optional[Path]) -> None:
    """Delete *path* if it exists. Runs during cleanup, so it must not raise."""
    if path is None:
        return
    try:
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
    except OSError:
        logger.debug("Failed to remove save dir: %s", path, exc_info=True)


def prune_expired_saves(
    live_dirs: Optional[Iterable[Path]] = None,
    *,
    now: Optional[float] = None,
) -> List[Path]:
    """Delete durable save directories untouched for the retention window.

    Directories in *live_dirs* belong to sessions that are still playing and
    are never touched, however old their files look; a run that has not saved
    for a long time must not lose its history mid-session.

    Retention is otherwise measured from the most recently modified save file
    in the directory, so an active player's saves are never collected out from
    under them. A retention of 0 days disables pruning rather than deleting
    everything, so a misconfiguration cannot wipe live saves.
    """
    retention = _retention_seconds()
    if retention <= 0:
        return []

    clients_dir = _save_root() / "clients"
    if not clients_dir.is_dir():
        return []

    protected = {Path(p) for p in (live_dirs or ())}
    cutoff = (time.time() if now is None else now) - retention
    pruned: List[Path] = []
    try:
        entries = list(clients_dir.iterdir())
    except OSError:
        logger.debug("Failed to list durable save root: %s", clients_dir, exc_info=True)
        return []

    for entry in entries:
        if not entry.is_dir():
            continue
        if entry in protected or entry.resolve() in protected:
            continue
        if _latest_mtime(entry) > cutoff:
            continue
        _remove_dir(entry)
        pruned.append(entry)
    return pruned


def _latest_mtime(directory: Path) -> float:
    """Most recent mtime among *directory* and its contents.

    An unreadable directory reports "now" so a transient filesystem error can
    never be mistaken for staleness and cost someone their saves.
    """
    try:
        latest = directory.stat().st_mtime
        for child in directory.iterdir():
            latest = max(latest, child.stat().st_mtime)
        return latest
    except OSError:
        logger.debug("Failed to stat save dir: %s", directory, exc_info=True)
        return time.time()
