"""Parity tests: the terminal and web surfaces must decide a turn identically.

Issue #113 was raised because `GameEngine` and `WebGameSession` kept
near-identical private copies of the turn logic, and those copies had already
drifted (the fire-lit fear reduction landed on one surface only). Both now run
through `game.turn`, and these tests exist so a future copy-paste divergence
fails here rather than in a player's session.

The parity assertions deliberately compare the two surfaces against each other
rather than against a hardcoded expectation: the contract is that they agree,
whatever the shared value happens to be.
"""

import unittest.mock as mock

import pytest

from game import save_commands, turn
from game.actions.base import ActionResult
from game.ai_interpreter import ALLOWED_ACTIONS, Intent
from game.death import death_line_for
from game.ending import ending_line_for, ending_reached
from game.events import EventBus
from game.events.requests import (
    DarknessFearRequest,
    FireLitRequest,
    ItemTakenRequest,
    ItemThrownRequest,
)
from game.events.types import ItemTakenEvent, ItemThrownEvent
from game.game_engine import GameEngine
from game.persistence import SaveManager
from server.protocol import RenderFrame, SessionPhase
from server.session import WebGameSession


def _fresh_surfaces():
    """A terminal engine and a web session at the same starting state."""
    engine = GameEngine()
    session = WebGameSession()
    session.handle_input("")  # dismiss the intro keypress
    return engine, session


def _intent(action: str = "look", effects=None, reply: str = "ok") -> Intent:
    return Intent(
        action=action,
        args={},
        confidence=0.9,
        reply=reply,
        effects=effects or {},
    )


class TestAIContextParity:
    def test_both_surfaces_build_the_same_context(self):
        """The prompt payload must not depend on which surface you play on."""
        engine, session = _fresh_surfaces()

        assert engine._build_ai_context() == session._build_ai_context()

    def test_contexts_agree_across_moves_and_layers(self):
        """Not just the opening state: revisits and the wrong-layer cabin too.

        The behaviour itself (visit tracking, which fixtures a layer shows)
        is pinned once in tests/test_game_engine.py; this only proves the web
        session reads the same payload for the same state.
        """
        engine, session = _fresh_surfaces()

        for direction in ("north", "south"):
            for surface in (engine, session):
                moved, _ = surface.map.move(direction, surface.player)
                assert moved is True
            assert engine._build_ai_context() == session._build_ai_context()

        for wrong_layer in (False, True):
            for surface in (engine, session):
                surface.map.current_location_id = "cabin_interior"
                surface.map.current_room_id = "cabin_main"
                if wrong_layer:
                    surface.map.world_state.enter_wrong_layer()
            assert engine._build_ai_context() == session._build_ai_context()

    def test_allowed_actions_are_sorted_on_both_surfaces(self):
        """`ALLOWED_ACTIONS` is a set, so ordering varies by PYTHONHASHSEED.

        The web session used to send `list(ALLOWED_ACTIONS)` while the terminal
        sent `sorted(...)`, which made the two surfaces send byte-different
        prompts for identical state and defeated the prompt cache.
        """
        engine, session = _fresh_surfaces()

        for context in (engine._build_ai_context(), session._build_ai_context()):
            assert context["allowed_actions"] == sorted(ALLOWED_ACTIONS)


class TestEffectParity:
    def test_deltas_are_clamped_to_the_per_turn_cap(self):
        """A single interpreted intent must not be able to end a run.

        Asserted against absolute values rather than surface-vs-surface
        equality: both surfaces call the same function, so they would agree
        on an unclamped value just as readily and the test would pass while
        the clamp was gone.
        """
        engine, session = _fresh_surfaces()
        for surface in (engine, session):
            surface.player.fear = 10
            surface.player.health = 50

        # Well past the per-turn cap in both directions.
        oversized = _intent(effects={"fear": 40, "health": -40})
        engine._apply_effects(oversized)
        session._apply_effects(oversized)

        for surface in (engine, session):
            assert surface.player.fear == 10 + turn.MAX_EFFECT_DELTA
            assert surface.player.health == 50 - turn.MAX_EFFECT_DELTA

    def test_stats_stay_within_bounds(self):
        """Clamping the delta is not enough; the resulting stat is bounded too."""
        engine, session = _fresh_surfaces()
        for surface in (engine, session):
            surface.player.fear = turn.MAX_STAT
            surface.player.health = turn.MIN_STAT

        engine._apply_effects(_intent(effects={"fear": 2, "health": -2}))
        session._apply_effects(_intent(effects={"fear": 2, "health": -2}))

        for surface in (engine, session):
            assert surface.player.fear == turn.MAX_STAT
            assert surface.player.health == turn.MIN_STAT

    def test_skip_inventory_behaves_the_same_on_both_surfaces(self):
        engine, session = _fresh_surfaces()

        target = engine.map.current_room.items[0].name
        grab = _intent(effects={"inventory_add": [target]})

        engine._apply_effects(grab, skip_inventory=True)
        session._apply_effects(grab, skip_inventory=True)

        assert engine.player.get_inventory_names() == session.player.get_inventory_names()
        assert engine.player.get_inventory_names() == []

    def test_authored_results_block_model_effects_on_both_surfaces(self):
        engine, session = _fresh_surfaces()

        for surface, handle_input in (
            (engine, engine.handle_user_input),
            (session, session.handle_input),
        ):
            intent = _intent(effects={"fear": 2})
            surface.action_registry = mock.MagicMock()
            surface.action_registry.execute.return_value = ActionResult.authored(
                "the story owns this turn"
            )

            with mock.patch("game.turn.interpret", return_value=intent):
                handle_input("do the story thing")

            assert surface.player.fear == 0
            assert intent.effects == {"fear": 2}

    def test_generic_results_apply_model_effects_on_both_surfaces(self):
        engine, session = _fresh_surfaces()

        for surface, handle_input in (
            (engine, engine.handle_user_input),
            (session, session.handle_input),
        ):
            intent = _intent(effects={"fear": 2})
            surface.action_registry = mock.MagicMock()
            surface.action_registry.execute.return_value = (
                ActionResult.success_result("the ordinary action lands")
            )

            with mock.patch("game.turn.interpret", return_value=intent):
                handle_input("do the ordinary thing")

            assert surface.player.fear == 2


class TestActionEventParity:
    """Stat-moving events are asserted against the core with a bare bus.

    Driving them through a surface would fire the real quest and cutscene
    listeners, and the terminal's quest screen blocks on stdin. What matters
    for parity is that both surfaces reach the same function, which
    `test_both_surfaces_delegate_to_the_core` pins directly.
    """

    def test_fire_lit_reduces_fear(self):
        """The exact drift issue #113 named: the web path emitted the event
        without granting the fear relief the terminal path did."""
        engine = GameEngine()
        engine.player.fear = 50

        lit = ActionResult.success_result(
            "the fire takes", requests=[FireLitRequest(fear_reduction=5)]
        )
        turn.handle_action_events(lit, engine.player, engine.map, EventBus())

        assert engine.player.fear == 45

    def test_thrown_into_darkness_raises_fear(self):
        engine = GameEngine()
        engine.player.fear = 10

        thrown = ActionResult.success_result(
            "it disappears", requests=[DarknessFearRequest(increase=5)]
        )
        turn.handle_action_events(thrown, engine.player, engine.map, EventBus())

        assert engine.player.fear == 15

    def test_both_surfaces_delegate_to_the_core(self):
        """Neither surface may keep its own copy of the event handling.

        Each surface binds the core function at import, so the patch target is
        the name in the surface's own module, not `game.turn`.
        """
        engine, session = _fresh_surfaces()
        result = ActionResult.success_result(
            "something happens", requests=[FireLitRequest(fear_reduction=5)]
        )

        for surface, where in (
            (engine, "game.game_engine.handle_action_events"),
            (session, "server.session.handle_action_events"),
        ):
            with mock.patch(where) as core:
                surface._handle_action_events(result)

            core.assert_called_once_with(
                result, surface.player, surface.map, surface.event_bus
            )

    def test_both_surfaces_emit_identical_events_and_stat_changes(self):
        engine, session = _fresh_surfaces()
        result = ActionResult.success_result(
            "the stone goes",
            requests=[
                ItemThrownRequest(
                    item_name="stone",
                    target=None,
                    into_darkness=False,
                ),
                ItemTakenRequest(item_name="rope", room_id="wilderness_start"),
                DarknessFearRequest(increase=5),
            ],
        )
        received = []

        for surface in (engine, session):
            surface.player.fear = 10
            surface_events = []
            surface.event_bus.subscribe("ItemThrownEvent", surface_events.append)
            surface.event_bus.subscribe("ItemTakenEvent", surface_events.append)
            surface._handle_action_events(result)
            received.append((surface_events, surface.player.fear))

        assert received[0] == received[1]
        assert received[0] == (
            [
                ItemThrownEvent(
                    item_name="stone",
                    target=None,
                    into_darkness=False,
                ),
                ItemTakenEvent(item_name="rope", room_id="wilderness_start"),
            ],
            15,
        )


class TestSaveCommandParity:
    """Both surfaces must speak the same save vocabulary.

    They deliberately keep separate save directories (a web session gets its
    own throwaway dir), so these tests point both at one empty directory.
    Otherwise the surfaces would differ on contents, not on wording.
    """

    def test_save_vocabulary_is_shared(self, tmp_path):
        engine, session = _fresh_surfaces()
        engine.save_manager = SaveManager(save_dir=tmp_path)
        session.save_manager = SaveManager(save_dir=tmp_path)

        engine._list_saves()
        session._list_saves()
        assert engine._last_feedback == session._last_feedback
        assert engine._last_feedback == save_commands.SAVES_NONE

        engine._delete_save("no-such-slot")
        session._delete_save("no-such-slot")
        assert engine._last_feedback == session._last_feedback
        assert engine._last_feedback == save_commands.SLOT_MISSING

        engine._save_game("a-slot")
        session._save_game("a-slot")
        assert engine._last_feedback == session._last_feedback
        assert engine._last_feedback == save_commands.SAVE_FIXED

    def test_missing_slot_leaves_the_run_untouched(self, tmp_path):
        """A load miss must not reset the run on either surface.

        The post-load resets are gated on the load actually landing. Ungating
        them is player-visible: `_last_room_id = None` forces a full room
        re-description where a miss should print only the one line.
        """
        engine, session = _fresh_surfaces()
        engine.save_manager = SaveManager(save_dir=tmp_path)
        session.save_manager = SaveManager(save_dir=tmp_path)

        engine.player.fear = 33
        session.player.fear = 33
        engine._last_room_id = "a-room-already-drawn"
        session._last_room_id = "a-room-already-drawn"
        queued = RenderFrame(lines=["a queued overlay"], clear=True, wait_for_key=True)
        session._pending_overlays.append(queued)

        engine._load_game("no-such-slot")
        session._load_game("no-such-slot")

        assert engine.player.fear == 33
        assert session.player.fear == 33
        assert engine._last_feedback == session._last_feedback
        assert engine._last_feedback == save_commands.SLOT_MISSING

        # No forced redraw and no session reset on a miss.
        assert engine._last_room_id == "a-room-already-drawn"
        assert session._last_room_id == "a-room-already-drawn"
        assert session._pending_overlays == [queued]

    def test_successful_load_resets_the_surface(self, tmp_path):
        """The mirror of the miss case: a real load does force the redraw."""
        engine, session = _fresh_surfaces()
        engine.save_manager = SaveManager(save_dir=tmp_path)
        session.save_manager = SaveManager(save_dir=tmp_path)

        engine._save_game("a-slot")
        engine._last_room_id = "a-room-already-drawn"
        session._last_room_id = "a-room-already-drawn"
        session._pending_overlays.append(
            RenderFrame(lines=["stale"], clear=True, wait_for_key=True)
        )
        # Start off the target phase, or asserting the reset proves nothing.
        session.phase = SessionPhase.OVERLAY_KEYPRESS

        engine._load_game("a-slot")
        session._load_game("a-slot")

        assert engine._last_feedback == save_commands.LOAD_SETTLED
        assert session._last_feedback == save_commands.LOAD_SETTLED
        assert engine._last_room_id is None
        assert session._last_room_id is None
        assert session._pending_overlays == []
        assert session.phase == SessionPhase.AWAITING_INPUT


class TestRunClosingParity:
    """Both surfaces must close a run on the same death and ending states.

    The decisions live in `game.death` and `game.ending` (unit-tested in
    tests/test_death.py and tests/test_ending.py) and the terminal glue is
    pinned in tests/test_game_engine.py. Each surface keeps its own glue that
    acts on those decisions, so the glue is compared here rather than
    re-asserted per surface.
    """

    @pytest.mark.parametrize(
        ("ending", "coda_stage"),
        [
            ("none", "none"),
            ("stayed", "none"),
            ("escaped", "home"),
            ("escaped", "end"),
            ("refused", "none"),
        ],
        ids=["open", "stayed", "escaped-mid-coda", "escaped-coda-done", "legacy-refused"],
    )
    def test_ending_checks_agree(self, ending, coda_stage, capsys):
        engine, session = _fresh_surfaces()
        for surface in (engine, session):
            surface.map.world_state.ending = ending
            surface.map.world_state.coda_stage = coda_stage

        engine_closed = engine._check_story_end()
        frame = session._ending_frame_if_over()

        assert engine_closed == ending_reached(engine.map.world_state)
        assert (frame is not None) == engine_closed
        assert (engine.running is False) == engine_closed
        assert (session.phase == SessionPhase.ENDED) == engine_closed
        line = ending_line_for(engine.map.world_state)
        if line is not None:
            assert line in capsys.readouterr().out
            assert line in frame.lines

    @pytest.mark.parametrize("closed_state", ["death", "stayed", "refused"])
    def test_loading_a_closed_save_closes_both_surfaces(
        self, closed_state, tmp_path, capsys
    ):
        """A save persisted at death or past an ending must not reopen on load,
        and the closing line must be the same one on both surfaces."""
        engine, session = _fresh_surfaces()
        engine.save_manager = SaveManager(save_dir=tmp_path)
        session.save_manager = SaveManager(save_dir=tmp_path)

        if closed_state == "death":
            engine.player.fear = 100
        else:
            engine.map.world_state.ending = closed_state
        engine._save_game("closed")
        engine.player.fear = 0
        engine.map.world_state.ending = "none"

        engine.handle_user_input("load closed")
        frame = session.handle_input("load closed")

        assert engine.running is False
        assert session.phase == SessionPhase.ENDED
        assert frame.game_over is True
        assert engine.player.fear == session.player.fear
        assert engine.map.world_state.ending == session.map.world_state.ending
        line = death_line_for(engine.player) or ending_line_for(engine.map.world_state)
        if line is not None:
            assert line in capsys.readouterr().out
            assert line in frame.lines


class TestRoomRenderParity:
    """Both surfaces head a room with the name the layer gives it, and tell a
    room's description whether the player has been here before."""

    @staticmethod
    def _place(surface, room_id: str, wrong_layer: bool) -> None:
        surface.map._set_current_room_by_id(room_id, been_here_before=True)
        if wrong_layer:
            surface.map.world_state.enter_wrong_layer()
            surface.map.world_state.transition_ending_to("escaped")

    @pytest.mark.parametrize(
        "wrong_layer, header", [(False, "Wood Track"), (True, "The Woods")]
    )
    def test_room_header_follows_the_layer_on_both_surfaces(
        self, wrong_layer, header, capsys
    ):
        engine, session = _fresh_surfaces()
        for surface in (engine, session):
            self._place(surface, "wood_track", wrong_layer)

        engine.render()
        terminal_lines = capsys.readouterr().out.splitlines()
        web_lines = session._render_room().lines

        assert terminal_lines[0] == header
        assert web_lines[0] == header

    @staticmethod
    def _record_revisits(surface, room_id: str) -> list:
        seen = []

        def describe(player, world_state, base, revisit):
            seen.append(revisit)
            return base

        for location in surface.map.locations.values():
            if room_id in location.rooms:
                location.rooms[room_id]._description_fn = describe
        return seen

    def test_forced_redraw_of_the_shown_room_is_a_revisit(self):
        """After an overlay the same room draws again; the arrival must not
        narrate itself twice, even though the map has not recorded a return."""
        engine, session = _fresh_surfaces()
        engine_seen = self._record_revisits(engine, "wilderness_start")
        session_seen = self._record_revisits(session, "wilderness_start")
        # The intro dismissal already drew the opening room on the web; start
        # both surfaces from nothing shown so the first render is the arrival.
        session._last_room_id = None
        session._described_room_id = None

        with mock.patch("builtins.print"):
            engine.render()
            engine._last_room_id = None  # what the quest and map screens do
            engine.render()
        session._render_room()
        session._last_room_id = None  # what an overlay dismissal does
        session._render_room()

        assert engine_seen == [False, True]
        assert session_seen == [False, True]

    def test_overlay_on_arrival_still_counts_as_a_first_visit(self):
        """The cabin's entry overlays come before its first description, so the
        redraw they force is the arrival, not a return."""
        engine, session = _fresh_surfaces()
        engine_seen = self._record_revisits(engine, "cabin_main")
        session_seen = self._record_revisits(session, "cabin_main")

        with mock.patch("builtins.print"):
            engine.render()
            engine.handle_user_input("north")
            engine.render()
            with mock.patch.object(
                engine, "_show_quest_screen",
                side_effect=lambda *a, **k: setattr(engine, "_last_room_id", None),
            ), mock.patch("game.cutscene.Cutscene.play"):
                engine.handle_user_input("cabin")
            engine.render()
        session.handle_input("north")
        session.handle_input("cabin")
        while session.phase == SessionPhase.OVERLAY_KEYPRESS:
            session.handle_input("")

        assert engine_seen == [False]
        # The web builds and drops a room frame when a turn queues overlays,
        # so the callback may run more than once; every run is the arrival.
        assert session_seen and all(seen is False for seen in session_seen)

    def test_load_resumes_the_room_as_a_revisit(self, tmp_path):
        """A save is made at a prompt, after its room was shown."""
        engine, session = _fresh_surfaces()
        engine.save_manager = SaveManager(save_dir=tmp_path)
        session.save_manager = SaveManager(save_dir=tmp_path)
        engine._save_game("first-entry")
        engine_seen = self._record_revisits(engine, "wilderness_start")
        session_seen = self._record_revisits(session, "wilderness_start")

        engine._load_game("first-entry")
        session._load_game("first-entry")
        with mock.patch("builtins.print"):
            engine.render()
        session._render_room()

        assert engine.map.current_room_been_here_before is False
        assert engine_seen == [True]
        assert session_seen == [True]

    def test_arrival_render_passes_the_visit_record_to_the_description(self):
        engine, session = _fresh_surfaces()
        seen = []

        def describe(player, world_state, base, revisit):
            seen.append(revisit)
            return base

        for surface in (engine, session):
            room = surface.map.current_room
            room._description_fn = describe

        engine.map.current_room_been_here_before = True
        session.map.current_room_been_here_before = True
        # The session described the opening room when the intro was
        # dismissed; forget it, the way a load does, so the room renders again.
        session._last_room_id = None
        with mock.patch("builtins.print"):
            engine.render()
        session._render_room()

        assert seen == [True, True]


class TestBlankInputParity:
    def test_blank_input_is_not_a_turn_on_either_surface(self, monkeypatch):
        """Bare Enter (terminal) or a raced keypress (web) must not reach the
        interpreter. Each surface guards this in its own input handler."""

        def _fail(*args, **kwargs):
            raise AssertionError("interpret() must not run for blank input")

        monkeypatch.setattr("game.turn.interpret", _fail)
        engine, session = _fresh_surfaces()

        for blank in ("", "   "):
            engine.handle_user_input(blank)
            session.handle_input(blank)

        assert engine.running is True
        assert session.phase == SessionPhase.AWAITING_INPUT


class TestTurnCoreFeedbackChannel:
    def test_listener_feedback_survives_the_turn(self):
        """Feedback is written through a callback, not returned, so a quest or
        cutscene listener firing during event handling can replace the action's
        own narration. A returned value would clobber it."""
        engine = GameEngine()

        class _StubRegistry:
            def execute(self, *_args, **_kwargs):
                return ActionResult.success_result("the action speaks")

        def _late_listener(_result, _player, _game_map, _event_bus):
            engine._set_feedback("the quest speaks last")

        with mock.patch("game.turn.interpret", return_value=_intent()), mock.patch(
            "game.turn.handle_action_events", _late_listener
        ):
            turn.take_turn(
                "do the thing",
                player=engine.player,
                game_map=engine.map,
                quest_manager=engine.quest_manager,
                action_registry=_StubRegistry(),
                event_bus=engine.event_bus,
                set_feedback=engine._set_feedback,
            )

        assert engine._last_feedback == "the quest speaks last"
