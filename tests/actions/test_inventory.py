"""Tests for inventory actions (take, drop, inventory)."""

import pytest
from unittest.mock import MagicMock

from game.actions.inventory import TakeAction, DropAction, InventoryAction
from game.actions.base import ActionContext


class TestInventoryAction:
    """Tests for InventoryAction (check inventory)."""
    
    @pytest.fixture
    def action(self):
        return InventoryAction()
    
    @pytest.fixture
    def mock_context(self):
        player = MagicMock()
        map_mock = MagicMock()
        intent = MagicMock()
        return ActionContext(player=player, map=map_mock, intent=intent)
    
    def test_action_name(self, action):
        assert action.name == "inventory"
    
    def test_uses_ai_reply(self, action, mock_context):
        mock_context.intent.reply = "Your pockets are empty."
        mock_context.intent.args = {}
        
        result = action.execute(mock_context)
        
        assert result.feedback == "Your pockets are empty."
    
    def test_lists_inventory_items(self, action, mock_context):
        mock_context.intent.reply = None
        mock_context.intent.args = {}
        
        item1 = MagicMock()
        item1.name = "rope"
        item2 = MagicMock()
        item2.name = "matches"
        mock_context.player.inventory = [item1, item2]
        
        result = action.execute(mock_context)
        
        assert "rope" in result.feedback
        assert "matches" in result.feedback
    
    def test_empty_inventory_message(self, action, mock_context):
        mock_context.intent.reply = None
        mock_context.intent.args = {}
        mock_context.player.inventory = []
        
        result = action.execute(mock_context)
        
        assert "air and lint" in result.feedback


class TestTakeAction:
    """Tests for TakeAction."""
    
    @pytest.fixture
    def action(self):
        return TakeAction()
    
    @pytest.fixture
    def mock_context(self):
        player = MagicMock()
        map_mock = MagicMock()
        intent = MagicMock()
        
        room = MagicMock()
        map_mock.current_room = room
        
        return ActionContext(player=player, map=map_mock, intent=intent)
    
    def test_action_name(self, action):
        assert action.name == "take"
    
    def test_take_without_item_name_fails(self, action, mock_context):
        mock_context.intent.args = {}
        mock_context.intent.reply = None
        
        result = action.execute(mock_context)
        
        assert result.success is False
        assert "Take what" in result.feedback
    
    def test_take_carryable_item(self, action, mock_context):
        mock_context.intent.args = {"item": "rope"}
        mock_context.intent.reply = None
        
        item = MagicMock()
        item.name = "rope"
        item.is_carryable.return_value = True
        mock_context.map.current_room.remove_item.return_value = item
        
        result = action.execute(mock_context)
        
        assert result.success is True
        assert "item_taken" in result.events
        mock_context.player.add_item.assert_called_once_with(item)
    
    def test_take_firewood_triggers_event(self, action, mock_context):
        mock_context.intent.args = {"item": "firewood"}
        mock_context.intent.reply = None
        
        item = MagicMock()
        item.name = "firewood"
        item.is_carryable.return_value = True
        mock_context.map.current_room.remove_item.return_value = item
        
        result = action.execute(mock_context)
        
        assert "fuel_gathered" in result.events
    
    def test_take_non_carryable_item(self, action, mock_context):
        mock_context.intent.args = {"item": "boulder"}
        mock_context.intent.reply = None
        
        item = MagicMock()
        item.name = "boulder"
        item.is_carryable.return_value = False
        mock_context.map.current_room.remove_item.return_value = item
        
        result = action.execute(mock_context)
        
        assert result.success is False
        assert "can't be picked up" in result.feedback
        mock_context.map.current_room.add_item.assert_called_once_with(item)
    
    def test_take_nonexistent_item(self, action, mock_context):
        mock_context.intent.args = {"item": "unicorn"}
        mock_context.intent.reply = None
        mock_context.map.current_room.remove_item.return_value = None
        mock_context.map.current_room._clean_item_name.return_value = "unicorn"
        
        result = action.execute(mock_context)
        
        assert result.success is False
        assert "no unicorn here" in result.feedback


class TestDropAction:
    """Tests for DropAction."""
    
    @pytest.fixture
    def action(self):
        return DropAction()
    
    @pytest.fixture
    def mock_context(self):
        player = MagicMock()
        map_mock = MagicMock()
        intent = MagicMock()
        
        room = MagicMock()
        map_mock.current_room = room
        
        return ActionContext(player=player, map=map_mock, intent=intent)
    
    def test_action_name(self, action):
        assert action.name == "drop"
    
    def test_drop_without_item_name_fails(self, action, mock_context):
        mock_context.intent.args = {}
        mock_context.intent.reply = None
        
        result = action.execute(mock_context)
        
        assert result.success is False
        assert "Drop what" in result.feedback
    
    def test_drop_item_from_inventory(self, action, mock_context):
        mock_context.intent.args = {"item": "rope"}
        mock_context.intent.reply = None
        
        item = MagicMock()
        item.name = "rope"
        mock_context.player.remove_item.return_value = item
        
        result = action.execute(mock_context)
        
        assert result.success is True
        assert "item_dropped" in result.events
        mock_context.map.current_room.add_item.assert_called_once_with(item)
    
    def test_drop_item_not_in_inventory(self, action, mock_context):
        mock_context.intent.args = {"item": "sword"}
        mock_context.intent.reply = None
        mock_context.player.remove_item.return_value = None
        mock_context.player._clean_item_name.return_value = "sword"
        
        result = action.execute(mock_context)
        
        assert result.success is False
        assert "don't have" in result.feedback
