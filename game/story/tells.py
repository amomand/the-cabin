"""Helpers for logging anomalies to the WrongnessLog.

Keeps anomaly ID + description lookup in one place so beat code doesn't need
to hold the description string alongside the enum value.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from game.story.anomalies import ANOMALY_DESCRIPTIONS, AnomalyID

if TYPE_CHECKING:
    from game.world_state import WorldState


def log_tell(world_state: "WorldState", anomaly: AnomalyID) -> bool:
    """Record an anomaly in the wrongness log.

    Returns True if newly logged, False if the player had already seen it.
    """
    description = ANOMALY_DESCRIPTIONS.get(anomaly, "")
    return world_state.wrongness.add(anomaly.value, description)
