"""Anomaly identifiers and in-world descriptions.

Every wrongness event the player can observe has an entry here. The ID is the
stable key used by `WrongnessLog`. The description is a short in-world label
surfaced in saved state and (eventually) in any recall mechanic.

Authored narration for the moment the player observes an anomaly lives with
the beat that fires it (in `game/actions/` or `game/map.py`). This file is
*identity*, not prose.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict


class AnomalyID(str, Enum):
    """Stable IDs for every observable anomaly in the game.

    Inherits from str so existing code that compares against raw strings
    ("fox_tracks", etc.) keeps working during migration, and so the value
    round-trips through JSON unchanged.
    """

    # Act II: the walk north.
    FOX_TRACKS = "fox_tracks"
    HARE = "hare"
    STONE_FORMATIONS = "stone_formations"

    # Act III: tells in the Wrong Cabin.
    FROST_WOOD_GRAIN = "frost_wood_grain"
    KNUCKLES_BIRCH = "knuckles_birch"
    DELAYED_SMILE = "delayed_smile"

    # Act IV: the definitive tell.
    CORRECTION_TURN = "correction_turn"


ANOMALY_DESCRIPTIONS: Dict[AnomalyID, str] = {
    AnomalyID.FOX_TRACKS: "a line of fox tracks that stops mid-stride",
    AnomalyID.HARE: "a hare that does not flee, does not breathe",
    AnomalyID.STONE_FORMATIONS: "half-buried stone formations, arranged, older than the family",
    AnomalyID.FROST_WOOD_GRAIN: "frost on the window, patterned like wood grain with growth rings spreading outward",
    AnomalyID.KNUCKLES_BIRCH: "Nika's hand on the mug - knuckles like knots in birch wood",
    AnomalyID.DELAYED_SMILE: "Nika's smile, laid across the face a fraction late",
    AnomalyID.CORRECTION_TURN: "Nika's stillness, and the turn that followed - a correction, not a return",
}
