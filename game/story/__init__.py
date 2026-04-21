"""Story data for The Cabin: anomaly IDs, tell descriptions, logging helpers.

Narrative beats still live in the action/map code that executes them, but the
*data* that identifies and describes story events lives here so there is one
place to change an anomaly ID or its description.
"""

from game.story.anomalies import AnomalyID, ANOMALY_DESCRIPTIONS
from game.story.tells import log_tell

__all__ = ["AnomalyID", "ANOMALY_DESCRIPTIONS", "log_tell"]
