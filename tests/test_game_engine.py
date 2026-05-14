"""Tests for GameEngine AI context and save/load behavior."""

from game.game_engine import (
    DEATH_LINE_FADE,
    DEATH_LINE_FEAR_COLLAPSE,
    GameEngine,
)
from game.persistence import SaveManager


class TestGameEngine:
    """Tests for GameEngine internals used by the AI context."""

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
