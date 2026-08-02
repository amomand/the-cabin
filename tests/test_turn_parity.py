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

from game import save_commands, turn
from game.actions.base import ActionResult
from game.ai_interpreter import ALLOWED_ACTIONS, Intent
from game.events import EventBus
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

        lit = ActionResult.success_result("the fire takes", events=["fire_lit"])
        turn.handle_action_events(lit, engine.player, engine.map, EventBus())

        assert engine.player.fear == 50 - turn.DEFAULT_FIRE_FEAR_REDUCTION

    def test_thrown_into_darkness_raises_fear(self):
        engine = GameEngine()
        engine.player.fear = 10

        thrown = ActionResult.success_result(
            "it disappears", events=["thrown_into_darkness"]
        )
        turn.handle_action_events(thrown, engine.player, engine.map, EventBus())

        assert engine.player.fear == 10 + turn.DEFAULT_DARKNESS_FEAR_INCREASE

    def test_both_surfaces_delegate_to_the_core(self):
        """Neither surface may keep its own copy of the event handling.

        Each surface binds the core function at import, so the patch target is
        the name in the surface's own module, not `game.turn`.
        """
        engine, session = _fresh_surfaces()
        result = ActionResult.success_result("something happens", events=["fire_lit"])

        for surface, where in (
            (engine, "game.game_engine.handle_action_events"),
            (session, "server.session.handle_action_events"),
        ):
            with mock.patch(where) as core:
                surface._handle_action_events(result)

            core.assert_called_once_with(
                result, surface.player, surface.map, surface.event_bus
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
