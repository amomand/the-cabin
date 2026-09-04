"""Tests for HelpAction."""

from unittest.mock import MagicMock

import pytest

from game.actions.help import HelpAction
from game.actions.base import ActionContext
from game.ai_interpreter import Intent
from game.devtools.seed_saves import SEEDS


def _help_for(state) -> str:
    ctx = ActionContext(player=state.player, map=state.map, intent=Intent("help", {}, 1.0))
    return HelpAction().execute(ctx).feedback


class TestHelpAction:
    def test_help_is_diegetic(self):
        ctx = MagicMock()
        ctx.ai_reply = None
        ctx.world_state = MagicMock()
        ctx.map.false_cabin_holds_door.return_value = False
        ctx.room.effective_exits.return_value = {"north": ("woods", "track")}

        result = HelpAction().execute(ctx)

        assert result.success is True
        assert "north" in result.feedback
        for leaked in ("go <", "look", "listen", "inventory", "take", "use", "throw"):
            assert leaked not in result.feedback.lower()

    def test_help_deduplicates_aliases_and_names_physical_destinations(
        self, sample_map, sample_player
    ):
        sample_map._set_current_room_by_id("cabin_clearing")
        intent = Intent("help", {}, 1.0)

        result = HelpAction().execute(
            ActionContext(player=sample_player, map=sample_map, intent=intent)
        )

        assert result.feedback.count("the cabin") == 1
        assert "the wilderness" in result.feedback
        assert "north, cabin" not in result.feedback


class TestHelpRespectsTheFalseCabinDoor:
    """Help must not advertise an exit the reunion gate closes (#247)."""

    @pytest.mark.parametrize(
        "seed_name", ["act3_seated", "act3_consented", "act4_night", "act5_dawn"]
    )
    def test_help_does_not_name_the_clearing_while_the_door_is_held(self, seed_name):
        text = _help_for(SEEDS[seed_name]())

        assert "the clearing" not in text
        assert "ways out" not in text
        for leaked in ("no exits", "cannot", "can't", "invalid"):
            assert leaked not in text.lower()

    def test_help_still_lists_exits_where_the_door_opens(self):
        """Guard against over-blocking: the consent beat, the walk out, and
        the real cabin all keep their ways out."""
        consent = SEEDS["act3_seated"]()
        consent.world_state.reunion_stage = "complete"
        assert "the clearing" in _help_for(consent)

        escaped = SEEDS["act5_dawn"]()
        escaped.world_state.ending = "escaped"
        assert "the clearing" in _help_for(escaped)

        real = SEEDS["act1_end"]()
        real.map._set_current_room_by_id("cabin_main")
        assert "ways out" in _help_for(real)


class TestHelpNamesRoomsByLayer:
    """The way out of the black clearing is the woods, not the track she walked in on."""

    def test_walk_out_names_the_wrong_layer_room(self):
        state = SEEDS["act5_dawn"]()
        assert state.world_state.transition_ending_to("escaped")
        moved, _ = state.map.move("out", state.player)
        assert moved and state.map.current_room_id == "cabin_clearing"

        text = _help_for(state)

        assert "the woods" in text
        assert "wood track" not in text
