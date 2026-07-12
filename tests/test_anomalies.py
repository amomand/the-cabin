"""
Tests for the anomaly identity table (game/story/anomalies.py).
"""
from game.story import AnomalyID
from game.story.anomalies import ANOMALY_DESCRIPTIONS


class TestAnomalyIdentity:
    def test_every_anomaly_has_a_description(self):
        for anomaly in AnomalyID:
            assert anomaly in ANOMALY_DESCRIPTIONS, f"missing description for {anomaly}"
            assert ANOMALY_DESCRIPTIONS[anomaly].strip(), f"empty description for {anomaly}"

    def test_no_orphan_descriptions(self):
        for key in ANOMALY_DESCRIPTIONS:
            assert isinstance(key, AnomalyID)

    def test_ids_are_unique_and_stable_strings(self):
        values = [a.value for a in AnomalyID]
        assert len(values) == len(set(values))
        for value in values:
            assert value == value.lower()
            assert " " not in value

    def test_night_seam_ids_present(self):
        """The rewritten-canon night seams (issue #141) exist as identities."""
        for name in (
            "MUG_IMPOSSIBLE",
            "BREATHING_TIDE",
            "PHONE_DARK",
            "WRONG_TINS",
            "BLACK_BOARDS",
            "MEMORY_ALOUD",
            "NO_CALL",
        ):
            assert hasattr(AnomalyID, name)

    def test_descriptions_are_single_line(self):
        for anomaly, description in ANOMALY_DESCRIPTIONS.items():
            assert "\n" not in description, f"{anomaly} description spans lines"
