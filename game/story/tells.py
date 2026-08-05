"""Helpers for logging anomalies to the WrongnessLog.

Keeps anomaly ID + description lookup in one place so beat code doesn't need
to hold the description string alongside the enum value.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from game.story import fear
from game.story.anomalies import ANOMALY_DESCRIPTIONS, AnomalyID

if TYPE_CHECKING:
    from game.world_state import WorldState


def log_tell(world_state: "WorldState", anomaly: AnomalyID, player=None) -> bool:
    """Record an anomaly in the wrongness log.

    Returns True if newly logged, False if the player had already seen it.

    Pass `player` and a newly logged tell also costs her something. It is
    deduped by the log, so seeing the same wrongness twice moves nothing —
    the fear is in noticing, not in looking again. `player` is optional so the
    dev seeds and tests can build wrongness state without a player.
    """
    description = ANOMALY_DESCRIPTIONS.get(anomaly, "")
    newly_logged = world_state.wrongness.add(anomaly.value, description)
    if newly_logged:
        fear.shift(player, fear.TELL_OBSERVED)
    return newly_logged
