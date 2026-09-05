"""The three visible seams in the false-cabin evening.

Each seam can be noticed early through its room fixture. Any still unseen when
Elli goes to look for the cars lands before the consent-door beat, so the
canonical evening cannot advance without the evidence Act IV remembers.
"""

from __future__ import annotations

from game.story.anomalies import AnomalyID
from game.story.tells import log_tell


EVENING_TELL_ORDER = (
    AnomalyID.FROST_WOOD_GRAIN,
    AnomalyID.KNUCKLES_BIRCH,
    AnomalyID.DELAYED_SMILE,
)


EVENING_TELL_PROSE = {
    AnomalyID.FROST_WOOD_GRAIN: (
        "You watch the window while Nika cooks. Frost builds at the inside "
        "corners, feathering until your eye catches the pattern. It is not "
        "feathering. The lines branch from a centre in rings, the grain of a "
        "split branch laid open. You blink. Frost again, weather on glass. "
        "Your head struck a tree. That is the file it goes into."
    ),
    AnomalyID.KNUCKLES_BIRCH: (
        "Dinner comes from tins. Nika talks in short runs with work in them: "
        "Jukka's knee, a winter of burst pipes, the tourist who asked for a "
        "bear bell in November. You let the evening stay easy. "
        "She reaches across for your plate. For the space of a breath, the hand "
        "is wrong. The knuckles stand too proud, the skin dry and ridged, fine "
        "birch grain running through it and knots where the joints should be. "
        "Then her grip shifts. A chapped hand. The white scar at the base of "
        "the thumb where the box cutter slipped when you were seventeen. "
        "\"You're staring.\"\n"
        "\"Sorry. Concussion.\"\n"
        "\"Mm. You always did stare. You used to stare at things until they "
        "confessed.\""
    ),
    AnomalyID.DELAYED_SMILE: (
        "Nika tells you what the tourist did when the bear bell sold out. You "
        "laugh, and the laugh catches in your ribs. She smiles back. Her mouth "
        "has already made the smile before the warmth reaches her eyes. Half a "
        "beat, no more. Then her eyes crease and she carries the plates to the "
        "sink. Outside the window, the clearing has gone dark."
    ),
}

EVENING_TELL_CALLBACK_PROSE = {
    AnomalyID.FROST_WOOD_GRAIN: (
        "Frost has whitened the corners of the window. You keep your eyes off "
        "the branching centre."
    ),
    AnomalyID.KNUCKLES_BIRCH: (
        "Nika's hands are in the dishwater now. The scar at the base of her "
        "thumb comes and goes beneath the suds."
    ),
    AnomalyID.DELAYED_SMILE: (
        "Nika dries the plates without looking round. Her face gives you "
        "nothing else."
    ),
}


def observe_evening_through(world_state, target, player=None) -> str:
    """Narrate unseen evening beats in order through ``target``.

    A player may inspect the fixtures in any order. Reaching for a later one
    lets the earlier part of the evening happen first; repeating an observed
    fixture returns a stable callback instead of replaying the scene.
    """
    if world_state.wrongness.has(target.value):
        return EVENING_TELL_CALLBACK_PROSE[target]

    narration = []
    for anomaly in EVENING_TELL_ORDER:
        if not world_state.wrongness.has(anomaly.value):
            log_tell(world_state, anomaly, player)
            narration.append(EVENING_TELL_PROSE[anomaly])
        if anomaly is target:
            break
    return "\n\n".join(narration)


def observe_remaining_evening_tells(world_state, player=None) -> str:
    """Narrate and log every evening seam not already seen, in story order."""
    unseen = [
        anomaly
        for anomaly in EVENING_TELL_ORDER
        if not world_state.wrongness.has(anomaly.value)
    ]
    for anomaly in unseen:
        log_tell(world_state, anomaly, player)
    return "\n\n".join(EVENING_TELL_PROSE[anomaly] for anomaly in unseen)
