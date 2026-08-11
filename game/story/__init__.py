"""Shared story contracts for The Cabin.

This package exports anomaly identifiers, fear rules, tell logging, and the
night-seam, recognition, and dawn helpers used by actions and the map.
"""

from game.story import fear
from game.story.anomalies import AnomalyID, ANOMALY_DESCRIPTIONS
from game.story.tells import log_tell
from game.story.night import (
    NIGHT_SEAM_IDS,
    NIGHT_SEAM_THRESHOLD,
    maybe_finish_the_knowing,
    night_seam_count,
    night_threshold_met,
    observe_night_seam,
)
from game.story.dawn import can_advance_to_dawn, is_dawn_offer_active

__all__ = [
    "AnomalyID",
    "ANOMALY_DESCRIPTIONS",
    "fear",
    "log_tell",
    "NIGHT_SEAM_IDS",
    "NIGHT_SEAM_THRESHOLD",
    "maybe_finish_the_knowing",
    "night_seam_count",
    "night_threshold_met",
    "observe_night_seam",
    "can_advance_to_dawn",
    "is_dawn_offer_active",
]
