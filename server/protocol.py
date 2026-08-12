"""Message protocol types for The Cabin web interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Tuple

BROKEN_MESSAGE_TEXT = "The words arrive broken. The room gives them nothing."
UNKNOWN_MESSAGE_TEXT = "The words find no shape here."


def decode_turn_message(payload: object) -> Tuple[Optional[str], Optional[str]]:
    """Decode one client message into the text to hand a session.

    Returns ``(text, None)`` for a usable message and ``(None, narrated_error)``
    for anything else. Both surfaces route through this so a payload that is
    merely odd, rather than a turn, gets the same answer over a socket as it
    does over HTTP.
    """
    if not isinstance(payload, dict):
        return None, UNKNOWN_MESSAGE_TEXT

    msg_type = payload.get("type")
    if msg_type == "keypress":
        return "", None
    if msg_type == "input":
        text = payload.get("text", "")
        if not isinstance(text, str):
            return None, UNKNOWN_MESSAGE_TEXT
        return text, None
    return None, UNKNOWN_MESSAGE_TEXT


class SessionPhase(Enum):
    """State machine phases for a web game session."""
    INTRO_KEYPRESS = auto()    # Showing intro text, waiting for any key
    AWAITING_INPUT = auto()    # Showing room, waiting for player command
    OVERLAY_KEYPRESS = auto()  # Showing quest/cutscene/map overlay, waiting for any key
    ENDED = auto()             # Game over or player quit


@dataclass
class RenderFrame:
    """A single frame of output to send to the client.

    Attributes:
        lines: Text lines to display.
        clear: Whether the client should clear the screen before rendering.
        prompt: If set, show an input prompt with this prefix (e.g. "> ").
        wait_for_key: If True, client should wait for any keypress instead of text input.
        game_over: If True, the game has ended.
    """
    lines: List[str] = field(default_factory=list)
    clear: bool = False
    prompt: Optional[str] = None
    wait_for_key: bool = False
    game_over: bool = False

    def to_dict(self) -> dict:
        """Serialize to a dict suitable for JSON over WebSocket."""
        d: dict = {"type": "render", "lines": self.lines}
        if self.clear:
            d["clear"] = True
        if self.prompt is not None:
            d["prompt"] = self.prompt
        if self.wait_for_key:
            d["wait_for_key"] = True
        if self.game_over:
            d["game_over"] = True
        return d
