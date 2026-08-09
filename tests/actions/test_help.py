"""Tests for HelpAction."""

from unittest.mock import MagicMock

from game.actions.help import HelpAction
from game.actions.base import ActionContext
from game.ai_interpreter import Intent


class TestHelpAction:
    def test_help_is_diegetic(self):
        ctx = MagicMock()
        ctx.ai_reply = None
        ctx.world_state = MagicMock()
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
