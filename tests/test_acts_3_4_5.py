"""Tests for Act III, IV, V content."""

from unittest.mock import MagicMock

from game.actions.base import ActionContext
from game.actions.refuse import RefuseAction
from game.actions.use import UseAction
from game.item import Item
from game.map import Map


def _make_ctx_for_use(item_name: str, world_state, room_items: dict) -> ActionContext:
    ctx = MagicMock()
    ctx.args = {"item": item_name}
    ctx.player.get_item.return_value = None
    ctx.room.get_item.side_effect = lambda n: room_items.get(n.lower())
    ctx.world_state = world_state
    ctx.ai_reply = None
    return ctx


class TestActIIITells:
    def _prep(self):
        m = Map()
        m.world_state.first_morning = True
        m.world_state.enter_wrong_layer()
        # Jump straight to the wrong cabin for focused tests.
        m.current_location_id = "cabin_interior"
        m.current_room_id = "cabin_main"
        room = m.current_room
        items = {it.name.lower(): it for it in room.items}
        return m, items

    def test_window_logs_frost_wood_grain_in_wrong_layer(self):
        m, items = self._prep()
        ctx = _make_ctx_for_use("window", m.world_state, items)
        r = UseAction().execute(ctx)
        assert r.success is True
        assert m.world_state.wrongness.has("frost_wood_grain") is True

    def test_mug_logs_knuckles_birch_in_wrong_layer(self):
        m, items = self._prep()
        ctx = _make_ctx_for_use("mug", m.world_state, items)
        UseAction().execute(ctx)
        assert m.world_state.wrongness.has("knuckles_birch") is True

    def test_nika_logs_delayed_smile_in_wrong_layer(self):
        m, items = self._prep()
        ctx = _make_ctx_for_use("nika", m.world_state, items)
        UseAction().execute(ctx)
        assert m.world_state.wrongness.has("delayed_smile") is True

    def test_window_real_layer_does_not_log(self):
        m = Map()
        m.current_location_id = "cabin_interior"
        m.current_room_id = "cabin_main"
        room = m.current_room
        items = {it.name.lower(): it for it in room.items}
        ctx = _make_ctx_for_use("window", m.world_state, items)
        UseAction().execute(ctx)
        assert m.world_state.wrongness.has("frost_wood_grain") is False


class TestActIVCorrectionTurn:
    def test_entering_wrong_old_woods_triggers_recognition(self):
        m = Map()
        m.world_state.first_morning = True
        m.world_state.enter_wrong_layer()
        # Start in the wrong cabin (Act II ends with the teleport here).
        m.current_location_id = "cabin_interior"
        m.current_room_id = "cabin_main"
        # Walk the wrong path: cabin_main -> cabin_clearing (out) -> wood_track -> old_woods
        moved, _ = m.move("out")
        assert moved
        moved, _ = m.move("north")
        assert moved
        moved, _ = m.move("north")
        assert moved
        assert m.world_state.recognition is True
        assert m.world_state.wrongness.has("correction_turn") is True

    def test_real_layer_old_woods_does_not_trigger_recognition(self):
        m = Map()
        m.world_state.first_morning = True
        m.move("north")  # into clearing
        m.move("cabin")  # into cabin
        m.move("grounds")  # out to grounds
        m.move("north")  # wood_track
        m.move("north")  # old_woods
        assert m.world_state.recognition is False


class TestActVRefusal:
    def _ctx(self, world_state) -> ActionContext:
        ctx = MagicMock()
        ctx.args = {}
        ctx.world_state = world_state
        ctx.ai_reply = None
        return ctx

    def test_refuse_without_recognition_is_uncertain(self):
        m = Map()
        m.world_state.enter_wrong_layer()
        r = RefuseAction().execute(self._ctx(m.world_state))
        assert r.success is True
        assert "refuse_too_early" in r.events
        assert m.world_state.is_wrong_layer() is True

    def test_refuse_in_real_layer_lands_as_no_target(self):
        m = Map()
        m.world_state.recognition = True
        r = RefuseAction().execute(self._ctx(m.world_state))
        assert "refuse_no_target" in r.events

    def test_refuse_with_recognition_in_wrong_layer_exits_layer(self):
        m = Map()
        m.world_state.enter_wrong_layer()
        m.world_state.recognition = True
        r = RefuseAction().execute(self._ctx(m.world_state))
        assert r.success is True
        assert "refuse" in r.events
        assert "wrong_layer_exited" in r.events
        assert m.world_state.is_wrong_layer() is False
