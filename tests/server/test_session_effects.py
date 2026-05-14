"""Tests for WebGameSession effect ordering and skip_inventory guard.

WebGameSession is the live web-runtime orchestrator. These tests pin the
same safety contract that GameEngine enforces in the terminal runtime:

1. Actions execute BEFORE AI-proposed effects apply (so action logic sees
   the player's true state, not an AI-mutated one).
2. AI-proposed inventory deltas are skipped when the action is unknown
   (``result is None``) or failed (``result.success is False``), so a
   refused or unrecognised intent cannot let the model pickpocket the
   room. Fear/health deltas still land.
"""

from unittest.mock import MagicMock, patch

import pytest

from game.actions.base import ActionResult
from game.ai_interpreter import Intent, clear_response_cache
from server.session import WebGameSession


@pytest.fixture(autouse=True)
def _clear_ai_cache():
    clear_response_cache()
    yield
    clear_response_cache()


def _make_intent(action: str = "take", effects=None, reply: str = "ok") -> Intent:
    return Intent(
        action=action,
        args={"item": "matches"},
        confidence=0.9,
        reply=reply,
        effects=effects or {},
    )


@pytest.fixture
def session():
    """A web session that has finished the intro keypress, with the
    action registry stubbed so tests can drive success/fail/unknown."""
    s = WebGameSession()
    s.handle_input("")  # dismiss intro
    s.action_registry = MagicMock()
    return s


class TestExecuteOrdering:
    def test_action_executes_before_effects_apply(self, session):
        """The action must see the player's pre-effect state, not a state
        already mutated by AI-proposed deltas."""
        call_order = []
        session.player.fear = 0

        def execute_side_effect(*_args, **_kwargs):
            # When the action runs, the AI's fear delta MUST NOT have applied yet.
            call_order.append(("action", session.player.fear))
            return ActionResult.success_result("you do the thing")

        session.action_registry.execute.side_effect = execute_side_effect

        original_apply = session._apply_effects

        def apply_spy(intent, skip_inventory=False):
            call_order.append(("effects", session.player.fear))
            return original_apply(intent, skip_inventory=skip_inventory)

        session._apply_effects = apply_spy  # type: ignore[assignment]

        with patch(
            "server.session.interpret",
            return_value=_make_intent(effects={"fear": 2}),
        ):
            session.handle_input("take matches")

        assert call_order[0][0] == "action", "action must run before effects"
        assert call_order[0][1] == 0, "action saw pre-effect fear"
        assert call_order[1][0] == "effects"
        # After effects, fear has been bumped by the (clamped) +2 delta.
        assert session.player.fear == 2


class TestSkipInventoryGuard:
    def test_failed_action_skips_inventory_add(self, session):
        """A failed action must not let an AI-proposed `inventory_add` land."""
        session.action_registry.execute.return_value = ActionResult.failure_result(
            feedback="the door does not give"
        )

        # Pick a room item the AI might propose to grab.
        room = session.map.current_room
        room_items_before = list(room.items)
        assert len(room_items_before) > 0, "need at least one room item to test guard"
        target_name = room_items_before[0].name

        starting_inventory = list(session.player.inventory)

        with patch(
            "server.session.interpret",
            return_value=_make_intent(
                effects={"inventory_add": [target_name]},
            ),
        ):
            session.handle_input("force the door")

        # Inventory unchanged: failed action does not let the AI pickpocket.
        assert list(session.player.inventory) == starting_inventory
        # Item still in the room.
        assert any(it.name == target_name for it in room.items)

    def test_unknown_action_skips_inventory_add(self, session):
        """An unknown action (`result is None`) must skip inventory deltas."""
        session.action_registry.execute.return_value = None

        room = session.map.current_room
        assert len(room.items) > 0
        target_name = room.items[0].name
        starting_inventory = list(session.player.inventory)

        with patch(
            "server.session.interpret",
            return_value=_make_intent(
                action="not_a_real_action",
                effects={"inventory_add": [target_name]},
                reply="you start, then think better of it",
            ),
        ):
            session.handle_input("weave a spell of opening")

        assert list(session.player.inventory) == starting_inventory
        assert any(it.name == target_name for it in room.items)

    def test_failed_action_still_applies_fear(self, session):
        """Skip-inventory must NOT block fear/health deltas — failure can
        still feel."""
        session.action_registry.execute.return_value = ActionResult.failure_result(
            feedback="you flinch"
        )
        session.player.fear = 0

        with patch(
            "server.session.interpret",
            return_value=_make_intent(effects={"fear": 2}),
        ):
            session.handle_input("look at it directly")

        assert session.player.fear == 2

    def test_successful_action_applies_inventory(self, session):
        """Sanity: successful action lets a valid inventory_add land."""
        session.action_registry.execute.return_value = ActionResult.success_result(
            feedback="you take it"
        )
        room = session.map.current_room
        assert len(room.items) > 0
        target_name = room.items[0].name
        starting_count = len(session.player.inventory)

        with patch(
            "server.session.interpret",
            return_value=_make_intent(
                effects={"inventory_add": [target_name]},
            ),
        ):
            session.handle_input(f"take {target_name}")

        assert len(session.player.inventory) == starting_count + 1
        assert any(it.name == target_name for it in session.player.inventory)

    def test_failed_action_skips_inventory_remove(self, session):
        """A failed action must not let an AI-proposed `inventory_remove`
        land — symmetric with inventory_add."""
        # Seed the player's inventory with a real item drawn from the map.
        seeded = next(iter(session.map.items.values()))
        session.player.add_item(seeded)
        assert session.player.has_item(seeded.name)

        session.action_registry.execute.return_value = ActionResult.failure_result(
            feedback="the latch resists"
        )

        with patch(
            "server.session.interpret",
            return_value=_make_intent(
                effects={"inventory_remove": [seeded.name]},
            ),
        ):
            session.handle_input("force the latch")

        # Item still held: failed action does not let the AI drop it.
        assert session.player.has_item(seeded.name)

    def test_unknown_action_skips_inventory_remove(self, session):
        """An unknown action (`result is None`) must also skip
        `inventory_remove`."""
        seeded = next(iter(session.map.items.values()))
        session.player.add_item(seeded)
        assert session.player.has_item(seeded.name)

        session.action_registry.execute.return_value = None

        with patch(
            "server.session.interpret",
            return_value=_make_intent(
                action="not_a_real_action",
                effects={"inventory_remove": [seeded.name]},
                reply="you start, then think better of it",
            ),
        ):
            session.handle_input("speak the unsaying")

        assert session.player.has_item(seeded.name)

    def test_successful_action_applies_inventory_remove(self, session):
        """Sanity: successful action lets a valid inventory_remove land."""
        seeded = next(iter(session.map.items.values()))
        session.player.add_item(seeded)
        assert session.player.has_item(seeded.name)

        session.action_registry.execute.return_value = ActionResult.success_result(
            feedback="you let it fall"
        )

        with patch(
            "server.session.interpret",
            return_value=_make_intent(
                effects={"inventory_remove": [seeded.name]},
            ),
        ):
            session.handle_input(f"drop {seeded.name}")

        assert not session.player.has_item(seeded.name)
