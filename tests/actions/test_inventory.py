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
    
    def test_take_without_item_name_fails(self, action, mock_context):
        mock_context.intent.args = {}
        mock_context.intent.reply = None
        
        result = action.execute(mock_context)
        
        assert result.success is False
        assert "uncertain what to close around" in result.feedback
    
    def test_take_carryable_item(self, action, mock_context):
        mock_context.intent.args = {"item": "rope"}
        mock_context.intent.reply = None
        
        item = MagicMock()
        item.name = "rope"
        item.is_carryable.return_value = True
        item.is_person.return_value = False
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
        item.is_person.return_value = False
        mock_context.map.current_room.remove_item.return_value = item
        
        result = action.execute(mock_context)
        
        assert "fuel_gathered" in result.events
    
    def test_take_non_carryable_item(self, action, mock_context):
        mock_context.intent.args = {"item": "boulder"}
        mock_context.intent.reply = None
        
        item = MagicMock()
        item.name = "boulder"
        item.is_carryable.return_value = False
        item.is_person.return_value = False
        mock_context.map.current_room.remove_item.return_value = item

        result = action.execute(mock_context)

        assert result.success is False
        assert "stays fixed" in result.feedback
        mock_context.map.current_room.add_item.assert_called_once_with(item)

    @staticmethod
    def _person_in_room(mock_context, *, wrong_layer=True, ending="none"):
        """Put Nika in the room and pin the layer/ending the beat depends on."""
        item = MagicMock()
        item.name = "nika"
        item.is_carryable.return_value = False
        item.is_person.return_value = True
        mock_context.map.current_room.remove_item.return_value = item
        mock_context.map.world_state.is_wrong_layer.return_value = wrong_layer
        mock_context.map.world_state.ending = ending
        return item

    def test_taking_a_person_is_not_answered_with_the_fixture_line(self, action, mock_context):
        """A person is not furniture. "The nika stays fixed in the room" was
        both ungrammatical and a reduction of her at the reunion (#168)."""
        mock_context.intent.args = {"item": "nika"}
        mock_context.intent.reply = None
        item = self._person_in_room(mock_context)

        result = action.execute(mock_context)

        assert result.success is False
        assert "stays fixed" not in result.feedback
        assert "The nika" not in result.feedback
        assert "She is not a thing to be picked up" in result.feedback
        mock_context.map.current_room.add_item.assert_called_once_with(item)

    def test_real_layer_take_agrees_with_use_that_she_is_not_here(self, action, mock_context):
        """Nika sits in cabin_main.items in both layers. Without a layer gate,
        `take nika` said she was standing there while `use nika` said she was
        not — two authored lines, same fixture, opposite facts."""
        mock_context.intent.args = {"item": "nika"}
        mock_context.intent.reply = None
        self._person_in_room(mock_context, wrong_layer=False)

        result = action.execute(mock_context)

        assert result.success is False
        assert result.feedback == "Nika isn't here."

    def test_after_the_refusal_the_thing_in_her_fleece_is_not_called_her(self, action, mock_context):
        """UseAction deliberately refuses to call it her once Elli has walked
        out. The take path must not undo that."""
        mock_context.intent.args = {"item": "nika"}
        mock_context.intent.reply = None
        self._person_in_room(mock_context, ending="escaped")

        result = action.execute(mock_context)

        assert result.success is False
        assert "She is not a thing" not in result.feedback
        assert "Nika's fleece" in result.feedback

    def test_the_authored_person_line_wins_over_model_prose(self, action, mock_context):
        """Authored prose is canonical here. Deferring to ai_reply would hand
        the beat back to the one thing this branch exists to catch."""
        mock_context.intent.args = {"item": "nika"}
        mock_context.intent.reply = "You lift Nika like a parcel and stow her away."
        self._person_in_room(mock_context)

        result = action.execute(mock_context)

        assert result.success is False
        assert "parcel" not in result.feedback
        assert "She is not a thing to be picked up" in result.feedback

    def test_a_person_is_never_pocketed_even_if_marked_carryable(self, action, mock_context):
        """Person is checked before carryability, so no trait combination can
        put her in the bag."""
        mock_context.intent.args = {"item": "nika"}
        mock_context.intent.reply = None

        item = MagicMock()
        item.name = "nika"
        item.is_carryable.return_value = True
        item.is_person.return_value = True
        mock_context.map.current_room.remove_item.return_value = item

        result = action.execute(mock_context)

        assert result.success is False
        mock_context.player.add_item.assert_not_called()
        mock_context.map.current_room.add_item.assert_called_once_with(item)
    
    def test_take_nonexistent_item(self, action, mock_context):
        mock_context.intent.args = {"item": "unicorn"}
        mock_context.intent.reply = None
        mock_context.map.current_room.remove_item.return_value = None
        mock_context.map.current_room._clean_item_name.return_value = "unicorn"
        
        result = action.execute(mock_context)
        
        assert result.success is False
        assert "Only cold air answers" in result.feedback


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
    
    def test_drop_without_item_name_fails(self, action, mock_context):
        mock_context.intent.args = {}
        mock_context.intent.reply = None
        
        result = action.execute(mock_context)
        
        assert result.success is False
        assert "opens around nothing" in result.feedback
    
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
        assert "not with you" in result.feedback
