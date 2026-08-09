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
        map_mock.current_room = room
        map_mock.observe_current_room.return_value = ""
        
        return ActionContext(player=player, map=map_mock, intent=intent)
    
    def test_uses_ai_reply_when_provided(self, action, mock_context):
        """Uses AI reply when available."""
        mock_context.intent.reply = "You see shadows dancing."
        mock_context.intent.args = {}
        
        result = action.execute(mock_context)
        
        assert result.success is True
        assert result.feedback == "You see shadows dancing."

    def test_authored_attention_prose_wins_over_ai_reply(self, action, mock_context):
        """Authored tells are not suppressed by AI look prose."""
        mock_context.intent.reply = "You see only trees."
        mock_context.intent.args = {}
        mock_context.map.observe_current_room.return_value = "The fox tracks end."

        result = action.execute(mock_context)

        assert result.success is True
        assert "fox tracks end" in result.feedback
        assert "only trees" not in result.feedback
    
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
        map_mock.current_room = room
        map_mock.observe_current_room.return_value = ""
        
        return ActionContext(player=player, map=map_mock, intent=intent)
    
    def test_uses_ai_reply_when_provided(self, action, mock_context):
        """Uses AI reply when available."""
        mock_context.intent.reply = "You hear rustling."
        mock_context.intent.args = {}
        
        result = action.execute(mock_context)
        
        assert result.success is True
        assert result.feedback == "You hear rustling."

    def test_authored_attention_prose_wins_over_ai_reply(self, action, mock_context):
        """Authored listen tells are not suppressed by AI listen prose."""
        mock_context.intent.reply = "The woods sound ordinary."
        mock_context.intent.args = {}
        mock_context.map.observe_current_room.return_value = "The hare does not breathe."

        result = action.execute(mock_context)

        assert result.success is True
        assert result.feedback == "The hare does not breathe."

    def test_default_outdoors_when_no_authored_prose(self, action, mock_context):
        """Returns the outdoor ambient line when there is no authored tell."""
        mock_context.intent.reply = None
        mock_context.intent.args = {}
        mock_context.map.current_room.is_indoors = False

        result = action.execute(mock_context)

        assert result.feedback == "Wind moves high in the trees. Near the ground, nothing answers."

    def test_default_indoors_does_not_put_trees_inside(self, action, mock_context):
        mock_context.intent.reply = None
        mock_context.intent.args = {}
        mock_context.map.current_room.is_indoors = True

        result = action.execute(mock_context)

        assert result.feedback == "You hold still. A board ticks once, then settles. Nothing else."
        assert "trees" not in result.feedback
