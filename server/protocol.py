"""Message protocol types for The Cabin web interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional


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
