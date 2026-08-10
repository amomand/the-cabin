"""Domain truth for the Act V dawn transition and offer.

The night becoming dawn and the dawn offer being active are adjacent states,
not synonyms.  Actions and interpreter context consume these predicates so a
malformed or stale save cannot make one surface invent a different gate.
"""

from __future__ import annotations

from typing import Optional

from game.story.night import night_threshold_met
from game.world_state import WorldState


def _dawn_requirements_met(
    world_state: WorldState,
    room_id: Optional[str],
) -> bool:
    """Return whether the shared, pre-choice dawn requirements hold."""
    return (
        world_state.is_wrong_layer()
        and room_id == "cabin_main"
        and world_state.ending == "none"
        and world_state.recognition
        and night_threshold_met(world_state)
    )


def can_advance_to_dawn(
    world_state: WorldState,
    room_id: Optional[str],
) -> bool:
    """Return whether waiting now may turn the completed night into dawn."""
    return (
        _dawn_requirements_met(world_state, room_id)
        and world_state.reunion_stage == "night"
    )


def is_dawn_offer_active(
    world_state: WorldState,
    room_id: Optional[str],
) -> bool:
    """Return whether the final mug offer can currently be answered."""
    return (
        _dawn_requirements_met(world_state, room_id)
        and world_state.reunion_stage == "dawn"
    )
