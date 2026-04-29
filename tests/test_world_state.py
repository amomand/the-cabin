"""
Tests for WorldState typed state management.
"""
import pytest
from game.world_state import WorldState, WrongnessLog


class TestWorldState:
    """Tests for WorldState dataclass."""

    def test_default_values(self):
        """WorldState should have sensible defaults."""
        state = WorldState()
        assert state.has_power is False
        assert state.fire_lit is False
        assert state.ending == "none"

    def test_explicit_initialization(self):
        """WorldState can be initialized with explicit values."""
        state = WorldState(has_power=True, fire_lit=True)
        assert state.has_power is True
        assert state.fire_lit is True

    def test_dict_style_get(self):
        """WorldState supports dict-style get() for backward compatibility."""
        state = WorldState(has_power=True)
        assert state.get("has_power") is True
        assert state.get("fire_lit") is False
        assert state.get("nonexistent", "default") == "default"

    def test_dict_style_bracket_access(self):
        """WorldState supports bracket access for backward compatibility."""
        state = WorldState(has_power=True)
        assert state["has_power"] is True
        
        with pytest.raises(KeyError):
            _ = state["nonexistent"]

    def test_dict_style_bracket_assignment(self):
        """WorldState supports bracket assignment for backward compatibility."""
        state = WorldState()
        state["has_power"] = True
        assert state.has_power is True
        
        # Unknown keys go to custom flags
        state["custom_flag"] = "value"
        assert state.get("custom_flag") == "value"

    def test_contains(self):
        """WorldState supports 'in' operator."""
        state = WorldState()
        assert "has_power" in state
        assert "fire_lit" in state
        assert "nonexistent" not in state
        
        state.set_flag("custom", True)
        assert "custom" in state

    def test_custom_flags(self):
        """WorldState can store custom flags."""
        state = WorldState()
        state.set_flag("quest_started", True)
        state.set_flag("npc_talked_to", "eli")
        
        assert state.get_flag("quest_started") is True
        assert state.get_flag("npc_talked_to") == "eli"
        assert state.get_flag("nonexistent", "default") == "default"

    def test_to_dict(self):
        """WorldState can be converted to dict for serialization."""
        state = WorldState(has_power=True, fire_lit=False)
        state.set_flag("custom", "value")
        
        d = state.to_dict()
        
        assert d["has_power"] is True
        assert d["fire_lit"] is False
        assert d["custom"] == "value"

    def test_from_dict(self):
        """WorldState can be restored from dict."""
        data = {
            "has_power": True,
            "fire_lit": True,
            "ending": "accepted",
            "custom_flag": "custom_value",
        }
        
        state = WorldState.from_dict(data)
        
        assert state.has_power is True
        assert state.fire_lit is True
        assert state.ending == "accepted"
        assert state.get_flag("custom_flag") == "custom_value"

    def test_from_dict_round_trip(self):
        """WorldState survives serialization round-trip."""
        original = WorldState(has_power=True)
        original.ending = "refused"
        original.set_flag("quest_progress", 3)
        
        restored = WorldState.from_dict(original.to_dict())
        
        assert restored.has_power == original.has_power
        assert restored.fire_lit == original.fire_lit
        assert restored.ending == original.ending
        assert restored.get_flag("quest_progress") == 3

    def test_validate_success(self):
        """validate() passes for valid state."""
        state = WorldState(has_power=True, fire_lit=False)
        state.validate()  # Should not raise

    def test_validate_invalid_type(self):
        """validate() raises for invalid types."""
        state = WorldState()
        state.has_power = "yes"  # type: ignore - intentionally wrong
        
        with pytest.raises(ValueError, match="has_power must be bool"):
            state.validate()


class TestWorldLayer:
    """Tests for the real/wrong world layer flag."""

    def test_defaults_to_real(self):
        state = WorldState()
        assert state.world_layer == "real"
        assert state.is_wrong_layer() is False

    def test_enter_and_exit_wrong_layer(self):
        state = WorldState()
        state.enter_wrong_layer()
        assert state.world_layer == "wrong"
        assert state.is_wrong_layer() is True
        state.exit_wrong_layer()
        assert state.world_layer == "real"
        assert state.is_wrong_layer() is False

    def test_persists_across_serialisation(self):
        state = WorldState()
        state.enter_wrong_layer()
        restored = WorldState.from_dict(state.to_dict())
        assert restored.world_layer == "wrong"

    def test_invalid_layer_coerced_on_load(self):
        restored = WorldState.from_dict({"world_layer": "nonsense"})
        assert restored.world_layer == "real"

    def test_validate_rejects_bad_layer(self):
        state = WorldState()
        state.world_layer = "other"  # type: ignore - intentionally wrong
        with pytest.raises(ValueError, match="world_layer"):
            state.validate()


class TestWrongnessLog:
    """Tests for the accumulating wrongness log."""

    def test_empty_by_default(self):
        state = WorldState()
        assert state.wrongness.count() == 0
        assert state.wrongness.threshold_met(n=1) is False

    def test_add_logs_new_anomaly(self):
        log = WrongnessLog()
        assert log.add("fox_tracks", "tracks end mid-stride") is True
        assert log.count() == 1
        assert log.has("fox_tracks") is True

    def test_add_is_idempotent_per_anomaly(self):
        log = WrongnessLog()
        assert log.add("fox_tracks") is True
        assert log.add("fox_tracks") is False
        assert log.count() == 1

    def test_seen_at_reflects_insertion_order(self):
        log = WrongnessLog()
        log.add("a")
        log.add("b")
        log.add("c")
        assert [e.seen_at for e in log.entries] == [0, 1, 2]
        assert [e.anomaly_id for e in log.entries] == ["a", "b", "c"]

    def test_threshold_met(self):
        log = WrongnessLog()
        log.add("a")
        log.add("b")
        assert log.threshold_met(n=3) is False
        log.add("c")
        assert log.threshold_met(n=3) is True

    def test_acknowledge(self):
        log = WrongnessLog()
        log.add("a")
        assert log.acknowledged_count() == 0
        assert log.acknowledge("a") is True
        assert log.acknowledged_count() == 1
        assert log.acknowledge("missing") is False

    def test_serialisation_round_trip(self):
        state = WorldState()
        state.wrongness.add("fox_tracks", "tracks end mid-stride")
        state.wrongness.add("hare", "unbreathing hare")
        state.wrongness.acknowledge("fox_tracks")

        restored = WorldState.from_dict(state.to_dict())
        assert restored.wrongness.count() == 2
        assert restored.wrongness.has("fox_tracks")
        ack = [e for e in restored.wrongness.entries if e.anomaly_id == "fox_tracks"][0]
        assert ack.acknowledged is True
        assert ack.description == "tracks end mid-stride"

    def test_from_dict_handles_missing_wrongness(self):
        restored = WorldState.from_dict({"has_power": True})
        assert restored.wrongness.count() == 0

    def test_validate_rejects_non_log(self):
        state = WorldState()
        state.wrongness = {}  # type: ignore - intentionally wrong
        with pytest.raises(ValueError, match="wrongness"):
            state.validate()
