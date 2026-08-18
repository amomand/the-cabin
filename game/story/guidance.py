"""Authored quest guidance for the false-cabin night.

The quest overlay derives its text from the QuestManager, which only knows the
Warm Up quest. Through the reunion, the night, and the dawn offer the live
objective is an authored story beat rather than a quest, so the overlay used
to fall back to "Nothing pulls at you just now" at the exact points where the
story was waiting on Elli (#246). This module maps the reunion stage the
overlay should reflect onto terse guidance. It only ever implies the Lyer.
"""

from __future__ import annotations

from typing import Optional

from game.world_state import WorldState


# Keyed by reunion stage. Each line names the beat the story is waiting on
# without naming the mechanism, in the same register as the room prose.
_FALSE_CABIN_GUIDANCE: dict[str, str] = {
    "arrival": "Nika is on her feet, coming to you. Let her.",
    "tended": "She has not finished deciding things about you. Let her finish.",
    "seated": (
        "The mug is in front of you, still steaming. Drink. Then tell her."
    ),
    "complete": (
        "First light, she says, together. The evening is easy. The door is "
        "three steps away."
    ),
    "consented": (
        "You chose the warm room. The spare mattress is down by the narrow "
        "bed. Sleep, if you can."
    ),
    "bedded": (
        "Sleep does not come. Lie still. Listen. Look at what the firelight "
        "shows you."
    ),
    "night": "The knowing is finished. Nothing left but to wait for grey.",
    "dawn": "The blue mug is held out to you, and stays held out. Drink, or say no.",
}


def false_cabin_objective(
    world_state: WorldState,
    room_id: Optional[str],
) -> Optional[str]:
    """Return the guidance line for the current false-cabin beat, if any.

    Only the wrong-layer cabin with an unresolved ending carries one. The
    real cabin, the woods, and the coda return None so the quest overlay
    falls through to the QuestManager as before.
    """
    if not (
        world_state.is_wrong_layer()
        and room_id == "cabin_main"
        and world_state.ending == "none"
    ):
        return None
    return _FALSE_CABIN_GUIDANCE.get(world_state.reunion_stage)
