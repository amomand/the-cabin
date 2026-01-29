"""
Tests for WorldState typed state management.
"""
import pytest
from game.world_state import WorldState


class TestWorldState:
    """Tests for WorldState dataclass."""

    def test_default_values(self):
        """WorldState should have sensible defaults."""
        state = WorldState()
        assert state.has_power is False
        assert state.fire_lit is False

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
            "custom_flag": "custom_value",
        }
        
        state = WorldState.from_dict(data)
        
        assert state.has_power is True
        assert state.fire_lit is True
        assert state.get_flag("custom_flag") == "custom_value"

    def test_from_dict_round_trip(self):
        """WorldState survives serialization round-trip."""
        original = WorldState(has_power=True)
        original.set_flag("quest_progress", 3)
        
        restored = WorldState.from_dict(original.to_dict())
        
        assert restored.has_power == original.has_power
        assert restored.fire_lit == original.fire_lit
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
