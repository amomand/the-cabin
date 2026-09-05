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
        from game.world_state import WorldState
        map_mock.world_state = WorldState()
        
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
    
    def test_look_is_always_a_revisit(self, action, mock_context):
        """Arriving showed the room once; a look from inside it must not narrate the arrival again."""
        mock_context.intent.reply = None
        mock_context.intent.args = {}

        action.execute(mock_context)

        mock_context.map.current_room.get_description.assert_called_once_with(
            mock_context.player, mock_context.world_state, revisit=True
        )

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
        from game.world_state import WorldState
        map_mock.world_state = WorldState()
        
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


@pytest.mark.parametrize("action", [LookAction(), ListenAction()])
def test_morning_landscape_cannot_be_rewritten_by_model_flavour(action, sample_map, sample_player):
    from game.actions.base import ModelEffectsPolicy
    from game.ai.types import Intent
    sample_map.world_state.first_morning = True
    sample_map._set_current_room_by_id("lakeside")
    intent = Intent(action.name, {}, 1.0, reply="A gust carries birdsong across the open water.")
    before = sample_map.world_state.to_dict()
    result = action.execute(ActionContext(player=sample_player, map=sample_map, intent=intent))
    assert "gust" not in result.feedback and "birdsong" not in result.feedback
    assert result.model_effects is ModelEffectsPolicy.BLOCK
    assert sample_map.world_state.to_dict() == before
