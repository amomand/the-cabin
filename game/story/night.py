"""The Act IV night: seam gathering and the recognition scene.

In the rewritten canon (issue #141), recognition is earned in the dark of the
false cabin. Each deliberate observation logs a night seam in the wrongness
log; once enough have accumulated, the knowing finishes as an authored scene.

This module owns the seam set, the threshold, and the recognition prose, so
the action handlers and map beats that gather seams share one source of truth.
"""

from __future__ import annotations

from typing import Optional

from game.story import fear
from game.story.anomalies import AnomalyID
from game.story.tells import log_tell


# The seams that count towards the knowing. MEMORY_ALOUD is logged by the bed
# beat itself (observed, not chosen); the others begin as deliberate finds.
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

# Once the threshold is reached, any still-unseen seams surface before the
# knowing. This keeps the investigation playable without making the published
# night optional or turning it into a five-command checklist.
NIGHT_SEAM_ORDER = (
    AnomalyID.BREATHING_TIDE,
    AnomalyID.MUG_IMPOSSIBLE,
    AnomalyID.PHONE_DARK,
    AnomalyID.WRONG_TINS,
    AnomalyID.BLACK_BOARDS,
)

NIGHT_SEAM_PROSE = {
    AnomalyID.BREATHING_TIDE: (
        "You lie still and listen to the breathing below you. Long, even "
        "breaths, someone going down into sleep, except they never change. "
        "A sleeping person's breath should catch at its edge, go ragged, slow "
        "with the body shifting. This one keeps coming, a tide without a moon, "
        "identical and patient. You count forty breaths. Every one is the same "
        "breath. "
        "The hare sat composed at the side of the path, its flanks not moving."
    ),
    AnomalyID.MUG_IMPOSSIBLE: (
        "The blue mug sits rinsed by the sink, whole, its chip at the two "
        "o'clock of the handle. You drank from it tonight. "
        "The hook by the stove was empty last night. You remember opening the "
        "cupboard. There was no blue mug anywhere in the cabin."
    ),
    AnomalyID.PHONE_DARK: (
        "Your phone is in your jacket on the peg. You lie a long while before "
        "you ease out from under the covers and get it, one held breath at a "
        "time. The screen will not wake. Not flat-battery dark. Dark all "
        "through, like the sky over the clearing."
    ),
    AnomalyID.WRONG_TINS: (
        "Dinner, late: tins you never bought, from a cupboard that holds no "
        "wine, though your own bottle stands corked on a counter somewhere "
        "south of this room. You go through the shelf in your head twice and "
        "find no bottle, no glass."
    ),
    AnomalyID.BLACK_BOARDS: (
        "The fire has burned down further than it should have. The warmth has "
        "pulled back from the walls towards the hearth, and along the floor, "
        "where the light is lowest, the boards have gone the deep matt black "
        "of the ground outside. When you look directly, they are boards. The "
        "room holds its shape the way the smile held its face: from your "
        "attention."
    ),
}

NIGHT_SEAM_CALLBACK_PROSE = {
    AnomalyID.BREATHING_TIDE: (
        "Below you, the breathing keeps its measure. You stop counting."
    ),
    AnomalyID.MUG_IMPOSSIBLE: (
        "The blue mug remains by the sink. The hook was empty."
    ),
    AnomalyID.PHONE_DARK: (
        "The screen stays dark. You put the phone beside you on the bed."
    ),
    AnomalyID.WRONG_TINS: (
        "The tins stand by the stove. Your wine is in the cabin you left."
    ),
    AnomalyID.BLACK_BOARDS: (
        "Look straight at the floor and there are boards. Let your gaze soften "
        "and the black returns between them."
    ),
}


def night_seam_count(world_state) -> int:
    return sum(
        1 for entry in world_state.wrongness.entries
        if entry.anomaly_id in NIGHT_SEAM_IDS
    )


def night_threshold_met(world_state) -> bool:
    return (
        night_seam_count(world_state) >= NIGHT_SEAM_THRESHOLD
        and (
            world_state.recognition
            or world_state.wrongness.has(AnomalyID.BREATHING_TIDE.value)
        )
    )


RECOGNITION_SCENE = (
    "The papers your concussion has been keeping line themselves up. "
    "The frost. The knuckles. The smile that came a half-beat late. The mug, "
    "whole in your hands tonight, and the hook that was empty last night. "
    "You called me, she said. You reach back through the fog of the afternoon, "
    "deliberately, and there is no calling in it anywhere. Only running.\n\n"
    "Beneath all of it is the flaw so wide you have been living inside it all "
    "evening: it didn't hurt. Twenty years, and none of them were in the room. "
    "The real Nika would have come; you know that with a certainty that aches "
    "worse than your ribs. But there would have been a beat at the threshold, "
    "boots half unlaced, both of you deciding how to stand. The distance is "
    "real. You made it yourself, message by unsent message, and the thing "
    "breathing in the dark below you waved it off.\n\n"
    "It knows the years. It counted them out of Nika somewhere in those woods, "
    "along with the towel and the mug and the lake path. What it does not have "
    "is the room: how the two of you would actually stand in one after all this "
    "time. Nobody has ever seen that room. You made sure it never happened. "
    "You lie in the dark of the wrong cabin, beside the thing wearing your "
    "oldest friend, and let the knowing finish."
)


def maybe_finish_the_knowing(world_state, player=None) -> Optional[str]:
    """Fire the recognition scene if the night seams have accumulated.

    Called by every beat that logs a night seam. Returns the authored scene
    (and sets the state) exactly once, when the threshold is crossed during
    the night. Recognition is a scene, not a silent flag flip: the returned
    prose must be appended to the feedback of the action that earned it.

    `player` is optional so tests and dev seeds can drive the state machine
    without one; passed, the knowing costs her the largest step in Act IV.
    """
    if world_state.recognition:
        return None
    if world_state.reunion_stage not in ("bedded", "night"):
        return None
    if not night_threshold_met(world_state):
        return None

    # The remaining physical seams arrive before the insight. The player has
    # done enough looking to earn the knowing; they do not need to guess every
    # parser target to receive the published night.
    remaining = []
    for anomaly in NIGHT_SEAM_ORDER:
        if log_tell(world_state, anomaly, player):
            remaining.append(NIGHT_SEAM_PROSE[anomaly])

    # The lie about the phone call joins the log as part of the knowing.
    log_tell(world_state, AnomalyID.NO_CALL, player)
    world_state.recognition = True
    world_state.transition_reunion_to("night")
    fear.shift(player, fear.RECOGNITION)
    remaining.append(RECOGNITION_SCENE)
    return "\n\n".join(remaining)


def observe_night_seam(world_state, anomaly: AnomalyID, player=None) -> tuple[str, bool]:
    """Observe one seam, complete the canonical night, or return a callback."""
    before = world_state.wrongness.count()
    first_observation = log_tell(world_state, anomaly, player)
    text = (
        NIGHT_SEAM_PROSE[anomaly]
        if first_observation
        else NIGHT_SEAM_CALLBACK_PROSE[anomaly]
    )
    scene = maybe_finish_the_knowing(world_state, player)
    if scene:
        text += "\n\n" + scene
    return text, world_state.wrongness.count() > before
