"""Durable in-process adapter for clients embedding the Python turn core.

The adapter deliberately speaks only JSON-shaped values.  Native clients own
rendering and lifecycle; :class:`WebGameSession` remains the single owner of
story state and turn behaviour.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from game.game_state import GameState
from game.persistence import SaveManager
from server.protocol import RenderFrame, SessionPhase, decode_turn_message
from server.session import WebGameSession


SNAPSHOT_VERSION = 1
HANDLE_VERSION = 1


class LocalEngineError(Exception):
    """Base class for a local-engine request that cannot be honoured."""


class InvalidSnapshot(LocalEngineError):
    """The durable checkpoint is corrupt or belongs to another schema."""


class TurnMismatch(LocalEngineError):
    """A turn id was reused with another body or arrived out of order."""


def _frame_from_dict(data: object) -> RenderFrame:
    if not isinstance(data, dict) or data.get("type") != "render":
        raise InvalidSnapshot("checkpoint frame is not a render frame")
    lines = data.get("lines")
    if not isinstance(lines, list) or not all(isinstance(line, str) for line in lines):
        raise InvalidSnapshot("checkpoint frame has invalid lines")
    prompt = data.get("prompt")
    if prompt is not None and not isinstance(prompt, str):
        raise InvalidSnapshot("checkpoint frame has invalid prompt")
    for flag in ("clear", "wait_for_key", "game_over"):
        if flag in data and not isinstance(data[flag], bool):
            raise InvalidSnapshot(f"checkpoint frame has invalid {flag}")
    return RenderFrame(
        lines=list(lines),
        clear=data.get("clear", False),
        prompt=prompt,
        wait_for_key=data.get("wait_for_key", False),
        game_over=data.get("game_over", False),
    )


class LocalEngine:
    """Serially driven, crash-safe wrapper around ``WebGameSession``.

    One instance represents one native client process.  The Objective-C bridge
    serialises all calls; this class makes each completed turn durable before
    returning its frame so an ambiguous force-quit can replay that exact turn.
    """

    def __init__(self, sandbox_root: str | os.PathLike[str]) -> None:
        self.root = Path(sandbox_root).resolve()
        self.runs_dir = self.root / "runs"
        self.saves_dir = self.root / "saves"
        self.logs_dir = self.root / "logs"
        self.run_id: Optional[str] = None
        self.session: Optional[WebGameSession] = None
        self.next_turn_id = 1
        self.last_completed: Optional[Dict[str, Any]] = None

    @property
    def resume_handle(self) -> Optional[str]:
        if self.run_id is None:
            return None
        return json.dumps(
            {
                "version": HANDLE_VERSION,
                "run_id": self.run_id,
                "next_turn_id": self.next_turn_id,
            },
            separators=(",", ":"),
            sort_keys=True,
        )

    def open(self) -> Dict[str, Any]:
        """Start a fresh run and durably return the authored intro frame."""
        self.run_id = uuid4().hex
        self.session = self._fresh_session()
        self.next_turn_id = 1
        self.last_completed = None
        frame = self.session.get_intro_frame()
        self._checkpoint()
        return self._response(frame)

    def adopt(self, resume_handle: str) -> None:
        """Restore a run from an opaque native-client handle, failing closed."""
        try:
            handle = json.loads(resume_handle)
        except (TypeError, json.JSONDecodeError) as error:
            raise InvalidSnapshot("resume handle is not valid JSON") from error
        if not isinstance(handle, dict) or handle.get("version") != HANDLE_VERSION:
            raise InvalidSnapshot("resume handle has an unsupported version")
        run_id = handle.get("run_id")
        next_turn_id = handle.get("next_turn_id")
        if (
            not isinstance(run_id, str)
            or not run_id
            or not run_id.isalnum()
            or not isinstance(next_turn_id, int)
            or isinstance(next_turn_id, bool)
            or next_turn_id < 1
        ):
            raise InvalidSnapshot("resume handle is malformed")
        self._clear_loaded_run()
        self._restore(run_id)
        # The handle may be one durable write behind the Python checkpoint when
        # the app died after the turn completed but before Swift stored its
        # response.  That is exactly the replay window, so only reject a handle
        # that points beyond Python's authoritative sequence.
        if next_turn_id > self.next_turn_id:
            self._clear_loaded_run()
            raise InvalidSnapshot("resume handle is ahead of its checkpoint")

    def send(self, turn_id: int, payload: object) -> Dict[str, Any]:
        """Apply or replay one idempotent logical turn."""
        if self.session is None or self.run_id is None:
            raise InvalidSnapshot("no local run is open")
        if not isinstance(turn_id, int) or isinstance(turn_id, bool) or turn_id < 1:
            raise TurnMismatch("turn id must be a positive integer")
        canonical = self._canonical_turn(payload)

        if turn_id == self.next_turn_id - 1 and self.last_completed is not None:
            if self.last_completed.get("turn") != canonical:
                raise TurnMismatch("turn id was already used by another request")
            return self._response(_frame_from_dict(self.last_completed.get("frame")))
        if turn_id != self.next_turn_id:
            raise TurnMismatch("turn id is out of sequence")

        text, error = decode_turn_message(canonical)
        if error is not None or text is None:
            raise TurnMismatch("turn body is malformed")
        frame = self.session.handle_input(text)
        self.last_completed = {
            "turn_id": turn_id,
            "turn": canonical,
            "frame": frame.to_dict(),
        }
        self.next_turn_id += 1
        self._checkpoint()
        return self._response(frame)

    def probe(self) -> Dict[str, Any]:
        """Validate that the adopted checkpoint still exists without a turn."""
        if self.session is None or self.run_id is None:
            raise InvalidSnapshot("no local run is open")
        return {"resume_handle": self.resume_handle}

    def persist(self) -> None:
        """Force a lifecycle checkpoint without advancing the game."""
        if self.session is not None and self.run_id is not None:
            self._checkpoint()

    def dispatch(self, request_json: str) -> str:
        """JSON entry point used by the native bridge."""
        try:
            request = json.loads(request_json)
            if not isinstance(request, dict):
                raise LocalEngineError("request must be an object")
            operation = request.get("operation")
            if operation == "open":
                result = self.open()
            elif operation == "adopt":
                handle = request.get("resume_handle")
                if not isinstance(handle, str):
                    raise InvalidSnapshot("adopt requires a resume handle")
                self.adopt(handle)
                result = {"resume_handle": self.resume_handle}
            elif operation == "send":
                result = self.send(request.get("turn_id"), request.get("turn"))
            elif operation == "probe":
                result = self.probe()
            elif operation == "persist":
                self.persist()
                result = {"resume_handle": self.resume_handle}
            else:
                raise LocalEngineError("unknown local-engine operation")
            envelope = {"ok": True, **result}
        except TurnMismatch as error:
            envelope = {"ok": False, "kind": "mismatch", "message": str(error)}
        except (InvalidSnapshot, LocalEngineError) as error:
            envelope = {"ok": False, "kind": "lost", "message": str(error)}
        except Exception:
            # Native code receives a stable, non-sensitive error.  The Python
            # logger may retain detail inside the app sandbox in debug builds.
            envelope = {
                "ok": False,
                "kind": "internal",
                "message": "local engine failed",
            }
        return json.dumps(envelope, separators=(",", ":"), ensure_ascii=False)

    def _fresh_session(self) -> WebGameSession:
        session = WebGameSession()
        session.save_manager = SaveManager(save_dir=self.saves_dir)
        return session

    @staticmethod
    def _canonical_turn(payload: object) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise TurnMismatch("turn body must be an object")
        kind = payload.get("type")
        if kind == "keypress" and set(payload) == {"type"}:
            return {"type": "keypress"}
        if (
            kind == "input"
            and set(payload) == {"type", "text"}
            and isinstance(payload.get("text"), str)
        ):
            return {"type": "input", "text": payload["text"]}
        raise TurnMismatch("turn body is malformed")

    def _response(self, frame: RenderFrame) -> Dict[str, Any]:
        return {"frame": frame.to_dict(), "resume_handle": self.resume_handle}

    def _snapshot(self) -> Dict[str, Any]:
        if self.session is None or self.run_id is None:
            raise InvalidSnapshot("no local run is open")
        state = GameState(
            player=self.session.player,
            map=self.session.map,
            quest_manager=self.session.quest_manager,
            cutscene_manager=self.session.cutscene_manager,
        )
        return {
            "version": SNAPSHOT_VERSION,
            "run_id": self.run_id,
            "next_turn_id": self.next_turn_id,
            "game_state": state.to_dict(),
            "session": {
                "phase": self.session.phase.name,
                "last_feedback": self.session._last_feedback,
                "last_room_id": self.session._last_room_id,
                "pending_overlays": [
                    frame.to_dict() for frame in self.session._pending_overlays
                ],
                "consumed_feedback": self.session._consumed_feedback,
            },
            "last_completed": self.last_completed,
        }

    def _checkpoint_path(self, run_id: str) -> Path:
        return self.runs_dir / f"{run_id}.json"

    def _checkpoint(self) -> None:
        assert self.run_id is not None
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        destination = self._checkpoint_path(self.run_id)
        temporary = destination.with_suffix(f".{uuid4().hex}.tmp")
        payload = json.dumps(
            self._snapshot(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        try:
            with temporary.open("x", encoding="utf-8") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, destination)
            try:
                directory_fd = os.open(self.runs_dir, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            except OSError:
                # Some Apple filesystems do not allow directory fsync.  The
                # atomically replaced file remains the authoritative boundary.
                pass
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass

    def _restore(self, run_id: str) -> None:
        path = self._checkpoint_path(run_id)
        try:
            snapshot = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise InvalidSnapshot("local checkpoint is missing or corrupt") from error
        if not isinstance(snapshot, dict) or snapshot.get("version") != SNAPSHOT_VERSION:
            raise InvalidSnapshot("local checkpoint has an unsupported version")
        if snapshot.get("run_id") != run_id:
            raise InvalidSnapshot("local checkpoint belongs to another run")
        next_turn_id = snapshot.get("next_turn_id")
        session_data = snapshot.get("session")
        game_state = snapshot.get("game_state")
        if (
            not isinstance(next_turn_id, int)
            or isinstance(next_turn_id, bool)
            or next_turn_id < 1
            or not isinstance(session_data, dict)
            or not isinstance(game_state, dict)
        ):
            raise InvalidSnapshot("local checkpoint is malformed")

        session = self._fresh_session()
        try:
            GameState.from_dict(
                game_state,
                session.player,
                session.map,
                session.quest_manager,
                session.cutscene_manager,
            )
            phase = SessionPhase[session_data["phase"]]
            last_feedback = session_data["last_feedback"]
            last_room_id = session_data["last_room_id"]
            consumed_feedback = session_data["consumed_feedback"]
            overlays = [
                _frame_from_dict(frame)
                for frame in session_data["pending_overlays"]
            ]
        except (KeyError, TypeError, ValueError, LocalEngineError) as error:
            raise InvalidSnapshot("local checkpoint session state is malformed") from error
        if (
            not isinstance(last_feedback, str)
            or (last_room_id is not None and not isinstance(last_room_id, str))
            or not isinstance(consumed_feedback, str)
        ):
            raise InvalidSnapshot("local checkpoint session state is malformed")

        last_completed = snapshot.get("last_completed")
        if last_completed is not None:
            if not isinstance(last_completed, dict):
                raise InvalidSnapshot("local checkpoint replay state is malformed")
            completed_id = last_completed.get("turn_id")
            if completed_id != next_turn_id - 1:
                raise InvalidSnapshot("local checkpoint replay sequence is malformed")
            canonical = self._canonical_turn(last_completed.get("turn"))
            frame = _frame_from_dict(last_completed.get("frame"))
            last_completed = {
                "turn_id": completed_id,
                "turn": canonical,
                "frame": frame.to_dict(),
            }
        elif next_turn_id != 1:
            raise InvalidSnapshot("local checkpoint is missing replay state")

        session.phase = phase
        session._last_feedback = last_feedback
        session._last_room_id = last_room_id
        session._pending_overlays = overlays
        session._consumed_feedback = consumed_feedback
        self.run_id = run_id
        self.session = session
        self.next_turn_id = next_turn_id
        self.last_completed = last_completed

    def _clear_loaded_run(self) -> None:
        self.run_id = None
        self.session = None
        self.next_turn_id = 1
        self.last_completed = None
