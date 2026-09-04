"""Tests for UseAction and related actions."""

import pytest
from unittest.mock import MagicMock

from game.actions.use import UseAction, UseCircuitBreakerAction, TurnOnLightsAction
from game.actions.base import ActionContext, ModelEffectsPolicy
from game.events.requests import (
    FireAttemptRequest,
    FireLitRequest,
    LightSwitchUsedRequest,
    PowerRestoredRequest,
)
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
        room.id = "cabin_main"
        map_mock.current_room = room
        map_mock.world_state = WorldState()
        
        return ActionContext(player=player, map=map_mock, intent=intent)
    
    def test_use_without_item_fails(self, action, mock_context):
        mock_context.intent.args = {}
        mock_context.intent.reply = None
        
        result = action.execute(mock_context)
        
        assert result.success is False
        assert "finds only air" in result.feedback
    
    def test_use_item_not_in_inventory(self, action, mock_context):
        mock_context.intent.args = {"item": "hammer"}
        mock_context.intent.reply = None
        mock_context.player.get_item.return_value = None
        mock_context.player._clean_item_name.return_value = "hammer"
        # Also absent from the room (falls through to inventory failure path)
        mock_context.room.get_item.return_value = None
        
        result = action.execute(mock_context)
        
        assert result.success is False
        assert "closes on empty air" in result.feedback
    
    def test_use_circuit_breaker(self, action, mock_context):
        mock_context.intent.args = {"item": "circuit breaker"}
        mock_context.intent.reply = "The model replaces the breaker beat."
        mock_context.intent.effects = {"fear": 5}
        
        item = MagicMock()
        item.name = "circuit breaker"
        mock_context.player.get_item.return_value = item
        
        result = action.execute(mock_context)
        
        assert result.success is True
        assert result.requests == (PowerRestoredRequest(),)
        assert "fridge shudders awake" in result.feedback
        assert "model" not in result.feedback
        assert result.model_effects is ModelEffectsPolicy.BLOCK
        assert mock_context.intent.effects == {"fear": 5}
        assert mock_context.world_state.has_power is True
    
    def test_use_matches_with_firewood(self, action, mock_context):
        mock_context.intent.args = {"item": "matches"}
        mock_context.intent.reply = "The model replaces the fire beat."
        mock_context.intent.effects = {"fear": 5}
        
        item = MagicMock()
        item.name = "matches"
        mock_context.player.get_item.return_value = item
        mock_context.player.has_item.return_value = True  # has firewood
        
        result = action.execute(mock_context)
        
        assert result.success is True
        assert result.requests == (FireLitRequest(fear_reduction=5),)
        assert "kindling catches" in result.feedback
        assert "model" not in result.feedback
        assert result.model_effects is ModelEffectsPolicy.BLOCK
        assert mock_context.intent.effects == {"fear": 5}
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
        assert result.requests == (
            FireAttemptRequest(has_fuel=False, has_matches=True),
        )
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
        assert result.requests == (LightSwitchUsedRequest(has_power=True),)
    
    def test_use_light_switch_without_power(self, action, mock_context):
        mock_context.intent.args = {"item": "light switch"}
        mock_context.intent.reply = None
        mock_context.world_state.has_power = False
        
        item = MagicMock()
        item.name = "light switch"
        mock_context.player.get_item.return_value = item
        
        result = action.execute(mock_context)
        
        assert result.success is True
        assert "Darkness stays" in result.feedback
    
    def test_use_generic_item(self, action, mock_context):
        mock_context.intent.args = {"item": "key"}
        mock_context.intent.reply = None
        
        item = MagicMock()
        item.name = "key"
        mock_context.player.get_item.return_value = item
        mock_context.player.has_item.return_value = False
        
        result = action.execute(mock_context)
        
        assert result.success is True
        assert result.requests == ()
        assert result.feedback == "You try the key against the nearest lock. It does not enter."

    def test_use_rope_tests_the_object_instead_of_confirming_the_command(
        self, action, mock_context
    ):
        mock_context.intent.args = {"item": "rope"}
        mock_context.intent.reply = None

        item = MagicMock()
        item.name = "rope"
        mock_context.player.get_item.return_value = item

        result = action.execute(mock_context)

        assert "pull the rope between both hands" in result.feedback.lower()
        assert result.feedback != "You use the rope."


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
        room.id = "cabin_main"
        map_mock.current_room = room
        map_mock.world_state = WorldState()
        
        return ActionContext(player=player, map=map_mock, intent=intent)
    
    def test_use_when_present(self, action, mock_context):
        mock_context.map.current_room.has_item.return_value = True
        mock_context.intent.reply = "The model replaces the breaker beat."
        mock_context.intent.effects = {"fear": 5}
        
        result = action.execute(mock_context)
        
        assert result.success is True
        assert result.requests == (PowerRestoredRequest(),)
        assert "fridge shudders awake" in result.feedback
        assert result.model_effects is ModelEffectsPolicy.BLOCK
        assert mock_context.intent.effects == {"fear": 5}
        assert mock_context.world_state.has_power is True
    
    def test_use_when_not_present(self, action, mock_context):
        mock_context.map.current_room.has_item.return_value = False
        
        result = action.execute(mock_context)
        
        assert result.success is False
        assert "wall and cold paint" in result.feedback


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
        room.id = "cabin_main"
        map_mock.current_room = room
        map_mock.world_state = WorldState()
        
        return ActionContext(player=player, map=map_mock, intent=intent)
    
    def test_no_light_switch(self, action, mock_context):
        mock_context.map.current_room.has_item.return_value = False
        
        result = action.execute(mock_context)
        
        assert result.success is False
        assert "finds no switch" in result.feedback
    
    def test_with_power(self, action, mock_context):
        mock_context.map.current_room.has_item.return_value = True
        mock_context.world_state.has_power = True
        mock_context.intent.reply = "The model replaces the light beat."
        mock_context.intent.effects = {"fear": 5}
        
        result = action.execute(mock_context)
        
        assert result.success is True
        assert result.requests == (LightSwitchUsedRequest(has_power=True),)
        assert "ceiling bulb burns weak and yellow" in result.feedback
        assert result.model_effects is ModelEffectsPolicy.BLOCK
        assert mock_context.intent.effects == {"fear": 5}
    
    def test_without_power(self, action, mock_context):
        mock_context.map.current_room.has_item.return_value = True
        mock_context.world_state.has_power = False
        
        result = action.execute(mock_context)
        
        assert result.success is True
        assert "Darkness stays" in result.feedback
