"""Tests for UseAction and related actions."""

import pytest
from unittest.mock import MagicMock

from game.actions.use import UseAction, UseCircuitBreakerAction, TurnOnLightsAction
from game.actions.base import ActionContext
from game.world_state import WorldState


class TestUseAction:
    """Tests for UseAction."""
    
    @pytest.fixture
    def action(self):
        return UseAction()
    
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
        assert action.name == "use"
    
    def test_use_without_item_fails(self, action, mock_context):
        mock_context.intent.args = {}
        mock_context.intent.reply = None
        
        result = action.execute(mock_context)
        
        assert result.success is False
        assert "Use what" in result.feedback
    
    def test_use_item_not_in_inventory(self, action, mock_context):
        mock_context.intent.args = {"item": "hammer"}
        mock_context.intent.reply = None
        mock_context.player.get_item.return_value = None
        mock_context.player._clean_item_name.return_value = "hammer"
        
        result = action.execute(mock_context)
        
        assert result.success is False
        assert "don't have" in result.feedback
    
    def test_use_circuit_breaker(self, action, mock_context):
        mock_context.intent.args = {"item": "circuit breaker"}
        mock_context.intent.reply = None
        
        item = MagicMock()
        item.name = "circuit breaker"
        mock_context.player.get_item.return_value = item
        
        result = action.execute(mock_context)
        
        assert result.success is True
        assert "power_restored" in result.events
        assert mock_context.world_state.has_power is True
    
    def test_use_matches_with_firewood(self, action, mock_context):
        mock_context.intent.args = {"item": "matches"}
        mock_context.intent.reply = None
        
        item = MagicMock()
        item.name = "matches"
        mock_context.player.get_item.return_value = item
        mock_context.player.has_item.return_value = True  # has firewood
        
        result = action.execute(mock_context)
        
        assert result.success is True
        assert "fire_lit" in result.events
        assert mock_context.world_state.fire_lit is True
    
    def test_use_matches_without_firewood(self, action, mock_context):
        mock_context.intent.args = {"item": "matches"}
        mock_context.intent.reply = None
        
        item = MagicMock()
        item.name = "matches"
        mock_context.player.get_item.return_value = item
        mock_context.player.has_item.return_value = False
        
        result = action.execute(mock_context)
        
        assert result.success is True
        assert "fire_no_fuel" in result.events
        assert "nothing to light" in result.feedback
    
    def test_use_light_switch_with_power(self, action, mock_context):
        mock_context.intent.args = {"item": "light switch"}
        mock_context.intent.reply = None
        mock_context.world_state.has_power = True
        
        item = MagicMock()
        item.name = "light switch"
        mock_context.player.get_item.return_value = item
        
        result = action.execute(mock_context)
        
        assert result.success is True
        assert "lights_on" in result.events
    
    def test_use_light_switch_without_power(self, action, mock_context):
        mock_context.intent.args = {"item": "light switch"}
        mock_context.intent.reply = None
        mock_context.world_state.has_power = False
        
        item = MagicMock()
        item.name = "light switch"
        mock_context.player.get_item.return_value = item
        
        result = action.execute(mock_context)
        
        assert result.success is True
        assert "remains dark" in result.feedback
    
    def test_use_generic_item(self, action, mock_context):
        mock_context.intent.args = {"item": "key"}
        mock_context.intent.reply = None
        
        item = MagicMock()
        item.name = "key"
        mock_context.player.get_item.return_value = item
        mock_context.player.has_item.return_value = False
        
        result = action.execute(mock_context)
        
        assert result.success is True
        assert "item_used" in result.events


class TestUseCircuitBreakerAction:
    """Tests for UseCircuitBreakerAction (room-based)."""
    
    @pytest.fixture
    def action(self):
        return UseCircuitBreakerAction()
    
    @pytest.fixture
    def mock_context(self):
        player = MagicMock()
        map_mock = MagicMock()
        intent = MagicMock()
        intent.reply = None
        intent.args = {}
        
        room = MagicMock()
        map_mock.current_room = room
        map_mock.world_state = WorldState()
        
        return ActionContext(player=player, map=map_mock, intent=intent)
    
    def test_action_name(self, action):
        assert action.name == "use_circuit_breaker"
    
    def test_use_when_present(self, action, mock_context):
        mock_context.map.current_room.has_item.return_value = True
        
        result = action.execute(mock_context)
        
        assert result.success is True
        assert "power_restored" in result.events
        assert mock_context.world_state.has_power is True
    
    def test_use_when_not_present(self, action, mock_context):
        mock_context.map.current_room.has_item.return_value = False
        
        result = action.execute(mock_context)
        
        assert result.success is False
        assert "no circuit breaker here" in result.feedback


class TestTurnOnLightsAction:
    """Tests for TurnOnLightsAction."""
    
    @pytest.fixture
    def action(self):
        return TurnOnLightsAction()
    
    @pytest.fixture
    def mock_context(self):
        player = MagicMock()
        map_mock = MagicMock()
        intent = MagicMock()
        intent.reply = None
        intent.args = {}
        
        room = MagicMock()
        map_mock.current_room = room
        map_mock.world_state = WorldState()
        
        return ActionContext(player=player, map=map_mock, intent=intent)
    
    def test_action_name(self, action):
        assert action.name == "turn_on_lights"
    
    def test_no_light_switch(self, action, mock_context):
        mock_context.map.current_room.has_item.return_value = False
        
        result = action.execute(mock_context)
        
        assert result.success is False
        assert "no light switch" in result.feedback
    
    def test_with_power(self, action, mock_context):
        mock_context.map.current_room.has_item.return_value = True
        mock_context.world_state.has_power = True
        
        result = action.execute(mock_context)
        
        assert result.success is True
        assert "lights_on" in result.events
    
    def test_without_power(self, action, mock_context):
        mock_context.map.current_room.has_item.return_value = True
        mock_context.world_state.has_power = False
        
        result = action.execute(mock_context)
        
        assert result.success is True
        assert "unresponsive" in result.feedback
