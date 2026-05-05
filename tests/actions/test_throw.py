"""Tests for ThrowAction."""

import pytest
from unittest.mock import MagicMock

from game.actions.throw import (
    DEFAULT_INDOOR_THROW_FEEDBACK,
    INDOOR_THROW_FEEDBACK,
    ThrowAction,
)
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
        room.id = "wilderness_start"
        room.is_indoors = False
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

    def test_throw_into_darkness_uses_ai_reply_outdoors(self, action, mock_context):
        mock_context.intent.args = {"item": "stone"}
        mock_context.intent.reply = "The stone skips away between the black pines."
        
        item = MagicMock()
        item.name = "stone"
        item.is_throwable.return_value = True
        mock_context.player.get_item.return_value = item
        mock_context.map.current_room.has_wildlife.return_value = False
        
        result = action.execute(mock_context)
        
        assert result.success is True
        assert result.feedback == "The stone skips away between the black pines."
        assert "thrown_into_darkness" in result.events
        assert result.state_changes.get("fear_increase") == 5

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
        mock_context.map.current_room.has_wildlife.return_value = False
        
        result = action.execute(mock_context)
        feedback = result.feedback.lower()
        
        assert result.success is True
        assert "item_thrown" in result.events
        assert "thrown_into_darkness" not in result.events
        assert "fear_increase" not in result.state_changes
        assert result.feedback == INDOOR_THROW_FEEDBACK[room_id].format(item_name="stone")
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
        mock_context.map.current_room.has_wildlife.return_value = False
        
        result = action.execute(mock_context)
        
        assert result.success is True
        assert result.feedback == DEFAULT_INDOOR_THROW_FEEDBACK.format(item_name="stone")
        assert "thrown_into_darkness" not in result.events
        assert "fear_increase" not in result.state_changes

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
        assert "thrown_into_darkness" not in result.events
        assert "fear_increase" not in result.state_changes
        assert "snow" not in feedback
        assert "trees" not in feedback
        assert "darkness" not in feedback
    
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
