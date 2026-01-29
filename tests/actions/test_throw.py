"""Tests for ThrowAction."""

import pytest
from unittest.mock import MagicMock

from game.actions.throw import ThrowAction
from game.actions.base import ActionContext


class TestThrowAction:
    """Tests for ThrowAction."""
    
    @pytest.fixture
    def action(self):
        return ThrowAction()
    
    @pytest.fixture
    def mock_context(self):
        player = MagicMock()
        map_mock = MagicMock()
        intent = MagicMock()
        
        room = MagicMock()
        map_mock.current_room = room
        
        return ActionContext(player=player, map=map_mock, intent=intent)
    
    def test_action_name(self, action):
        assert action.name == "throw"
    
    def test_throw_without_item_fails(self, action, mock_context):
        mock_context.intent.args = {}
        mock_context.intent.reply = None
        
        result = action.execute(mock_context)
        
        assert result.success is False
        assert "Throw what" in result.feedback
    
    def test_throw_item_not_in_inventory(self, action, mock_context):
        mock_context.intent.args = {"item": "rock"}
        mock_context.intent.reply = None
        mock_context.player.get_item.return_value = None
        mock_context.player._clean_item_name.return_value = "rock"
        
        result = action.execute(mock_context)
        
        assert result.success is False
        assert "don't have" in result.feedback
    
    def test_throw_non_throwable_item(self, action, mock_context):
        mock_context.intent.args = {"item": "piano"}
        mock_context.intent.reply = None
        
        item = MagicMock()
        item.name = "piano"
        item.is_throwable.return_value = False
        mock_context.player.get_item.return_value = item
        
        result = action.execute(mock_context)
        
        assert result.success is False
        assert "isn't something you can throw" in result.feedback
    
    def test_throw_into_darkness(self, action, mock_context):
        mock_context.intent.args = {"item": "stone"}
        mock_context.intent.reply = None
        
        item = MagicMock()
        item.name = "stone"
        item.is_throwable.return_value = True
        mock_context.player.get_item.return_value = item
        mock_context.map.current_room.has_wildlife.return_value = False
        
        result = action.execute(mock_context)
        
        assert result.success is True
        assert "item_thrown" in result.events
        assert "thrown_into_darkness" in result.events
        assert result.state_changes.get("fear_increase") == 5
    
    def test_throw_at_wildlife_attack(self, action, mock_context):
        mock_context.intent.args = {"item": "stone", "target": "wolf"}
        mock_context.intent.reply = None
        
        item = MagicMock()
        item.name = "stone"
        item.is_throwable.return_value = True
        mock_context.player.get_item.return_value = item
        
        mock_context.map.current_room.has_wildlife.return_value = True
        
        wolf = MagicMock()
        wolf.provoke.return_value = {
            "action": "attack",
            "message": "The wolf lunges at you!",
            "health_damage": 15,
            "fear_increase": 20
        }
        mock_context.map.current_room.get_wildlife.return_value = wolf
        
        result = action.execute(mock_context)
        
        assert result.success is True
        assert "wildlife_attack" in result.events
        assert result.state_changes["health_damage"] == 15
    
    def test_throw_at_wildlife_flee(self, action, mock_context):
        mock_context.intent.args = {"item": "stone", "target": "rabbit"}
        mock_context.intent.reply = None
        
        item = MagicMock()
        item.name = "stone"
        item.is_throwable.return_value = True
        mock_context.player.get_item.return_value = item
        
        mock_context.map.current_room.has_wildlife.return_value = True
        
        rabbit = MagicMock()
        rabbit.provoke.return_value = {
            "action": "flee",
            "message": "The rabbit bolts into the underbrush.",
            "remove_from_room": True
        }
        mock_context.map.current_room.get_wildlife.return_value = rabbit
        
        result = action.execute(mock_context)
        
        assert result.success is True
        assert "wildlife_fled" in result.events
        mock_context.map.current_room.remove_wildlife.assert_called_once()
