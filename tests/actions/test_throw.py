"""Tests for ThrowAction."""

import pytest
from unittest.mock import MagicMock

from game.actions.throw import (
    DEFAULT_INDOOR_THROW_FEEDBACK,
    INDOOR_THROW_FEEDBACK,
    ThrowAction,
)
from game.actions.base import ActionContext
from game.events.requests import DarknessFearRequest, ItemThrownRequest


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
        room.id = "wilderness_start"
        room.is_indoors = False
        map_mock.current_room = room
        
        return ActionContext(player=player, map=map_mock, intent=intent)
    
    def test_throw_without_item_fails(self, action, mock_context):
        mock_context.intent.args = {}
        mock_context.intent.reply = None
        
        result = action.execute(mock_context)
        
        assert result.success is False
        assert "tightens around nothing" in result.feedback
    
    def test_throw_item_not_in_inventory(self, action, mock_context):
        mock_context.intent.args = {"item": "rock"}
        mock_context.intent.reply = None
        mock_context.player.get_item.return_value = None
        mock_context.player._clean_item_name.return_value = "rock"
        
        result = action.execute(mock_context)
        
        assert result.success is False
        assert "not with you" in result.feedback
    
    def test_throw_non_throwable_item(self, action, mock_context):
        mock_context.intent.args = {"item": "piano"}
        mock_context.intent.reply = None
        
        item = MagicMock()
        item.name = "piano"
        item.is_throwable.return_value = False
        mock_context.player.get_item.return_value = item
        
        result = action.execute(mock_context)
        
        assert result.success is False
        assert "will not leave your hand" in result.feedback
    
    def test_throw_into_darkness(self, action, mock_context):
        mock_context.intent.args = {"item": "stone"}
        mock_context.intent.reply = None
        
        item = MagicMock()
        item.name = "stone"
        item.is_throwable.return_value = True
        mock_context.player.get_item.return_value = item

        result = action.execute(mock_context)
        
        assert result.success is True
        assert result.requests == (
            ItemThrownRequest(item_name="stone", target=None, into_darkness=False),
            DarknessFearRequest(increase=5),
        )
        assert "nothing answers" in result.feedback.lower()
        assert "something else" not in result.feedback.lower()

    def test_throw_into_darkness_cannot_invent_a_response_from_the_woods(self, action, mock_context):
        mock_context.intent.args = {"item": "stone"}
        mock_context.intent.reply = "The stone skips away between the black pines."
        
        item = MagicMock()
        item.name = "stone"
        item.is_throwable.return_value = True
        mock_context.player.get_item.return_value = item

        result = action.execute(mock_context)
        
        assert result.success is True
        assert "nothing answers" in result.feedback.lower()
        assert "The stone skips" not in result.feedback
        assert result.requests[-1] == DarknessFearRequest(increase=5)

    @pytest.mark.parametrize("room_id", INDOOR_THROW_FEEDBACK.keys())
    def test_untargeted_throw_indoors_uses_room_feedback(self, action, mock_context, room_id):
        mock_context.intent.args = {"item": "stone"}
        mock_context.intent.reply = (
            "The stone disappears into the darkness and lands in snow near the trees."
        )
        mock_context.map.current_room.id = room_id
        mock_context.map.current_room.is_indoors = True
        
        item = MagicMock()
        item.name = "stone"
        item.is_throwable.return_value = True
        mock_context.player.get_item.return_value = item

        result = action.execute(mock_context)
        feedback = result.feedback.lower()
        
        assert result.success is True
        assert result.requests == (
            ItemThrownRequest(item_name="stone", target=None, into_darkness=False),
        )
        assert result.feedback == INDOOR_THROW_FEEDBACK[room_id].format(item_name="stone")
        mock_context.map.current_room.add_item.assert_called_once_with(item)
        assert "snow" not in feedback
        assert "trees" not in feedback
        assert "darkness" not in feedback

    def test_untargeted_throw_uses_generic_indoor_feedback_for_new_indoor_room(self, action, mock_context):
        mock_context.intent.args = {"item": "stone"}
        mock_context.intent.reply = "The stone vanishes into snow and trees."
        mock_context.map.current_room.id = "new_indoor_room"
        mock_context.map.current_room.is_indoors = True
        
        item = MagicMock()
        item.name = "stone"
        item.is_throwable.return_value = True
        mock_context.player.get_item.return_value = item

        result = action.execute(mock_context)
        
        assert result.success is True
        assert result.feedback == DEFAULT_INDOOR_THROW_FEEDBACK.format(item_name="stone")
        mock_context.map.current_room.add_item.assert_called_once_with(item)
        assert result.requests == (
            ItemThrownRequest(item_name="stone", target=None, into_darkness=False),
        )

    def test_untargeted_throw_inside_real_cabin_map_uses_indoor_feedback(
        self, action, sample_map, sample_player
    ):
        intent = MagicMock()
        intent.args = {"item": "stone"}
        intent.reply = "The stone disappears into the darkness and lands in snow near the trees."
        sample_map._set_current_room_by_id("cabin_main", been_here_before=True)
        sample_player.add_item(sample_map.items["stone"])
        
        result = action.execute(ActionContext(player=sample_player, map=sample_map, intent=intent))
        feedback = result.feedback.lower()
        
        assert sample_map.current_room.id == "cabin_main"
        assert sample_map.current_room.is_indoors is True
        assert result.success is True
        assert result.feedback == INDOOR_THROW_FEEDBACK["cabin_main"].format(item_name="stone")
        assert sample_map.current_room.has_item("stone") is True
        assert result.requests == (
            ItemThrownRequest(item_name="stone", target=None, into_darkness=False),
        )
        assert "snow" not in feedback
        assert "trees" not in feedback
        assert "darkness" not in feedback
