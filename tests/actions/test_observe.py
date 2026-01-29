"""Tests for observation actions (look, listen)."""

import pytest
from unittest.mock import MagicMock

from game.actions.observe import LookAction, ListenAction
from game.actions.base import ActionContext


class TestLookAction:
    """Tests for LookAction."""
    
    @pytest.fixture
    def action(self):
        return LookAction()
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock action context."""
        player = MagicMock()
        map_mock = MagicMock()
        intent = MagicMock()
        
        room = MagicMock()
        room.get_description.return_value = "A dark forest clearing."
        room.get_items_description.return_value = ""
        room.get_visible_wildlife.return_value = []
        map_mock.current_room = room
        
        return ActionContext(player=player, map=map_mock, intent=intent)
    
    def test_action_name(self, action):
        """Action name is 'look'."""
        assert action.name == "look"
    
    def test_uses_ai_reply_when_provided(self, action, mock_context):
        """Uses AI reply when available."""
        mock_context.intent.reply = "You see shadows dancing."
        mock_context.intent.args = {}
        
        result = action.execute(mock_context)
        
        assert result.success is True
        assert result.feedback == "You see shadows dancing."
    
    def test_builds_description_without_ai_reply(self, action, mock_context):
        """Builds description from room when no AI reply."""
        mock_context.intent.reply = None
        mock_context.intent.args = {}
        
        result = action.execute(mock_context)
        
        assert result.success is True
        assert "dark forest clearing" in result.feedback
    
    def test_includes_items_description(self, action, mock_context):
        """Includes item descriptions in look output."""
        mock_context.intent.reply = None
        mock_context.intent.args = {}
        mock_context.map.current_room.get_items_description.return_value = " A rope lies on the ground."
        
        result = action.execute(mock_context)
        
        assert "rope" in result.feedback
    
    def test_includes_wildlife_description(self, action, mock_context):
        """Includes visible wildlife in look output."""
        mock_context.intent.reply = None
        mock_context.intent.args = {}
        
        fox = MagicMock()
        fox.visual_description = "A fox watches from the treeline."
        mock_context.map.current_room.get_visible_wildlife.return_value = [fox]
        
        result = action.execute(mock_context)
        
        assert "fox watches" in result.feedback


class TestListenAction:
    """Tests for ListenAction."""
    
    @pytest.fixture
    def action(self):
        return ListenAction()
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock action context."""
        player = MagicMock()
        map_mock = MagicMock()
        intent = MagicMock()
        
        room = MagicMock()
        room.get_audible_wildlife.return_value = []
        map_mock.current_room = room
        
        return ActionContext(player=player, map=map_mock, intent=intent)
    
    def test_action_name(self, action):
        """Action name is 'listen'."""
        assert action.name == "listen"
    
    def test_uses_ai_reply_when_provided(self, action, mock_context):
        """Uses AI reply when available."""
        mock_context.intent.reply = "You hear rustling."
        mock_context.intent.args = {}
        
        result = action.execute(mock_context)
        
        assert result.success is True
        assert result.feedback == "You hear rustling."
    
    def test_describes_wildlife_sounds(self, action, mock_context):
        """Describes audible wildlife sounds."""
        mock_context.intent.reply = None
        mock_context.intent.args = {}
        
        owl = MagicMock()
        owl.sound_description = "An owl hoots in the distance."
        mock_context.map.current_room.get_audible_wildlife.return_value = [owl]
        
        result = action.execute(mock_context)
        
        assert "owl hoots" in result.feedback
    
    def test_default_when_no_wildlife(self, action, mock_context):
        """Returns default message when no audible wildlife."""
        mock_context.intent.reply = None
        mock_context.intent.args = {}
        mock_context.map.current_room.get_audible_wildlife.return_value = []
        
        result = action.execute(mock_context)
        
        assert "wind through the trees" in result.feedback
