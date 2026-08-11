"""Tests for MoveAction."""

import copy
import pickle

import pytest
from unittest.mock import MagicMock, PropertyMock

from game.actions.base import ActionContext
from game.actions.move import MoveAction
from game.events.requests import PlayerMovedRequest
from game.map import MoveOutcome


def test_move_outcome_preserves_legacy_two_tuple_contract():
    outcome = MoveOutcome.story(False, "The path closes.")

    assert isinstance(outcome, tuple)
    assert outcome == (False, "The path closes.")
    assert len(outcome) == 2
    assert outcome[0] is False
    assert outcome[1] == "The path closes."
    assert tuple(outcome) == (False, "The path closes.")
    assert outcome.moved is False
    assert outcome.message == "The path closes."
    assert outcome.story_beat is True


@pytest.mark.parametrize(
    "reconstruct",
    [copy.copy, copy.deepcopy, lambda value: pickle.loads(pickle.dumps(value))],
)
def test_move_outcome_preserves_metadata_when_reconstructed(reconstruct):
    outcome = MoveOutcome.story(False, "The path closes.")

    reconstructed = reconstruct(outcome)

    assert reconstructed == outcome
    assert reconstructed.story_beat is True


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

        def move_to_new_room(direction, player):
            mock_context.map.current_room = MagicMock(id="new_room")
            return True, ""

        mock_context.map.move.side_effect = move_to_new_room
        
        result = action.execute(mock_context)
        
        assert result.success is True
        assert result.feedback == ""
        assert result.requests == (
            PlayerMovedRequest(
                from_room_id="start_room",
                to_room_id="new_room",
                direction="north",
            ),
        )

    def test_successful_move_preserves_story_beat_message(self, action, mock_context):
        """Authored movement beats from Map.move surface through the action."""
        mock_context.intent.args = {"direction": "north"}
        mock_context.intent.reply = None
        mock_context.map.move.return_value = (True, "The clearing is wrong.")
        mock_context.map.current_room.id = "new_room"

        result = action.execute(mock_context)

        assert result.success is True
        assert result.feedback == "The clearing is wrong."
    
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
