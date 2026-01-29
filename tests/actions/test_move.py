"""Tests for MoveAction."""

import pytest
from unittest.mock import MagicMock, PropertyMock

from game.actions.move import MoveAction
from game.actions.base import ActionContext


class TestMoveAction:
    """Tests for MoveAction."""
    
    @pytest.fixture
    def action(self):
        return MoveAction()
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock action context."""
        player = MagicMock()
        map_mock = MagicMock()
        intent = MagicMock()
        
        # Set up room with id
        room = MagicMock()
        room.id = "start_room"
        map_mock.current_room = room
        
        return ActionContext(player=player, map=map_mock, intent=intent)
    
    def test_action_name(self, action):
        """Action name is 'move'."""
        assert action.name == "move"
    
    def test_move_without_direction_fails(self, action, mock_context):
        """Moving without a direction fails."""
        mock_context.intent.args = {}
        mock_context.intent.reply = None
        
        result = action.execute(mock_context)
        
        assert result.success is False
        assert "Where" in result.feedback
    
    def test_move_with_ai_reply_on_no_direction(self, action, mock_context):
        """Uses AI reply when no direction given."""
        mock_context.intent.args = {}
        mock_context.intent.reply = "The cold bites. Move where?"
        
        result = action.execute(mock_context)
        
        assert result.success is False
        assert result.feedback == "The cold bites. Move where?"
    
    def test_successful_move(self, action, mock_context):
        """Successful movement returns proper result."""
        mock_context.intent.args = {"direction": "north"}
        mock_context.intent.reply = None
        mock_context.map.move.return_value = (True, "")
        
        # Update room id after move
        mock_context.map.current_room.id = "new_room"
        
        result = action.execute(mock_context)
        
        assert result.success is True
        assert result.feedback == ""  # No feedback during movement
        assert "player_moved" in result.events
        assert "entered_room" in result.events
        assert result.state_changes["direction"] == "north"
    
    def test_failed_move_blocked(self, action, mock_context):
        """Failed movement returns failure result."""
        mock_context.intent.args = {"direction": "north"}
        mock_context.intent.reply = None
        mock_context.map.move.return_value = (False, "You can't go that way.")
        
        result = action.execute(mock_context)
        
        assert result.success is False
        assert "can't go that way" in result.feedback or "path isn't there" in result.feedback
    
    def test_failed_move_with_ai_reply(self, action, mock_context):
        """Uses AI reply on failed movement."""
        mock_context.intent.args = {"direction": "north"}
        mock_context.intent.reply = "The trees block your path."
        mock_context.map.move.return_value = (False, "blocked")
        
        result = action.execute(mock_context)
        
        assert result.success is False
        assert result.feedback == "The trees block your path."
