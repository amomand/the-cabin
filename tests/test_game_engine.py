"""Tests for GameEngine AI context and save/load behavior."""

from pathlib import Path

from game.config import Config
from game.game_engine import (
    DEATH_LINE_FADE,
    DEATH_LINE_FEAR_COLLAPSE,
    GameEngine,
)
from game.persistence import SaveManager
from game.story.anomalies import AnomalyID
from game.story.tells import log_tell


class TestGameEngine:
    """Tests for GameEngine internals used by the AI context."""

    def test_terminal_save_manager_uses_cabin_save_dir(self, monkeypatch, tmp_path):
        save_dir = tmp_path / "configured-saves"
        monkeypatch.setenv("CABIN_SAVE_DIR", str(save_dir))
        config = Config.load(tmp_path / "missing-config.json")
        monkeypatch.setattr("game.game_engine.get_config", lambda: config)

        engine = GameEngine()

        assert engine.save_manager.save_dir == Path(save_dir)
        assert not save_dir.exists()

    def test_build_ai_context_tracks_first_visit_and_revisit(self):
        """AI context distinguishes a first entry from a return visit."""
        engine = GameEngine()

        start_context = engine._build_ai_context()
        assert start_context["room_id"] == "wilderness_start"
        assert start_context["been_here_before"] is False
        assert start_context["rooms_visited"] == 1

        moved, _ = engine.map.move("north", engine.player)
        assert moved is True

        first_visit_context = engine._build_ai_context()
        assert first_visit_context["been_here_before"] is False
        assert first_visit_context["rooms_visited"] == 2

        moved, _ = engine.map.move("south", engine.player)
        assert moved is True

        revisit_context = engine._build_ai_context()
        assert revisit_context["been_here_before"] is True
        assert revisit_context["rooms_visited"] == 2

    def test_build_ai_context_hides_wrong_layer_fixtures_in_real_cabin(self):
        engine = GameEngine()
        engine.map.current_location_id = "cabin_interior"
        engine.map.current_room_id = "cabin_main"

        context = engine._build_ai_context()

        assert "window" not in context["room_items"]
        assert "mug" not in context["room_items"]
        assert "nika" not in context["room_items"]

    def test_build_ai_context_keeps_wrong_layer_fixtures_in_wrong_cabin(self):
        engine = GameEngine()
        engine.map.current_location_id = "cabin_interior"
        engine.map.current_room_id = "cabin_main"
        engine.map.world_state.enter_wrong_layer()

        context = engine._build_ai_context()

        assert "window" in context["room_items"]
        assert "mug" in context["room_items"]
        assert "nika" in context["room_items"]

    def test_load_game_restores_current_room_history(self, tmp_path):
        """Loading restores the current room and whether it is a revisit."""
        engine = GameEngine()
        engine.save_manager = SaveManager(save_dir=tmp_path / "saves")

        engine.map.move("north", engine.player)
        engine.map.move("south", engine.player)
        assert engine.map.current_room.id == "wilderness_start"
        assert engine.map.current_room_been_here_before is True

        engine._save_game("visit-state")

        engine.map.move("north", engine.player)
        assert engine.map.current_room.id == "cabin_clearing"

        engine._load_game("visit-state")

        assert engine.map.current_room.id == "wilderness_start"
        assert engine.map.current_room_been_here_before is True
        assert engine.map.get_visited_rooms() == {"wilderness_start", "cabin_clearing"}

    def test_load_game_falls_back_to_dev_seed_name(self, tmp_path):
        """Named dev seeds are permanently available without copying JSON files."""
        engine = GameEngine()
        engine.save_manager = SaveManager(save_dir=tmp_path / "empty-saves")

        engine._load_game("act1_end")

        assert engine.map.current_room.id == "bedroom"
        assert engine.map.world_state.first_morning is True
        assert "warm_up" in engine.quest_manager.completed_quests
        assert "somewhere remembered" in engine._last_feedback

    def test_load_missing_save_is_diegetic(self, tmp_path):
        engine = GameEngine()
        engine.save_manager = SaveManager(save_dir=tmp_path / "empty-saves")

        engine._load_game("missing")

        assert "find nothing tied to it" in engine._last_feedback
        assert "save" not in engine._last_feedback.lower()
        assert "slot" not in engine._last_feedback.lower()

    def test_save_feedback_is_diegetic(self, tmp_path):
        engine = GameEngine()
        engine.save_manager = SaveManager(save_dir=tmp_path / "saves")

        engine._save_game("test-save")

        assert "fix this moment" in engine._last_feedback
        assert "save" not in engine._last_feedback.lower()

    def test_list_saves_when_empty(self, tmp_path):
        """`saves` with no save files reports an empty list diegetically."""
        engine = GameEngine()
        engine.save_manager = SaveManager(save_dir=tmp_path / "empty-saves")

        engine._list_saves()

        assert "no fixed points" in engine._last_feedback

    def test_list_saves_shows_known_slots(self, tmp_path):
        """`saves` lists every slot the player has written, by name."""
        engine = GameEngine()
        engine.save_manager = SaveManager(save_dir=tmp_path / "saves")

        engine._save_game("slot-one")
        engine._save_game("slot-two")
        engine._list_saves()

        feedback = engine._last_feedback
        assert "slot-one" in feedback
        assert "slot-two" in feedback

    def test_delete_existing_save_removes_it(self, tmp_path):
        """`delete save NAME` removes the file and confirms diegetically."""
        engine = GameEngine()
        engine.save_manager = SaveManager(save_dir=tmp_path / "saves")
        engine._save_game("doomed")
        assert engine.save_manager.save_exists("doomed")

        engine._delete_save("doomed")

        assert not engine.save_manager.save_exists("doomed")
        assert "doomed" in engine._last_feedback

    def test_delete_nonexistent_save_says_so(self, tmp_path):
        """Deleting a slot that does not exist uses the missing-thread line."""
        engine = GameEngine()
        engine.save_manager = SaveManager(save_dir=tmp_path / "empty-saves")

        engine._delete_save("nope")

        assert "find nothing tied to it" in engine._last_feedback

    def test_quest_update_feedback_has_no_label(self):
        """Quest update callbacks render bare in-world prose."""
        engine = GameEngine()

        engine._on_quest_updated("The fire has taken. The room exhales.")

        assert engine._last_feedback == "The fire has taken. The room exhales."
        assert "Quest Update:" not in engine._last_feedback

    def test_quest_completion_feedback_has_no_label(self):
        """Quest completion callbacks render bare in-world prose."""
        engine = GameEngine()

        engine._on_quest_completed("Warmth gathers in the walls.")

        assert engine._last_feedback == "Warmth gathers in the walls."
        assert "Quest Complete:" not in engine._last_feedback

    def test_quest_screen_uses_diegetic_dismiss_prompt(self, monkeypatch, capsys):
        """The terminal quest overlay does not print interface instructions."""
        import builtins
        import game.game_engine as game_engine_module

        engine = GameEngine()
        monkeypatch.setattr(engine, "clear_terminal", lambda: None)
        monkeypatch.setattr(
            game_engine_module.termios,
            "tcgetattr",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(game_engine_module.termios.error()),
        )
        monkeypatch.setattr(builtins, "input", lambda _prompt="": "")

        engine._show_quest_screen("The work waits in the cold.")

        output = capsys.readouterr().out
        assert "*Back to the room.*" in output
        assert "Press any key" not in output
        assert "Press Enter" not in output

    def test_map_screen_uses_diegetic_dismiss_prompt(self, monkeypatch, capsys):
        """The terminal map overlay does not print interface instructions."""
        import builtins
        import game.game_engine as game_engine_module

        engine = GameEngine()
        monkeypatch.setattr(engine, "clear_terminal", lambda: None)
        monkeypatch.setattr(
            game_engine_module.termios,
            "tcgetattr",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(game_engine_module.termios.error()),
        )
        monkeypatch.setattr(builtins, "input", lambda _prompt="": "")

        engine._show_map()

        output = capsys.readouterr().out
        assert "*The room returns.*" in output
        assert "Press any key" not in output
        assert "Press Enter" not in output


class TestDeathHandling:
    """Fear at 100 or health at 0 ends the run with an authored line."""

    def test_running_continues_below_thresholds(self, capsys):
        engine = GameEngine()
        engine.player.fear = 99
        engine.player.health = 1

        died = engine._check_death()

        assert died is False
        assert engine.running is True
        assert capsys.readouterr().out == ""

    def test_fear_at_100_ends_run_with_authored_line(self, capsys):
        engine = GameEngine()
        engine.player.fear = 100

        died = engine._check_death()

        assert died is True
        assert engine.running is False
        out = capsys.readouterr().out
        assert DEATH_LINE_FEAR_COLLAPSE in out
        assert DEATH_LINE_FADE not in out

    def test_health_at_zero_ends_run_with_authored_line(self, capsys):
        engine = GameEngine()
        engine.player.health = 0

        died = engine._check_death()

        assert died is True
        assert engine.running is False
        out = capsys.readouterr().out
        assert DEATH_LINE_FADE in out
        assert DEATH_LINE_FEAR_COLLAPSE not in out

    def test_fear_collapse_takes_precedence_over_fade(self, capsys):
        engine = GameEngine()
        engine.player.fear = 100
        engine.player.health = 0

        engine._check_death()

        out = capsys.readouterr().out
        assert DEATH_LINE_FEAR_COLLAPSE in out
        assert DEATH_LINE_FADE not in out

    def test_pending_feedback_lands_before_closing_line(self, capsys):
        engine = GameEngine()
        engine.player.fear = 100
        engine._last_feedback = "Something gives in your chest."

        engine._check_death()

        out = capsys.readouterr().out
        assert "Something gives in your chest." in out
        assert out.index("Something gives in your chest.") < out.index(
            DEATH_LINE_FEAR_COLLAPSE
        )
        # Feedback is consumed so render() won't reprint it.
        assert engine._last_feedback == ""

    def test_death_lines_stay_diegetic(self):
        """No fourth-wall language in the closing beats."""
        for line in (DEATH_LINE_FEAR_COLLAPSE, DEATH_LINE_FADE):
            lower = line.lower()
            for banned in ("game over", "you lose", "invalid", "error", "death"):
                assert banned not in lower, line

    def test_load_into_death_state_ends_run(self, tmp_path, capsys):
        """A save persisted at the death threshold ends the run on load."""
        from game.input.handler import ParsedInput, InputType

        engine = GameEngine()
        engine.save_manager = SaveManager(save_dir=tmp_path / "saves")
        engine.player.fear = 100  # save at fear collapse threshold
        engine._save_game("dead-on-arrival")

        # Reset and route a load through handle_user_input so the death check
        # in the LOAD branch is exercised.
        engine.running = True
        engine.player.fear = 0
        engine.input_handler.parse = lambda raw: ParsedInput(
            input_type=InputType.LOAD,
            slot_name="dead-on-arrival",
            raw_text=raw,
        )

        engine.handle_user_input("load dead-on-arrival")

        assert engine.running is False
        assert DEATH_LINE_FEAR_COLLAPSE in capsys.readouterr().out

    def test_lyer_encounter_does_not_kill_player(self):
        """The Act II climax must not push fear to 100 and end the run."""
        engine = GameEngine()
        engine.player.fear = 80  # +40 would land on the death threshold
        engine.player.health = 50

        engine.map._trigger_lyer_encounter(engine.player)

        assert engine.player.fear < 100
        assert engine.player.health > 0
        # _check_death is normally called from handle_user_input; verify the
        # post-encounter state would not trigger it.
        assert engine._check_death() is False
        assert engine.running is True


class TestEndingHandling:
    """The stayed ending and completed coda stop behind their last lines."""

    def test_no_ending_leaves_the_run_open(self, capsys):
        engine = GameEngine()

        assert engine._check_story_end() is False
        assert engine.running is True
        assert capsys.readouterr().out == ""

    def test_stayed_ending_stops_the_run(self, capsys):
        engine = GameEngine()
        engine.map.world_state.ending = "stayed"

        assert engine._check_story_end() is True
        assert engine.running is False
        assert "You are home." in capsys.readouterr().out

    def test_escape_stays_open_until_the_coda_finishes(self, capsys):
        engine = GameEngine()
        engine.map.world_state.ending = "escaped"
        engine.map.world_state.coda_stage = "home"

        assert engine._check_story_end() is False
        assert engine.running is True
        assert capsys.readouterr().out == ""

    def test_coda_narration_lands_before_the_run_stops(self, capsys):
        engine = GameEngine()
        engine.map.world_state.ending = "escaped"
        engine.map.world_state.coda_stage = "end"
        engine._last_feedback = "You sit in your grandmother's chair."

        engine._check_story_end()

        out = capsys.readouterr().out
        assert "You sit in your grandmother's chair." in out
        assert "You wait." in out
        assert engine._last_feedback == ""

    def test_death_takes_precedence_over_ending(self, capsys):
        """A turn that lands both ends as a death, with the death line last."""
        engine = GameEngine()
        engine.map.world_state.ending = "stayed"
        engine.player.fear = 100

        assert engine._check_death() is True
        assert engine.running is False
        assert DEATH_LINE_FEAR_COLLAPSE in capsys.readouterr().out

    def test_stayed_ending_through_handle_user_input_ends_the_run(self, capsys):
        """The full turn path, not just the checker, has to close the run."""
        engine = GameEngine()
        ws = engine.map.world_state
        ws.enter_wrong_layer()
        ws.recognition = True
        ws.reunion_stage = "dawn"
        for anomaly in (
            AnomalyID.MEMORY_ALOUD,
            AnomalyID.BREATHING_TIDE,
            AnomalyID.PHONE_DARK,
            AnomalyID.MUG_IMPOSSIBLE,
        ):
            log_tell(ws, anomaly)
        engine.map.current_location_id = "cabin_interior"
        engine.map.current_room_id = "cabin_main"

        engine.handle_user_input("drink up")

        assert ws.ending == "stayed"
        assert engine.running is False
        output = capsys.readouterr().out
        assert "Frost covers the glass in finished rings" in output
        assert "You are home." in output

    def test_load_into_ended_state_stops_the_run(self, tmp_path, capsys):
        """A save persisted past an ending does not reopen on load."""
        from game.input.handler import ParsedInput, InputType

        engine = GameEngine()
        engine.save_manager = SaveManager(save_dir=tmp_path / "saves")
        engine.map.world_state.ending = "refused"
        engine._save_game("after-the-walk")

        engine.running = True
        engine.map.world_state.ending = "none"
        engine.input_handler.parse = lambda raw: ParsedInput(
            input_type=InputType.LOAD,
            slot_name="after-the-walk",
            raw_text=raw,
        )

        engine.handle_user_input("load after-the-walk")

        assert engine.map.world_state.ending == "refused"
        assert engine.running is False


class TestFireLitComfort:
    def test_fire_lit_event_reduces_fear(self):
        """Pins the terminal side of the fire-lit fear reduction; the web
        session is held to it by tests/test_turn_parity.py."""
        from game.actions.base import ActionResult
        from game.events.requests import FireLitRequest

        engine = GameEngine()
        # The FireLitEvent can trigger the warm-up quest listener, whose
        # terminal screen blocks on a keypress; neutralise it for the test.
        engine._show_quest_screen = lambda *args, **kwargs: None
        engine.player.fear = 30
        result = ActionResult(
            success=True,
            feedback="",
            requests=(FireLitRequest(fear_reduction=5),),
        )

        engine._handle_action_events(result, intent=None)

        assert engine.player.fear == 25


class TestBlankInputIsNotATurn:
    """Bare Enter at the terminal prompt must not run a game turn.

    Blank input used to reach the interpreter as an empty game action. The
    web-side race is in tests/server/test_session.py::TestBlankInputIsNotATurn
    and both surfaces are held together in tests/test_turn_parity.py.
    """

    def test_blank_input_never_reaches_interpreter(self, monkeypatch):
        def _fail(*args, **kwargs):
            raise AssertionError("interpret() must not run for blank input")

        monkeypatch.setattr("game.turn.interpret", _fail)
        engine = GameEngine()
        engine.handle_user_input("")
        engine.handle_user_input("   ")
        assert engine.running is True
