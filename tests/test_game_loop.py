"""
Tests for GameLoop._execute_action ordering and skip_inventory guard.

GameLoop is currently a latent (un-wired) parallel orchestrator to GameEngine.
These tests pin the same safety contract the engine enforces:

1. Actions execute BEFORE AI-proposed effects apply (so action logic sees
   the player's true state, not an AI-mutated one).
2. AI-proposed inventory deltas are skipped when the action is unknown
   (`result is None`) or failed (`result.success is False`), so a refused
   or unrecognised intent cannot let the model pickpocket the room.
   Fear/health deltas still land.
"""

from unittest.mock import MagicMock, patch

import pytest

from game.actions.base import ActionResult
from game.ai_interpreter import Intent
from game.effects.manager import EffectManager
from game.game_loop import GameLoop


def _make_intent(action: str = "take", effects=None, reply: str = "ok") -> Intent:
    return Intent(
        action=action,
        args={"item": "matches"},
        confidence=0.9,
        reply=reply,
        effects=effects or {},
    )


@pytest.fixture
def loop():
    """A GameLoop with a stub action registry; real EffectManager so we
    exercise the new skip_inventory contract end-to-end."""
    action_registry = MagicMock()
    gl = GameLoop(
        action_registry=action_registry,
        effect_manager=EffectManager(),
    )
    # Ensure no save-side rendering interferes during _execute_action.
    gl.render = MagicMock()
    gl.input = MagicMock()
    return gl


class TestExecuteActionOrdering:
    """Pin the action-first, effects-after order."""

    def test_action_executes_before_effects_apply(self, loop):
        """The action sees the player's pre-effect state, not a state already
        mutated by AI-proposed deltas. Mirrors GameEngine.handle_user_input."""
        call_order = []
        loop.player.fear = 0

        def execute_side_effect(*_args, **_kwargs):
            # When the action runs, the AI's fear delta MUST NOT have applied yet.
            call_order.append(("action", loop.player.fear))
            return ActionResult.success_result("you do the thing")

        loop.actions.execute.side_effect = execute_side_effect

        original_apply = loop.effects.apply_intent_effects

        def apply_spy(*args, **kwargs):
            call_order.append(("effects", loop.player.fear))
            return original_apply(*args, **kwargs)

        loop.effects.apply_intent_effects = apply_spy

        with patch(
            "game.game_loop.interpret",
            return_value=_make_intent(effects={"fear": 2}),
        ):
            loop._execute_action("take matches")

        assert call_order[0][0] == "action", "action must run before effects"
        assert call_order[0][1] == 0, "action saw pre-effect fear"
        assert call_order[1][0] == "effects"
        # After effects, fear has been bumped by the (clamped) +2 delta.
        assert loop.player.fear == 2


class TestSkipInventoryGuard:
    """Pin the engine's skip_inventory contract on GameLoop."""

    def test_failed_action_skips_inventory_add(self, loop):
        """A failed action must NOT let an AI inventory_add land — even if the
        item is genuinely present in the room. Fear/health still apply."""
        room = loop.map.current_room
        # Pick any real room item the AI might try to grab.
        room_items = list(loop.map.items.keys())
        assert room_items, "fixture map should contain items"
        target_item = next(
            (name for name in room_items if room.has_item(name)),
            None,
        )
        if target_item is None:
            pytest.skip("no carryable room item available in starting room")

        loop.actions.execute.return_value = ActionResult.failure_result(
            "your hand stops short of it"
        )

        effects = {
            "fear": 1,
            "inventory_add": [target_item],
        }
        starting_fear = loop.player.fear
        starting_inventory = list(loop.player.get_inventory_names())

        with patch(
            "game.game_loop.interpret",
            return_value=_make_intent(effects=effects),
        ):
            loop._execute_action("take it")

        # Inventory delta was blocked.
        assert loop.player.get_inventory_names() == starting_inventory
        assert room.has_item(target_item), "item must still be in the room"
        # Fear delta still landed.
        assert loop.player.fear == starting_fear + 1

    def test_unknown_action_skips_inventory_add(self, loop):
        """`result is None` (registry returned no result) is the unknown-action
        path. Inventory deltas are skipped; fear/health still apply."""
        room = loop.map.current_room
        target_item = next(
            (name for name in loop.map.items if room.has_item(name)),
            None,
        )
        if target_item is None:
            pytest.skip("no carryable room item available in starting room")

        loop.actions.execute.return_value = None

        effects = {
            "fear": 1,
            "inventory_add": [target_item],
        }
        starting_fear = loop.player.fear
        starting_inventory = list(loop.player.get_inventory_names())

        with patch(
            "game.game_loop.interpret",
            return_value=_make_intent(action="unknown", effects=effects),
        ):
            loop._execute_action("do the strange thing")

        assert loop.player.get_inventory_names() == starting_inventory
        assert room.has_item(target_item)
        assert loop.player.fear == starting_fear + 1

    def test_successful_action_allows_inventory_add(self, loop):
        """Sanity check: when the action succeeds, inventory deltas still apply.
        This is the path the guard is NOT supposed to block."""
        room = loop.map.current_room
        target_item = next(
            (name for name in loop.map.items if room.has_item(name)),
            None,
        )
        if target_item is None:
            pytest.skip("no carryable room item available in starting room")

        loop.actions.execute.return_value = ActionResult.success_result("taken")

        with patch(
            "game.game_loop.interpret",
            return_value=_make_intent(effects={"inventory_add": [target_item]}),
        ):
            loop._execute_action("take it")

        assert target_item in loop.player.get_inventory_names()
        assert not room.has_item(target_item)
