"""The Act IV night: seam gathering and the recognition scene.

In the rewritten canon (issue #141), recognition is earned in the dark of the
false cabin. Each deliberate observation logs a night seam in the wrongness
log; once enough have accumulated, the knowing finishes as an authored scene.

This module owns the seam set, the threshold, and the recognition prose, so
the action handlers and map beats that gather seams share one source of truth.
"""

from __future__ import annotations

from typing import Optional

from game.story.anomalies import AnomalyID
from game.story.tells import log_tell


# The seams that count towards the knowing. MEMORY_ALOUD is logged by the bed
# beat itself (observed, not chosen); the others are gathered deliberately.
NIGHT_SEAM_IDS = frozenset(
    {
        AnomalyID.MEMORY_ALOUD.value,
        AnomalyID.BREATHING_TIDE.value,
        AnomalyID.PHONE_DARK.value,
        AnomalyID.WRONG_TINS.value,
        AnomalyID.BLACK_BOARDS.value,
        AnomalyID.MUG_IMPOSSIBLE.value,
    }
)

# How many night seams finish the knowing. MEMORY_ALOUD arrives free with the
# bed beat, so the player gathers at least three more before recognition.
NIGHT_SEAM_THRESHOLD = 4


def night_seam_count(world_state) -> int:
    return sum(
        1 for entry in world_state.wrongness.entries
        if entry.anomaly_id in NIGHT_SEAM_IDS
    )


def night_threshold_met(world_state) -> bool:
    return night_seam_count(world_state) >= NIGHT_SEAM_THRESHOLD


RECOGNITION_SCENE = (
    "The papers your concussion has been keeping line themselves up.\n"
    "The frost. The knuckles. The smile that came a half-beat late. The mug, "
    "whole in your hands tonight, and the hook that was empty last night.\n"
    "You called me, she said. You reach back through the fog of the afternoon, "
    "deliberately, and there is no calling in it anywhere. Only running.\n\n"
    "And beneath all of it, the flaw so wide you have been living inside it "
    "all evening: it didn't hurt. Twenty years, and none of it was in the "
    "room. The real Nika would have come. You know that with a certainty that "
    "aches worse than the ribs. And there would have been a beat, at the "
    "threshold, boots half unlaced, both of you deciding how to stand. The "
    "distance is real. You made it yourself, message by unsent message, and "
    "the thing breathing tidally in the dark below you has waved it off.\n\n"
    "It knows the years. What it does not have is the room. How the two of "
    "you would actually stand in one, after all this time. Nobody has ever "
    "seen that. It never happened anywhere. You made sure it never happened.\n\n"
    "You lie in the dark of the wrong cabin, beside the thing wearing your "
    "oldest friend, and let the knowing finish."
)


def maybe_finish_the_knowing(world_state) -> Optional[str]:
    """Fire the recognition scene if the night seams have accumulated.

    Called by every beat that logs a night seam. Returns the authored scene
    (and sets the state) exactly once, when the threshold is crossed during
    the night. Recognition is a scene, not a silent flag flip: the returned
    prose must be appended to the feedback of the action that earned it.
    """
    if world_state.recognition:
        return None
    if world_state.reunion_stage not in ("bedded", "night"):
        return None
    if not night_threshold_met(world_state):
        return None

    # The lie about the phone call joins the log as part of the knowing.
    log_tell(world_state, AnomalyID.NO_CALL)
    world_state.recognition = True
    world_state.reunion_stage = "night"
    return RECOGNITION_SCENE
