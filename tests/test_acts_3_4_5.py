"""Tests for Act III, IV, V content."""

from unittest.mock import MagicMock

from game.actions.base import ActionContext
from game.actions.accept import AcceptAction
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
    def _prep(self, reunion_stage: str = "complete"):
        m = Map()
        m.world_state.first_morning = True
        m.world_state.enter_wrong_layer()
        # Tells only fire once the reunion has landed. Tests that care about
        # the tells themselves skip past the reunion scene by default.
        m.world_state.reunion_stage = reunion_stage  # type: ignore[assignment]
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

    def test_tells_do_not_fire_during_arrival_stage(self):
        """Before the reunion lands, sensory tells are dormant."""
        m, items = self._prep(reunion_stage="arrival")
        # Mug and window both pre-reunion; no anomalies logged.
        UseAction().execute(_make_ctx_for_use("mug", m.world_state, items))
        UseAction().execute(_make_ctx_for_use("window", m.world_state, items))
        assert m.world_state.wrongness.has("knuckles_birch") is False
        assert m.world_state.wrongness.has("frost_wood_grain") is False

    def test_tells_do_not_fire_during_seated_stage(self):
        m, items = self._prep(reunion_stage="seated")
        UseAction().execute(_make_ctx_for_use("window", m.world_state, items))
        assert m.world_state.wrongness.has("frost_wood_grain") is False


class TestActIIIReunion:
    """The scripted reunion scene with the false Nika in the wrong cabin."""

    def _prep(self):
        m = Map()
        m.world_state.enter_wrong_layer()
        m.current_location_id = "cabin_interior"
        m.current_room_id = "cabin_main"
        room = m.current_room
        items = {it.name.lower(): it for it in room.items}
        return m, items

    def test_entering_wrong_layer_sets_reunion_to_arrival(self):
        m = Map()
        m.world_state.enter_wrong_layer()
        assert m.world_state.reunion_stage == "arrival"

    def test_use_nika_at_arrival_advances_to_seated(self):
        m, items = self._prep()
        r = UseAction().execute(_make_ctx_for_use("nika", m.world_state, items))
        assert r.success is True
        assert "reunion_seated" in r.events
        assert m.world_state.reunion_stage == "seated"
        # No wrongness logged yet.
        assert m.world_state.wrongness.has("delayed_smile") is False

    def test_use_mug_at_arrival_does_not_advance(self):
        m, items = self._prep()
        r = UseAction().execute(_make_ctx_for_use("mug", m.world_state, items))
        assert m.world_state.reunion_stage == "arrival"
        assert "use_mug_pre_seated" in r.events

    def test_use_mug_at_seated_completes_reunion(self):
        m, items = self._prep()
        m.world_state.reunion_stage = "seated"
        r = UseAction().execute(_make_ctx_for_use("mug", m.world_state, items))
        assert "reunion_complete" in r.events
        assert m.world_state.reunion_stage == "complete"
        # This is the emotional beat, not a wrongness tell.
        assert m.world_state.wrongness.has("knuckles_birch") is False

    def test_use_nika_at_seated_is_a_wait(self):
        m, items = self._prep()
        m.world_state.reunion_stage = "seated"
        r = UseAction().execute(_make_ctx_for_use("nika", m.world_state, items))
        assert m.world_state.reunion_stage == "seated"
        assert "use_nika_seated" in r.events

    def test_use_mug_after_complete_logs_tell(self):
        m, items = self._prep()
        m.world_state.reunion_stage = "complete"
        UseAction().execute(_make_ctx_for_use("mug", m.world_state, items))
        assert m.world_state.wrongness.has("knuckles_birch") is True

    def test_refusal_resets_reunion_stage(self):
        """Exiting the wrong layer via refusal clears the reunion."""
        m = Map()
        m.world_state.enter_wrong_layer()
        m.world_state.reunion_stage = "complete"
        m.world_state.exit_wrong_layer()
        assert m.world_state.reunion_stage == "none"


class TestActIIIWrongOutside:
    """The pivot beat: stepping out of the wrong cabin for the first time."""

    def _prep(self, reunion_stage: str = "complete"):
        m = Map()
        m.world_state.enter_wrong_layer()
        m.world_state.reunion_stage = reunion_stage  # type: ignore[assignment]
        m.current_location_id = "cabin_interior"
        m.current_room_id = "cabin_main"
        return m

    def test_cannot_leave_wrong_cabin_before_reunion_complete(self):
        m = self._prep(reunion_stage="arrival")
        moved, msg = m.move("out")
        assert moved is False
        assert "sit down" in msg.lower() or "can't go back" in msg.lower()
        # Still in the wrong cabin.
        assert m.current_room_id == "cabin_main"

    def test_cannot_leave_wrong_cabin_when_seated(self):
        m = self._prep(reunion_stage="seated")
        moved, _ = m.move("out")
        assert moved is False

    def test_can_leave_wrong_cabin_after_reunion_complete(self):
        m = self._prep(reunion_stage="complete")
        moved, msg = m.move("out")
        assert moved is True
        assert m.current_room_id == "cabin_clearing"
        # First step out fires the wrong-outside beat.
        assert "this isn't where i drove to" in msg.lower()
        assert m.world_state.wrong_outside_seen is True

    def test_wrong_outside_beat_fires_only_once(self):
        m = self._prep(reunion_stage="complete")
        _, first_msg = m.move("out")
        _, _ = m.move("cabin")  # back inside
        _, second_msg = m.move("out")
        assert "this isn't where i drove to" in first_msg.lower()
        assert "this isn't where i drove to" not in second_msg.lower()

    def test_refusal_resets_wrong_outside_seen(self):
        m = self._prep(reunion_stage="complete")
        m.move("out")
        assert m.world_state.wrong_outside_seen is True
        m.world_state.exit_wrong_layer()
        assert m.world_state.wrong_outside_seen is False


class TestActIVCorrectionTurn:
    def test_entering_wrong_old_woods_triggers_recognition(self):
        m = Map()
        m.world_state.first_morning = True
        m.world_state.enter_wrong_layer()
        # Reunion must have landed before Elli can leave the wrong cabin.
        m.world_state.reunion_stage = "complete"
        # Start in the wrong cabin (Act II ends with the teleport here).
        m.current_location_id = "cabin_interior"
        m.current_room_id = "cabin_main"
        # Walk the wrong path: cabin_main -> cabin_clearing (out) -> wood_track -> old_woods
        moved, _ = m.move("out")
        assert moved
        moved, _ = m.move("north")
        assert moved
        moved, msg = m.move("north")
        assert moved
        # The correction-turn now lands as a held beat, not a silent flag flip.
        assert "correction" in msg.lower() or "turn was wrong" in msg.lower()
        assert m.world_state.recognition is True
        assert m.world_state.wrongness.has("correction_turn") is True

    def test_correction_turn_fires_only_once(self):
        m = Map()
        m.world_state.first_morning = True
        m.world_state.enter_wrong_layer()
        m.world_state.reunion_stage = "complete"
        m.current_location_id = "cabin_interior"
        m.current_room_id = "cabin_main"
        m.move("out")
        m.move("north")
        _, first_msg = m.move("north")
        # Walk back and re-enter old woods; beat should not re-fire.
        m.move("south")
        _, second_msg = m.move("north")
        assert "turn was wrong" in first_msg.lower()
        assert "turn was wrong" not in second_msg.lower()

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
    def _ctx(self, map_: Map) -> ActionContext:
        ctx = MagicMock()
        ctx.args = {}
        ctx.map = map_
        ctx.world_state = map_.world_state
        ctx.ai_reply = None
        return ctx

    @staticmethod
    def _move_to_threshold(map_: Map) -> None:
        map_.current_location_id = "cabin_grounds"
        map_.current_room_id = "cabin_clearing"

    @staticmethod
    def _fill_wrongness(world_state) -> None:
        """Populate enough anomalies for the refusal threshold (3) to be met.

        Refusal now requires both recognition *and* accumulated tells.
        """
        world_state.wrongness.add("fox_tracks", "")
        world_state.wrongness.add("hare", "")
        world_state.wrongness.add("correction_turn", "")

    def test_refuse_without_recognition_is_uncertain(self):
        m = Map()
        m.world_state.enter_wrong_layer()
        self._fill_wrongness(m.world_state)
        self._move_to_threshold(m)
        r = RefuseAction().execute(self._ctx(m))
        assert r.success is True
        assert "refuse_too_early" in r.events
        assert m.world_state.is_wrong_layer() is True

    def test_refuse_without_threshold_is_uncertain(self):
        m = Map()
        m.world_state.enter_wrong_layer()
        m.world_state.recognition = True
        # No wrongness logged.
        self._move_to_threshold(m)
        r = RefuseAction().execute(self._ctx(m))
        assert "refuse_too_early" in r.events
        assert m.world_state.is_wrong_layer() is True

    def test_refuse_in_real_layer_lands_as_no_target(self):
        m = Map()
        m.world_state.recognition = True
        self._fill_wrongness(m.world_state)
        self._move_to_threshold(m)
        r = RefuseAction().execute(self._ctx(m))
        assert "refuse_no_target" in r.events

    def test_refuse_away_from_threshold_is_not_available(self):
        m = Map()
        m.world_state.enter_wrong_layer()
        m.world_state.recognition = True
        self._fill_wrongness(m.world_state)
        m.current_location_id = "cabin_grounds"
        m.current_room_id = "old_woods"
        r = RefuseAction().execute(self._ctx(m))
        assert "refuse_not_at_threshold" in r.events
        assert m.world_state.is_wrong_layer() is True

    def test_refuse_with_recognition_in_wrong_layer_exits_layer(self):
        m = Map()
        m.world_state.enter_wrong_layer()
        m.world_state.recognition = True
        self._fill_wrongness(m.world_state)
        self._move_to_threshold(m)
        r = RefuseAction().execute(self._ctx(m))
        assert r.success is True
        assert "refuse" in r.events
        assert "wrong_layer_exited" in r.events
        assert m.world_state.is_wrong_layer() is False
        assert m.world_state.ending == "refused"
        assert "the cabin waits in the next clearing" in r.feedback.lower()


class TestActVAcceptance:
    def _ctx(self, map_: Map) -> ActionContext:
        ctx = MagicMock()
        ctx.args = {}
        ctx.map = map_
        ctx.world_state = map_.world_state
        ctx.ai_reply = None
        return ctx

    @staticmethod
    def _move_to_threshold(map_: Map) -> None:
        map_.current_location_id = "cabin_grounds"
        map_.current_room_id = "cabin_clearing"

    @staticmethod
    def _fill_wrongness(world_state) -> None:
        world_state.wrongness.add("fox_tracks", "")
        world_state.wrongness.add("hare", "")
        world_state.wrongness.add("correction_turn", "")

    def test_accept_without_recognition_is_uncertain(self):
        m = Map()
        m.world_state.enter_wrong_layer()
        self._fill_wrongness(m.world_state)
        self._move_to_threshold(m)
        r = AcceptAction().execute(self._ctx(m))
        assert r.success is True
        assert "accept_too_early" in r.events
        assert m.world_state.is_wrong_layer() is True
        assert m.world_state.ending == "none"

    def test_accept_in_real_layer_lands_as_no_target(self):
        m = Map()
        m.world_state.recognition = True
        self._fill_wrongness(m.world_state)
        self._move_to_threshold(m)
        r = AcceptAction().execute(self._ctx(m))
        assert "accept_no_target" in r.events
        assert m.world_state.ending == "none"

    def test_accept_away_from_threshold_is_not_available(self):
        m = Map()
        m.world_state.enter_wrong_layer()
        m.world_state.recognition = True
        self._fill_wrongness(m.world_state)
        m.current_location_id = "cabin_grounds"
        m.current_room_id = "old_woods"
        r = AcceptAction().execute(self._ctx(m))
        assert "accept_not_at_threshold" in r.events
        assert m.world_state.ending == "none"

    def test_accept_with_recognition_in_wrong_layer_exits_layer(self):
        m = Map()
        m.world_state.enter_wrong_layer()
        m.world_state.recognition = True
        self._fill_wrongness(m.world_state)
        self._move_to_threshold(m)
        r = AcceptAction().execute(self._ctx(m))
        assert r.success is True
        assert "accept" in r.events
        assert "wrong_layer_exited" in r.events
        assert m.world_state.is_wrong_layer() is False
        assert m.world_state.ending == "accepted"
