"""Tests for Acts III, IV, V content: the false-cabin night, the two endings,
the walk out, and the coda (rewritten canon, issue #141)."""

from unittest.mock import MagicMock

from game.actions.base import ActionContext
from game.actions.accept import AcceptAction
from game.actions.refuse import RefuseAction
from game.actions.use import UseAction
from game.actions.wait import WaitAction
from game.ending import ending_line_for
from game.map import Map
from game.story import AnomalyID
from game.story.night import NIGHT_SEAM_THRESHOLD


def _wrong_cabin_map(reunion_stage: str = "arrival") -> Map:
    """A map dropped straight into the wrong cabin at the given stage."""
    m = Map()
    m.world_state.first_morning = True
    m.world_state.enter_wrong_layer()
    m.world_state.reunion_stage = reunion_stage  # type: ignore[assignment]
    m.current_location_id = "cabin_interior"
    m.current_room_id = "cabin_main"
    return m


def _ctx_for_use(m: Map, item_name: str) -> ActionContext:
    ctx = MagicMock()
    ctx.args = {"item": item_name}
    ctx.player.get_item.return_value = None
    room = m.current_room
    items = {it.name.lower(): it for it in room.items}
    ctx.room.get_item.side_effect = lambda n: items.get(n.lower())
    ctx.map = m
    ctx.world_state = m.world_state
    ctx.ai_reply = None
    return ctx


def _ctx_plain(m: Map) -> ActionContext:
    ctx = MagicMock()
    ctx.args = {}
    ctx.map = m
    ctx.world_state = m.world_state
    ctx.ai_reply = None
    return ctx


def _gather_night_seams(m: Map, n: int) -> None:
    """Log night seams directly, below or up to the threshold.

    Deliberately excludes the observation-triggered seams (breathing, black
    boards) so tests can cross the threshold with a live look/listen.
    """
    seams = [
        AnomalyID.MEMORY_ALOUD,
        AnomalyID.PHONE_DARK,
        AnomalyID.WRONG_TINS,
        AnomalyID.MUG_IMPOSSIBLE,
    ]
    for anomaly in seams[:n]:
        m.world_state.wrongness.add(anomaly.value, "")


class TestActIIITells:
    """The evening tells, gated behind the completed reunion."""

    def test_window_logs_frost_wood_grain_in_wrong_layer(self):
        m = _wrong_cabin_map("complete")
        r = UseAction().execute(_ctx_for_use(m, "window"))
        assert r.success is True
        assert m.world_state.wrongness.has("frost_wood_grain") is True

    def test_mug_logs_knuckles_birch_at_complete(self):
        m = _wrong_cabin_map("complete")
        UseAction().execute(_ctx_for_use(m, "mug"))
        assert m.world_state.wrongness.has("knuckles_birch") is True

    def test_nika_logs_delayed_smile_at_complete(self):
        m = _wrong_cabin_map("complete")
        UseAction().execute(_ctx_for_use(m, "nika"))
        assert m.world_state.wrongness.has("delayed_smile") is True

    def test_window_real_layer_does_not_log(self):
        m = Map()
        m.current_location_id = "cabin_interior"
        m.current_room_id = "cabin_main"
        UseAction().execute(_ctx_for_use(m, "window"))
        assert m.world_state.wrongness.has("frost_wood_grain") is False

    def test_tells_do_not_fire_before_complete(self):
        for stage in ("arrival", "tended", "seated"):
            m = _wrong_cabin_map(stage)
            UseAction().execute(_ctx_for_use(m, "window"))
            assert m.world_state.wrongness.has("frost_wood_grain") is False


class TestActIIIReunion:
    """The scripted reunion beats: arrival -> tended -> seated -> complete."""

    def test_entering_wrong_layer_sets_reunion_to_arrival(self):
        m = Map()
        m.world_state.enter_wrong_layer()
        assert m.world_state.reunion_stage == "arrival"

    def test_use_nika_at_arrival_advances_to_tended(self):
        m = _wrong_cabin_map("arrival")
        r = UseAction().execute(_ctx_for_use(m, "nika"))
        assert "reunion_tended" in r.events
        assert m.world_state.reunion_stage == "tended"
        assert "you called me" in r.feedback.lower()

    def test_use_nika_at_tended_advances_to_seated(self):
        m = _wrong_cabin_map("tended")
        r = UseAction().execute(_ctx_for_use(m, "nika"))
        assert "reunion_seated" in r.events
        assert m.world_state.reunion_stage == "seated"
        assert "first light" in r.feedback.lower()

    def test_use_mug_before_seated_does_not_advance(self):
        for stage in ("arrival", "tended"):
            m = _wrong_cabin_map(stage)
            r = UseAction().execute(_ctx_for_use(m, "mug"))
            assert m.world_state.reunion_stage == stage
            assert "use_mug_pre_seated" in r.events

    def test_use_mug_at_seated_completes_reunion(self):
        m = _wrong_cabin_map("seated")
        r = UseAction().execute(_ctx_for_use(m, "mug"))
        assert "reunion_complete" in r.events
        assert m.world_state.reunion_stage == "complete"
        # The blue mug beat: the chip, the impossible rightness.
        assert "blue enamel" in r.feedback.lower()
        # The emotional beat, not a wrongness tell.
        assert m.world_state.wrongness.has("knuckles_birch") is False

    def test_exit_wrong_layer_resets_reunion_stage(self):
        m = _wrong_cabin_map("complete")
        m.world_state.exit_wrong_layer()
        assert m.world_state.reunion_stage == "none"


class TestActIIIConsentDoor:
    """The consent beat: she opens the door, sees the wrong outside, and
    chooses the warm room."""

    def test_cannot_leave_wrong_cabin_before_reunion_complete(self):
        for stage in ("arrival", "tended", "seated"):
            m = _wrong_cabin_map(stage)
            moved, msg = m.move("out")
            assert moved is False
            assert "sit down" in msg.lower()
            assert m.current_room_id == "cabin_main"

    def test_first_out_after_complete_fires_consent_beat_without_moving(self):
        m = _wrong_cabin_map("complete")
        moved, msg = m.move("out")
        assert moved is False
        assert m.current_room_id == "cabin_main"
        assert "come inside. i'm here now" in msg.lower()
        assert "you let the door close" in msg.lower()
        assert m.world_state.consent_given is True
        assert m.world_state.reunion_stage == "consented"

    def test_second_out_is_held_by_the_night(self):
        m = _wrong_cabin_map("complete")
        m.move("out")
        moved, msg = m.move("out")
        assert moved is False
        assert "come inside" not in msg.lower()
        assert "first light" in msg.lower()

    def test_exit_wrong_layer_clears_consent(self):
        m = _wrong_cabin_map("complete")
        m.move("out")
        m.world_state.exit_wrong_layer()
        assert m.world_state.consent_given is False

    def test_consent_beat_cannot_regress_a_later_stage(self):
        """A malformed save deeper into the night with consent_given missing
        must be held by the night, not walked back to the consent beat."""
        for stage in ("consented", "bedded", "night", "dawn"):
            m = _wrong_cabin_map(stage)
            assert m.world_state.consent_given is False  # malformed on purpose
            moved, msg = m.move("out")
            assert moved is False
            assert m.world_state.reunion_stage == stage
            assert "you let the door close" not in msg.lower()


class TestActIVNight:
    """The night: the bed beat, the gathered seams, the knowing."""

    def test_mattress_at_consented_beds_down_and_logs_memory_aloud(self):
        m = _wrong_cabin_map("consented")
        r = UseAction().execute(_ctx_for_use(m, "mattress"))
        assert "reunion_bedded" in r.events
        assert m.world_state.reunion_stage == "bedded"
        assert m.world_state.wrongness.has(AnomalyID.MEMORY_ALOUD.value) is True
        assert "like when we were kids" in r.feedback.lower()

    def test_listen_at_night_logs_breathing(self):
        m = _wrong_cabin_map("bedded")
        text = m.observe_current_room("listen")
        assert "the same breath" in text.lower()
        assert m.world_state.wrongness.has(AnomalyID.BREATHING_TIDE.value) is True

    def test_look_at_night_logs_black_boards(self):
        m = _wrong_cabin_map("bedded")
        text = m.observe_current_room("look")
        assert "matt black" in text.lower()
        assert m.world_state.wrongness.has(AnomalyID.BLACK_BOARDS.value) is True

    def test_phone_at_night_logs_phone_dark(self):
        m = _wrong_cabin_map("bedded")
        r = UseAction().execute(_ctx_for_use(m, "phone"))
        assert m.world_state.wrongness.has(AnomalyID.PHONE_DARK.value) is True
        assert "dark all through" in r.feedback.lower()

    def test_tins_at_night_log_wrong_tins(self):
        m = _wrong_cabin_map("bedded")
        r = UseAction().execute(_ctx_for_use(m, "tins"))
        assert m.world_state.wrongness.has(AnomalyID.WRONG_TINS.value) is True

    def test_mug_at_night_logs_mug_impossible(self):
        m = _wrong_cabin_map("bedded")
        r = UseAction().execute(_ctx_for_use(m, "mug"))
        assert m.world_state.wrongness.has(AnomalyID.MUG_IMPOSSIBLE.value) is True
        assert "hook" in r.feedback.lower()

    def test_night_seams_do_not_fire_before_bedded(self):
        m = _wrong_cabin_map("consented")
        assert m.observe_current_room("listen") == ""
        UseAction().execute(_ctx_for_use(m, "phone"))
        assert m.world_state.wrongness.has(AnomalyID.PHONE_DARK.value) is False

    def test_recognition_fires_at_threshold_with_scene(self):
        m = _wrong_cabin_map("bedded")
        _gather_night_seams(m, NIGHT_SEAM_THRESHOLD - 1)
        assert m.world_state.recognition is False
        # The threshold-crossing observation carries the scene.
        text = m.observe_current_room("listen")
        assert m.world_state.recognition is True
        assert m.world_state.reunion_stage == "night"
        assert "let the knowing finish" in text.lower()
        # The phone-call lie joins the log as part of the knowing.
        assert m.world_state.wrongness.has(AnomalyID.NO_CALL.value) is True

    def test_recognition_does_not_fire_below_threshold(self):
        m = _wrong_cabin_map("bedded")
        _gather_night_seams(m, NIGHT_SEAM_THRESHOLD - 2)
        text = m.observe_current_room("look")
        assert m.world_state.recognition is False
        assert "let the knowing finish" not in text.lower()

    def test_recognition_scene_fires_only_once(self):
        m = _wrong_cabin_map("bedded")
        _gather_night_seams(m, NIGHT_SEAM_THRESHOLD - 1)
        first = m.observe_current_room("listen")
        second = m.observe_current_room("look")
        assert "let the knowing finish" in first.lower()
        assert "let the knowing finish" not in second.lower()

    def test_bed_beat_finishes_the_knowing_if_seams_already_gathered(self):
        """A pre-loaded log (dev seed, replayed save) must not strand
        recognition: the mattress beat itself runs the threshold check."""
        m = _wrong_cabin_map("consented")
        for anomaly in (
            AnomalyID.PHONE_DARK,
            AnomalyID.WRONG_TINS,
            AnomalyID.MUG_IMPOSSIBLE,
        ):
            m.world_state.wrongness.add(anomaly.value, "")
        r = UseAction().execute(_ctx_for_use(m, "mattress"))
        assert m.world_state.recognition is True
        assert m.world_state.reunion_stage == "night"
        assert "let the knowing finish" in r.feedback.lower()


class TestActVDawn:
    """The dawn offer and the two endings."""

    def _night_map(self, recognised: bool = True) -> Map:
        m = _wrong_cabin_map("bedded")
        _gather_night_seams(m, NIGHT_SEAM_THRESHOLD - 1)
        if recognised:
            m.observe_current_room("listen")  # crosses the threshold
            assert m.world_state.recognition is True
        return m

    def test_wait_at_night_brings_dawn(self):
        m = self._night_map()
        r = WaitAction().execute(_ctx_plain(m))
        assert "dawn" in r.events
        assert m.world_state.reunion_stage == "dawn"
        assert "drink up" in r.feedback.lower()

    def test_wait_before_recognition_does_not_bring_dawn(self):
        m = _wrong_cabin_map("bedded")
        r = WaitAction().execute(_ctx_plain(m))
        assert m.world_state.reunion_stage == "bedded"
        assert "dawn" not in r.events

    def test_wait_without_seams_does_not_bring_dawn(self):
        """A malformed save (recognition without the gathered seams) must not
        reach an offer it would then be unable to answer: the dawn gate
        matches the refuse/accept dual gate."""
        m = _wrong_cabin_map("night")
        m.world_state.recognition = True  # seams missing
        r = WaitAction().execute(_ctx_plain(m))
        assert m.world_state.reunion_stage == "night"
        assert "dawn" not in r.events

    def _dawn_map(self) -> Map:
        m = self._night_map()
        WaitAction().execute(_ctx_plain(m))
        assert m.world_state.reunion_stage == "dawn"
        return m

    def test_refuse_without_recognition_is_uncertain(self):
        m = _wrong_cabin_map("bedded")
        r = RefuseAction().execute(_ctx_plain(m))
        assert "refuse_too_early" in r.events
        assert m.world_state.ending == "none"

    def test_refuse_in_real_layer_lands_as_no_target(self):
        m = Map()
        m.world_state.recognition = True
        _gather_night_seams(m, NIGHT_SEAM_THRESHOLD)
        r = RefuseAction().execute(_ctx_plain(m))
        assert "refuse_no_target" in r.events

    def test_refuse_before_dawn_is_not_available(self):
        m = self._night_map()
        r = RefuseAction().execute(_ctx_plain(m))
        assert "refuse_not_at_threshold" in r.events
        assert m.world_state.ending == "none"

    def test_refuse_at_dawn_lands_the_escape(self):
        m = self._dawn_map()
        r = RefuseAction().execute(_ctx_plain(m))
        assert "ending_escaped" in r.events
        assert m.world_state.ending == "escaped"
        # She has not left yet: the walk out happens on foot.
        assert m.world_state.is_wrong_layer() is True
        assert "and you are still not her" in r.feedback.lower()
        assert "it's lying out there" in r.feedback.lower()

    def test_drinking_the_mug_at_dawn_is_the_stayed_ending(self):
        m = self._dawn_map()
        r = UseAction().execute(_ctx_for_use(m, "mug"))
        assert "ending_stayed" in r.events
        assert m.world_state.ending == "stayed"
        assert ending_line_for(m.world_state) == "You are home."

    def test_accept_before_dawn_is_not_available(self):
        m = self._night_map()
        r = AcceptAction().execute(_ctx_plain(m))
        assert "accept_not_at_threshold" in r.events
        assert m.world_state.ending == "none"

    def test_accept_after_refusal_does_not_reopen(self):
        m = self._dawn_map()
        RefuseAction().execute(_ctx_plain(m))
        r = AcceptAction().execute(_ctx_plain(m))
        assert "accept_after_refusal" in r.events
        assert m.world_state.ending == "escaped"


class TestWalkOutAndCoda:
    """The walk out through the indifferent woods, and the coda."""

    def _escaped_map(self) -> Map:
        m = _wrong_cabin_map("bedded")
        _gather_night_seams(m, NIGHT_SEAM_THRESHOLD - 1)
        m.observe_current_room("listen")
        WaitAction().execute(_ctx_plain(m))
        RefuseAction().execute(_ctx_plain(m))
        assert m.world_state.ending == "escaped"
        return m

    def test_walk_out_route_exits_the_layer_and_starts_the_coda(self):
        m = self._escaped_map()
        moved, msg = m.move("out")
        assert moved is True
        assert m.current_room_id == "cabin_clearing"
        assert "without any interest" in msg.lower()

        moved, msg = m.move("south")
        assert moved is True
        assert m.current_room_id == "wood_track"
        assert "mattering to nothing" in msg.lower() or "worst hour" in msg.lower()

        moved, msg = m.move("south")
        assert moved is True
        assert m.current_room_id == "cabin_grounds_main"
        assert m.world_state.is_wrong_layer() is False
        assert m.world_state.coda_stage == "home"
        assert "boot prints" in msg.lower()

    def _coda_map(self) -> Map:
        m = self._escaped_map()
        m.move("out")
        m.move("south")
        m.move("south")
        m.current_location_id = "cabin_interior"
        m.current_room_id = "cabin_main"
        return m

    def test_phone_at_home_makes_the_call(self):
        m = self._coda_map()
        r = UseAction().execute(_ctx_for_use(m, "phone"))
        assert "coda_call" in r.events
        assert m.world_state.coda_stage == "called"
        assert "drive slow" in r.feedback.lower()

    def test_wait_after_the_call_starts_the_scraping(self):
        m = self._coda_map()
        UseAction().execute(_ctx_for_use(m, "phone"))
        r = WaitAction().execute(_ctx_plain(m))
        assert "coda_scraping" in r.events
        assert m.world_state.coda_stage == "scraping"
        assert "scraping" in r.feedback.lower()

    def test_wait_through_the_scraping_ends_the_story(self):
        m = self._coda_map()
        UseAction().execute(_ctx_for_use(m, "phone"))
        WaitAction().execute(_ctx_plain(m))
        r = WaitAction().execute(_ctx_plain(m))
        assert "ending_complete" in r.events
        assert m.world_state.coda_stage == "end"
        assert "then it stops" in r.feedback.lower()
        assert ending_line_for(m.world_state) == "You wait."

    def test_story_is_not_over_before_the_final_wait(self):
        m = self._coda_map()
        assert ending_line_for(m.world_state) is None
        UseAction().execute(_ctx_for_use(m, "phone"))
        WaitAction().execute(_ctx_plain(m))
        assert ending_line_for(m.world_state) is None
