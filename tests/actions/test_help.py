"""Tests for HelpAction."""

from unittest.mock import MagicMock

from game.actions.help import HelpAction


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
