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

    # Act II: the forest approach.
    FOX_TRACKS = "fox_tracks"
    HARE = "hare"
    # Stable save value from the first implementation. Current canon uses the
    # missing deer path and emptied forest; no stone formations appear in play.
    STONE_FORMATIONS = "stone_formations"

    # Act III: tells in the Wrong Cabin.
    FROST_WOOD_GRAIN = "frost_wood_grain"
    KNUCKLES_BIRCH = "knuckles_birch"
    DELAYED_SMILE = "delayed_smile"

    # Act IV (legacy v1): the correction-turn tell. Retired by the rewritten
    # canon (#141); kept so old saves that logged it still load cleanly.
    CORRECTION_TURN = "correction_turn"

    # Act IV (rewritten canon): the night seams, gathered in the dark of the
    # false cabin. These drive recognition once the arc swap lands (#141).
    MUG_IMPOSSIBLE = "mug_impossible"
    BREATHING_TIDE = "breathing_tide"
    PHONE_DARK = "phone_dark"
    WRONG_TINS = "wrong_tins"
    BLACK_BOARDS = "black_boards"
    MEMORY_ALOUD = "memory_aloud"
    NO_CALL = "no_call"


ANOMALY_DESCRIPTIONS: Dict[AnomalyID, str] = {
    AnomalyID.FOX_TRACKS: "a line of fox tracks that stops mid-stride",
    AnomalyID.HARE: "a hare that does not flee, does not breathe",
    AnomalyID.STONE_FORMATIONS: "the deer path gone, the old woods emptied of animal life",
    AnomalyID.FROST_WOOD_GRAIN: "frost on the window, branching in the growth rings of split wood",
    AnomalyID.KNUCKLES_BIRCH: "Nika's hand on the plate, birch grain in the skin and knots at the joints",
    AnomalyID.DELAYED_SMILE: "Nika's smile, the mouth moving a half-beat before the eyes",
    AnomalyID.CORRECTION_TURN: "Nika's stillness, and the turn that followed - a correction, not a return",
    AnomalyID.MUG_IMPOSSIBLE: "the whole blue mug by the sink, though its hook was empty last night",
    AnomalyID.BREATHING_TIDE: "forty breaths in the dark, every one the same breath",
    AnomalyID.PHONE_DARK: "the phone that will not wake, dark all through like the sky",
    AnomalyID.WRONG_TINS: "dinner tins you never bought in a cupboard with no wine",
    AnomalyID.BLACK_BOARDS: "floorboards gone matt black at the edge of the firelight",
    AnomalyID.MEMORY_ALOUD: "the treasured memory, said aloud in the dark - a thing the real Nika would die before saying",
    AnomalyID.NO_CALL: "'you called me' - and the afternoon holds no calling anywhere, only running",
}
