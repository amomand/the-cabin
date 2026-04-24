"""Tests for GameEngine AI context and save/load behavior."""

from game.game_engine import GameEngine
from game.persistence import SaveManager


class TestGameEngine:
    """Tests for GameEngine internals used by the AI context."""

    def test_build_ai_context_tracks_first_visit_and_revisit(self):
        """AI context distinguishes a first entry from a return visit."""
        engine = GameEngine()

        start_context = engine._build_ai_context()
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
