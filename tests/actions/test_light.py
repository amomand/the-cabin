"""Tests for LightAction."""

import pytest
from unittest.mock import MagicMock

from game.actions.light import LightAction
from game.actions.base import ActionContext
from game.world_state import WorldState


class TestLightAction:
    """Tests for LightAction."""
    
    @pytest.fixture
    def action(self):
        return LightAction()
    
    @pytest.fixture
    def mock_context(self):
        player = MagicMock()
        map_mock = MagicMock()
        intent = MagicMock()
        
        room = MagicMock()
        map_mock.current_room = room
        map_mock.world_state = WorldState()
        
        return ActionContext(player=player, map=map_mock, intent=intent)
    
    def test_action_name(self, action):
        assert action.name == "light"
    
    def test_light_fire_with_fuel_and_matches(self, action, mock_context):
        mock_context.intent.args = {"target": "fireplace"}
        mock_context.intent.reply = None
        mock_context.player.has_item.side_effect = lambda x: x in ["firewood", "matches"]
        
        result = action.execute(mock_context)
        
        assert result.success is True
        assert "fire_lit" in result.events
        assert mock_context.world_state.fire_lit is True
    
    def test_light_fire_without_matches(self, action, mock_context):
        mock_context.intent.args = {"target": "fire"}
        mock_context.intent.reply = None
        mock_context.player.has_item.side_effect = lambda x: x == "firewood"
        
        result = action.execute(mock_context)
        
        assert result.success is False
        assert "need matches" in result.feedback
    
    def test_light_fire_without_fuel(self, action, mock_context):
        mock_context.intent.args = {"target": "fireplace"}
        mock_context.intent.reply = None
        mock_context.player.has_item.return_value = False
        
        result = action.execute(mock_context)
        
        assert result.success is True  # Triggers event, not a hard failure
        assert "use_fireplace_no_fuel" in result.events
    
    def test_light_unknown_target(self, action, mock_context):
        mock_context.intent.args = {"target": "rock"}
        mock_context.intent.reply = None
        
        result = action.execute(mock_context)
        
        assert result.success is False
        assert "can't light" in result.feedback
    
    def test_uses_ai_reply(self, action, mock_context):
        mock_context.intent.args = {"target": "fire"}
        mock_context.intent.reply = "The flames dance to life."
        mock_context.player.has_item.return_value = True
        
        result = action.execute(mock_context)
        
        assert result.feedback == "The flames dance to life."
