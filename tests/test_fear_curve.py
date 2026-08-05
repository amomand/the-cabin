"""The authored fear curve across Acts II-V (issue #185).

Fear used to freeze at 40 from the Act II climax to the end of the game: the
climax was the only beat in the back half that touched it, and every rule-based
intent carries `effects=None`, so the AI channel contributed nothing either.
Twenty-five turns of the most frightening material in the story with a dead
gauge on screen.

These tests pin *movement and direction*, not exact totals. The numbers live in
`game/story/fear.py` and are meant to be tuned; a test that hard-coded them
would just be the table written twice.
"""

from __future__ import annotations

import pytest

from game.actions.accept import AcceptAction
from game.actions.refuse import RefuseAction
from game.actions.use import UseAction
from game.actions.wait import WaitAction
from game.devtools.seed_saves import SEEDS
from game.map import Map
from game.player import Player
from game.story import AnomalyID, fear, log_tell
from game.world_state import WorldState

from tests.test_acts_3_4_5 import _ctx_for_use, _ctx_plain, _wrong_cabin_map


class TestShiftIsBounded:
    def test_shift_never_reaches_the_collapse_threshold(self):
        """Scripted beats do not kill. A run ends on the dawn choice, never
        because a beat happened to land on 100."""
        player = Player()
        player.fear = 95

        fear.shift(player, 999)

        assert player.fear == fear.AUTHORED_CEILING
        assert player.fear < 100

    def test_shift_floors_at_zero(self):
        player = Player()
        player.fear = 3

        fear.shift(player, -50)

        assert player.fear == 0

    def test_shift_tolerates_no_player(self):
        """Several beat helpers are reachable from dev tooling and tests that
        carry world state but no player."""
        fear.shift(None, 10)  # must not raise


class TestTellsCost:
    def test_a_newly_logged_tell_raises_fear(self):
        ws, player = WorldState(), Player()

        log_tell(ws, AnomalyID.FOX_TRACKS, player)

        assert player.fear == fear.TELL_OBSERVED

    def test_seeing_the_same_wrongness_twice_costs_nothing(self):
        """The log dedupes, so the fear is in noticing, not in looking again."""
        ws, player = WorldState(), Player()

        log_tell(ws, AnomalyID.FOX_TRACKS, player)
        log_tell(ws, AnomalyID.FOX_TRACKS, player)

        assert player.fear == fear.TELL_OBSERVED


class TestTheReunionLowersFear:
    """The lie is comfort. Being tended, sat down and given coffee is the trap
    working, and a curve that only climbed would say the opposite."""

    @pytest.mark.parametrize("stage", ["arrival", "tended"])
    def test_being_tended_and_seated_lowers_fear(self, stage):
        m = _wrong_cabin_map(stage)
        player = Player()
        player.fear = 50

        UseAction().execute(_ctx_for_use(m, "nika", player))

        assert player.fear < 50

    def test_the_first_mouthful_lowers_fear(self):
        m = _wrong_cabin_map("seated")
        player = Player()
        player.fear = 50

        UseAction().execute(_ctx_for_use(m, "mug", player))

        assert m.world_state.reunion_stage == "complete"
        assert player.fear < 50


class TestTheLieShowingThroughRaisesFear:
    def test_the_consent_door_raises_fear(self):
        m = _wrong_cabin_map("complete")
        player = Player()
        player.fear = 30

        moved, _ = m.move("out", player)

        assert moved is False
        assert m.world_state.consent_given is True
        assert player.fear == 30 + fear.CONSENT_DOOR

    def test_the_knowing_is_the_largest_step_in_act_iv(self):
        m = _wrong_cabin_map("bedded")
        ws = m.world_state
        for anomaly in (AnomalyID.MEMORY_ALOUD, AnomalyID.PHONE_DARK, AnomalyID.WRONG_TINS):
            ws.wrongness.add(anomaly.value, "")
        player = Player()
        player.fear = 40

        result = UseAction().execute(_ctx_for_use(m, "mug", player))

        assert ws.recognition is True
        assert "let the knowing finish" in result.feedback
        # The seam's own tell plus the knowing itself.
        assert player.fear > 40 + fear.RECOGNITION


class TestTheDawnChoiceMovesFearInOppositeDirections:
    def _at_dawn(self):
        m = _wrong_cabin_map("night")
        ws = m.world_state
        ws.recognition = True
        for anomaly in (AnomalyID.MEMORY_ALOUD, AnomalyID.PHONE_DARK,
                        AnomalyID.WRONG_TINS, AnomalyID.MUG_IMPOSSIBLE):
            ws.wrongness.add(anomaly.value, "")
        ws.reunion_stage = "dawn"
        player = Player()
        player.fear = 70
        return m, player

    def test_staying_lets_the_fear_go_quiet(self):
        """Taking the mug is surrender, and the fear goes with her."""
        m, player = self._at_dawn()

        AcceptAction().execute(_ctx_plain(m, player))

        assert m.world_state.ending == "stayed"
        assert player.fear < 70

    def test_refusing_stops_the_pretence_and_raises_it(self):
        m, player = self._at_dawn()

        RefuseAction().execute(_ctx_plain(m, player))

        assert m.world_state.ending == "escaped"
        assert player.fear > 70


class TestTheWalkOutAndCoda:
    def _escaped_at_the_door(self):
        m = _wrong_cabin_map("dawn")
        m.world_state.ending = "escaped"
        player = Player()
        player.fear = 60
        return m, player

    def test_every_step_of_the_walk_out_moves_fear(self):
        m, player = self._escaped_at_the_door()
        readings = [player.fear]

        for direction in ("out", "south", "south"):
            m.move(direction, player)
            readings.append(player.fear)

        # Threshold up, woods up, arriving home down.
        assert readings[1] > readings[0]
        assert readings[2] > readings[1]
        assert readings[3] < readings[2]
        assert m.world_state.coda_stage == "home"

    def test_the_scraping_under_the_boards_raises_fear(self):
        m = Map()
        ws = m.world_state
        ws.ending = "escaped"
        ws.coda_stage = "called"
        m.current_location_id = "cabin_interior"
        m.current_room_id = "cabin_main"
        player = Player()
        player.fear = 50

        WaitAction().execute(_ctx_plain(m, player))

        assert ws.coda_stage == "scraping"
        assert player.fear == 50 + fear.CODA_SCRAPING


class TestSeedsCarryReachableStats:
    """The Act III+ seeds used to load at fear 0 and full health, which is not
    a state play can reach: they flipped the layer by hand and skipped the
    climax entirely."""

    @pytest.mark.parametrize(
        "name",
        ["act3_arrival", "act3_seated", "act3_consented",
         "act4_night", "act4_recognition", "act5_dawn", "coda_home"],
    )
    def test_back_half_seeds_are_not_at_zero_fear(self, name):
        state = SEEDS[name]()

        assert state.player.fear > 0

    def test_the_arrival_seed_carries_the_climax_injury(self):
        state = SEEDS["act3_arrival"]()

        assert state.player.health < 100
        assert state.player.fear >= fear.CLIMAX_FLIGHT
        assert state.world_state.lyer_encountered is True
        assert state.world_state.is_wrong_layer() is True
        assert state.map.current_room_id == "cabin_main"

    def test_the_dawn_seed_is_frightened_enough_to_be_offered_the_mug(self):
        """The stayed ending used to fire with the meter reading zero: the
        player took the mug from the thing wearing their oldest friend with
        nothing on the gauge at all."""
        state = SEEDS["act5_dawn"]()

        assert state.player.fear > fear.CLIMAX_FLIGHT
