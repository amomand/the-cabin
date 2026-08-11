"""Tests for Acts III, IV, V content: the false-cabin night, the two endings,
the walk out, and the coda (rewritten canon, issue #141)."""

from unittest.mock import MagicMock

import pytest

from game.actions.base import ActionContext
from game.actions.accept import AcceptAction
from game.actions.refuse import RefuseAction
from game.actions.use import UseAction
from game.actions.wait import WaitAction
from game.ending import ending_line_for
from game.map import Map
from game.player import Player
from game.room import DENIAL_INDOORS, DENIAL_OUTDOORS
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


def _ctx_for_use(m: Map, item_name: str, player=None) -> ActionContext:
    ctx = MagicMock()
    ctx.args = {"item": item_name}
    # A real Player, not a mock: these beats move fear, and a MagicMock stat
    # can be neither bounded nor asserted on.
    ctx.player = Player() if player is None else player
    room = m.current_room
    items = {it.name.lower(): it for it in room.items}
    ctx.room.get_item.side_effect = lambda n: items.get(n.lower())
    ctx.map = m
    ctx.world_state = m.world_state
    ctx.ai_reply = None
    return ctx


def _ctx_plain(m: Map, player=None) -> ActionContext:
    ctx = MagicMock()
    ctx.args = {}
    ctx.player = Player() if player is None else player
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
        assert "Frost again, weather on glass" in r.feedback

    def test_mug_logs_knuckles_birch_at_complete(self):
        m = _wrong_cabin_map("complete")
        r = UseAction().execute(_ctx_for_use(m, "mug"))
        assert m.world_state.wrongness.has("knuckles_birch") is True
        assert "white scar at the base of the thumb" in r.feedback
        assert "skin is bark" not in r.feedback

    def test_nika_logs_delayed_smile_at_complete(self):
        m = _wrong_cabin_map("complete")
        r = UseAction().execute(_ctx_for_use(m, "nika"))
        assert m.world_state.wrongness.has("delayed_smile") is True
        assert "mouth has already made the smile" in r.feedback

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

    def test_evening_tells_do_not_first_fire_after_consent(self):
        m = _wrong_cabin_map("consented")

        UseAction().execute(_ctx_for_use(m, "window"))
        UseAction().execute(_ctx_for_use(m, "mug"))
        UseAction().execute(_ctx_for_use(m, "nika"))

        assert m.world_state.wrongness.count() == 0

    def test_later_fixture_keeps_evening_tells_in_story_order(self):
        m = _wrong_cabin_map("complete")

        r = UseAction().execute(_ctx_for_use(m, "nika"))

        frost = r.feedback.index("Frost builds at the inside corners")
        hand = r.feedback.index("the hand is wrong")
        smile = r.feedback.index("mouth has already made the smile")
        assert frost < hand < smile
        assert m.world_state.wrongness.count() == 3

    def test_repeated_evening_fixtures_use_callbacks_without_replaying(self):
        m = _wrong_cabin_map("complete")
        UseAction().execute(_ctx_for_use(m, "nika"))

        frost = UseAction().execute(_ctx_for_use(m, "window"))
        hand = UseAction().execute(_ctx_for_use(m, "mug"))
        smile = UseAction().execute(_ctx_for_use(m, "nika"))

        assert "keep your eyes off" in frost.feedback
        assert "dishwater" in hand.feedback
        assert "without looking round" in smile.feedback
        assert "Frost builds at the inside corners" not in frost.feedback
        assert "the hand is wrong" not in hand.feedback
        assert "mouth has already made the smile" not in smile.feedback
        assert m.world_state.wrongness.count() == 3

    def test_knuckle_tell_does_not_first_fire_after_refusal(self):
        m = _wrong_cabin_map("dawn")
        m.world_state.ending = "escaped"

        UseAction().execute(_ctx_for_use(m, "mug"))

        assert m.world_state.wrongness.has(AnomalyID.KNUCKLES_BIRCH.value) is False


class TestActIIIReunion:
    """The scripted reunion beats: arrival -> tended -> seated -> complete."""

    def test_entering_wrong_layer_sets_reunion_to_arrival(self):
        m = Map()
        m.world_state.enter_wrong_layer()
        assert m.world_state.reunion_stage == "arrival"

    def test_use_nika_at_arrival_advances_to_tended(self):
        m = _wrong_cabin_map("arrival")
        r = UseAction().execute(_ctx_for_use(m, "nika"))
        assert r.requests == ()
        assert m.world_state.reunion_stage == "tended"
        assert "you called me" in r.feedback.lower()

    def test_use_nika_at_tended_advances_to_seated(self):
        m = _wrong_cabin_map("tended")
        r = UseAction().execute(_ctx_for_use(m, "nika"))
        assert r.requests == ()
        assert m.world_state.reunion_stage == "seated"
        assert "first light" in r.feedback.lower()

    def test_use_mug_before_seated_does_not_advance(self):
        for stage in ("arrival", "tended"):
            m = _wrong_cabin_map(stage)
            r = UseAction().execute(_ctx_for_use(m, "mug"))
            assert m.world_state.reunion_stage == stage
            assert r.requests == ()

    def test_use_mug_at_seated_completes_reunion(self):
        m = _wrong_cabin_map("seated")
        r = UseAction().execute(_ctx_for_use(m, "mug"))
        assert r.requests == ()
        assert m.world_state.reunion_stage == "complete"
        # The blue mug beat: the chip, the impossible rightness.
        assert "blue enamel" in r.feedback.lower()
        assert "Exactly, precisely" not in r.feedback
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
        assert "frost builds at the inside corners" in msg.lower()
        assert "the hand is wrong" in msg.lower()
        assert "mouth has already made the smile" in msg.lower()
        assert m.world_state.consent_given is True
        assert m.world_state.reunion_stage == "consented"
        for anomaly in (
            AnomalyID.FROST_WOOD_GRAIN,
            AnomalyID.KNUCKLES_BIRCH,
            AnomalyID.DELAYED_SMILE,
        ):
            assert m.world_state.wrongness.has(anomaly.value)

    def test_consent_beat_narrates_only_evening_tells_not_already_seen(self):
        m = _wrong_cabin_map("complete")
        UseAction().execute(_ctx_for_use(m, "window"))

        _, msg = m.move("out")

        assert "frost builds at the inside corners" not in msg.lower()
        assert "the hand is wrong" in msg.lower()
        assert "mouth has already made the smile" in msg.lower()
        assert m.world_state.wrongness.count() == 3

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

    def test_dead_directions_do_not_describe_the_outdoors(self):
        """The regression: inside the wrong cabin, "north" answered with trees."""
        m = _wrong_cabin_map("seated")

        for direction in ("north", "south", "bedroom", "konttori"):
            moved, msg = m.move(direction)
            assert moved is False, direction
            assert "trees" not in msg.lower(), direction
            assert "the room does not continue" in msg.lower(), direction

    def test_real_cabin_dead_directions_use_the_indoor_line(self):
        """The wrong layer is not the only interior the line has to serve."""
        m = Map()
        m.current_location_id = "cabin_interior"
        m.current_room_id = "cabin_main"

        moved, msg = m.move("west")

        assert moved is False
        assert msg == DENIAL_INDOORS

    def test_wilderness_still_gets_the_treeline(self):
        m = Map()
        moved, msg = m.move("west")
        assert moved is False
        assert msg == DENIAL_OUTDOORS

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
        assert r.requests == ()
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
        # Any canonical night seams not chosen directly land before the scene.
        for anomaly in (
            AnomalyID.BREATHING_TIDE,
            AnomalyID.PHONE_DARK,
            AnomalyID.WRONG_TINS,
            AnomalyID.MUG_IMPOSSIBLE,
            AnomalyID.BLACK_BOARDS,
        ):
            assert m.world_state.wrongness.has(anomaly.value)
        assert "deep matt black" in text.lower()

    def test_recognition_waits_for_the_unvarying_breath(self):
        m = _wrong_cabin_map("bedded")
        for anomaly in (
            AnomalyID.MEMORY_ALOUD,
            AnomalyID.PHONE_DARK,
            AnomalyID.WRONG_TINS,
            AnomalyID.MUG_IMPOSSIBLE,
            AnomalyID.BLACK_BOARDS,
        ):
            m.world_state.wrongness.add(anomaly.value, "")

        UseAction().execute(_ctx_for_use(m, "mug"))

        assert m.world_state.recognition is False

    def test_repeated_night_observations_use_callbacks(self):
        m = _wrong_cabin_map("bedded")

        first_listen = m.observe_current_room("listen")
        second_listen = m.observe_current_room("listen")
        first_phone = UseAction().execute(_ctx_for_use(m, "phone"))
        second_phone = UseAction().execute(_ctx_for_use(m, "phone"))

        assert "forty breaths" in first_listen.lower()
        assert "stop counting" in second_listen.lower()
        assert "one held breath at a time" in first_phone.feedback.lower()
        assert "put the phone beside you" in second_phone.feedback.lower()
        assert "forty breaths" not in second_listen.lower()
        assert "one held breath at a time" not in second_phone.feedback.lower()

    def test_threshold_completes_the_night_before_recognition(self):
        m = _wrong_cabin_map("bedded")
        m.world_state.wrongness.add(AnomalyID.MEMORY_ALOUD.value, "")
        m.observe_current_room("listen")
        UseAction().execute(_ctx_for_use(m, "phone"))

        result = UseAction().execute(_ctx_for_use(m, "mug"))

        tins = result.feedback.index("Dinner, late")
        boards = result.feedback.index("boards have gone the deep matt black")
        knowing = result.feedback.index("The papers your concussion")
        assert tins < boards < knowing

        mug_again = UseAction().execute(_ctx_for_use(m, "mug"))
        tins_again = UseAction().execute(_ctx_for_use(m, "tins"))
        look_again = m.observe_current_room("look")
        assert "blue mug remains" in mug_again.feedback.lower()
        assert "tins stand" in tins_again.feedback.lower()
        assert "look straight at the floor" in look_again.lower()
        assert "Dinner, late" not in tins_again.feedback
        assert "fire has burned down" not in look_again.lower()

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
            AnomalyID.BREATHING_TIDE,
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
        assert r.requests == ()
        assert m.world_state.reunion_stage == "dawn"
        assert "drink up" in r.feedback.lower()
        assert "handed everything across to a friend" in r.feedback.lower()

    def test_wait_before_recognition_does_not_bring_dawn(self):
        m = _wrong_cabin_map("bedded")
        r = WaitAction().execute(_ctx_plain(m))
        assert m.world_state.reunion_stage == "bedded"
        assert r.requests == ()

    def test_wait_without_seams_does_not_bring_dawn(self):
        """A malformed save (recognition without the gathered seams) must not
        reach an offer it would then be unable to answer: the dawn gate
        matches the refuse/accept dual gate."""
        m = _wrong_cabin_map("night")
        m.world_state.recognition = True  # seams missing
        r = WaitAction().execute(_ctx_plain(m))
        assert m.world_state.reunion_stage == "night"
        assert r.requests == ()

    def test_wait_outside_the_false_cabin_does_not_bring_dawn(self):
        m = self._night_map()
        m.current_room_id = "konttori"

        r = WaitAction().execute(_ctx_plain(m))

        assert m.world_state.reunion_stage == "night"
        assert r.requests == ()

    def _dawn_map(self) -> Map:
        m = self._night_map()
        WaitAction().execute(_ctx_plain(m))
        assert m.world_state.reunion_stage == "dawn"
        return m

    def test_refuse_without_recognition_is_uncertain(self):
        m = _wrong_cabin_map("bedded")
        r = RefuseAction().execute(_ctx_plain(m))
        assert r.requests == ()
        assert m.world_state.ending == "none"

    def test_refuse_in_real_layer_lands_as_no_target(self):
        m = Map()
        m.world_state.recognition = True
        _gather_night_seams(m, NIGHT_SEAM_THRESHOLD)
        r = RefuseAction().execute(_ctx_plain(m))
        assert r.requests == ()

    def test_refuse_before_dawn_is_not_available(self):
        m = self._night_map()
        r = RefuseAction().execute(_ctx_plain(m))
        assert r.requests == ()
        assert m.world_state.ending == "none"

    def test_refuse_at_dawn_lands_the_escape(self):
        m = self._dawn_map()
        r = RefuseAction().execute(_ctx_plain(m))
        assert r.requests == ()
        assert m.world_state.ending == "escaped"
        # She has not left yet: the walk out happens on foot.
        assert m.world_state.is_wrong_layer() is True
        assert "and you are still not her" in r.feedback.lower()
        assert "it's lying out there" in r.feedback.lower()
        assert "i missed your mother's funeral" in r.feedback.lower()
        assert "when you left me the message" in r.feedback.lower()
        assert "you'd taped a photograph" in r.feedback.lower()
        assert "when she left me the message" not in r.feedback.lower()
        assert "whatever is under the face" in r.feedback.lower()

    def test_drinking_the_mug_at_dawn_is_the_stayed_ending(self):
        m = self._dawn_map()
        r = UseAction().execute(_ctx_for_use(m, "mug"))
        assert r.requests == ()
        assert m.world_state.ending == "stayed"
        assert ending_line_for(m.world_state) == "You are home."
        assert "then you stop checking" in r.feedback.lower()
        assert "you hold out the mug" in r.feedback.lower()

    def test_drinking_the_mug_cannot_bypass_a_malformed_dawn_gate(self):
        m = _wrong_cabin_map("dawn")
        m.world_state.recognition = True

        r = UseAction().execute(_ctx_for_use(m, "mug"))

        assert r.requests == ()
        assert m.world_state.ending == "none"

    def test_accept_before_dawn_is_not_available(self):
        m = self._night_map()
        r = AcceptAction().execute(_ctx_plain(m))
        assert r.requests == ()
        assert m.world_state.ending == "none"

    def test_accept_after_refusal_does_not_reopen(self):
        m = self._dawn_map()
        RefuseAction().execute(_ctx_plain(m))
        r = AcceptAction().execute(_ctx_plain(m))
        assert r.requests == ()
        assert m.world_state.ending == "escaped"

    def test_repeated_accept_does_not_replay_the_ending_or_fear_shift(self):
        m = self._dawn_map()
        player = Player()
        player.fear = 80

        first = AcceptAction().execute(_ctx_plain(m, player))
        fear_after_choice = player.fear
        repeated = AcceptAction().execute(_ctx_plain(m, player))

        assert first.requests == ()
        assert repeated.feedback == "You are home."
        assert repeated.requests == ()
        assert player.fear == fear_after_choice
        assert m.world_state.ending == "stayed"

    def test_conflicting_refusal_does_not_replay_after_staying(self):
        m = self._dawn_map()
        player = Player()
        player.fear = 80
        AcceptAction().execute(_ctx_plain(m, player))
        fear_after_choice = player.fear

        rejected = RefuseAction().execute(_ctx_plain(m, player))

        assert rejected.feedback == "You are home."
        assert rejected.requests == ()
        assert player.fear == fear_after_choice
        assert m.world_state.ending == "stayed"

    @pytest.mark.parametrize("legacy_ending", ("accepted", "refused"))
    def test_legacy_endings_reject_new_action_consequences(self, legacy_ending):
        m = self._dawn_map()
        m.world_state.ending = legacy_ending
        player = Player()
        player.fear = 80

        accept_result = AcceptAction().execute(_ctx_plain(m, player))
        refuse_result = RefuseAction().execute(_ctx_plain(m, player))

        assert accept_result.requests == ()
        assert refuse_result.requests == ()
        assert player.fear == 80
        assert m.world_state.ending == legacy_ending


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

    def test_walk_out_does_not_replay_backwards(self):
        m = self._escaped_map()
        m.move("out")

        moved, cabin_msg = m.move("cabin")
        assert moved is False
        assert m.current_room_id == "cabin_clearing"
        assert "do not turn back" in cabin_msg.lower()

        m.move("south")
        moved, clearing_msg = m.move("back")
        assert moved is False
        assert m.current_room_id == "wood_track"
        assert "black clearing is behind" in clearing_msg.lower()

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
        assert r.requests == ()
        assert m.world_state.coda_stage == "called"
        assert "drive slow" in r.feedback.lower()

    def test_carried_phone_cannot_make_the_call_outdoors(self):
        """The phone is carryable: a player who pocketed it in Act I must
        still make the call at the cabin window, not from the grounds."""
        m = self._escaped_map()
        m.move("out")
        m.move("south")
        m.move("south")
        assert m.current_room_id == "cabin_grounds_main"
        player = Player()
        player.add_item(m.items["phone"])  # carried
        ctx = _ctx_plain(m, player)
        ctx.args = {"item": "phone"}
        r = UseAction().execute(ctx)
        assert r.requests == ()
        assert m.world_state.coda_stage == "home"

    def test_wait_after_the_call_starts_the_scraping(self):
        m = self._coda_map()
        UseAction().execute(_ctx_for_use(m, "phone"))
        r = WaitAction().execute(_ctx_plain(m))
        assert r.requests == ()
        assert m.world_state.coda_stage == "scraping"
        assert "scraping" in r.feedback.lower()

    def test_wait_through_the_scraping_ends_the_story(self):
        m = self._coda_map()
        UseAction().execute(_ctx_for_use(m, "phone"))
        WaitAction().execute(_ctx_plain(m))
        r = WaitAction().execute(_ctx_plain(m))
        assert r.requests == ()
        assert m.world_state.coda_stage == "end"
        assert "then it stops" in r.feedback.lower()
        assert ending_line_for(m.world_state) == "You wait."

    def test_story_is_not_over_before_the_final_wait(self):
        m = self._coda_map()
        assert ending_line_for(m.world_state) is None
        UseAction().execute(_ctx_for_use(m, "phone"))
        WaitAction().execute(_ctx_plain(m))
        assert ending_line_for(m.world_state) is None
