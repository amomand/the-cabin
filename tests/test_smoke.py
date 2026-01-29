"""
Smoke tests to verify all game modules can be imported.
"""


class TestModuleImports:
    """Verify all game modules are importable."""

    def test_import_player(self):
        from game.player import Player
        assert Player is not None

    def test_import_item(self):
        from game.item import Item, create_items
        assert Item is not None
        assert create_items is not None

    def test_import_wildlife(self):
        from game.wildlife import Wildlife, create_wildlife
        assert Wildlife is not None
        assert create_wildlife is not None

    def test_import_room(self):
        from game.room import Room
        assert Room is not None

    def test_import_location(self):
        from game.location import Location
        assert Location is not None

    def test_import_map(self):
        from game.map import Map
        assert Map is not None

    def test_import_quest(self):
        from game.quest import Quest, QuestManager
        assert Quest is not None
        assert QuestManager is not None

    def test_import_requirements(self):
        from game.requirements import Requirement
        assert Requirement is not None

    def test_import_cutscene(self):
        from game.cutscene import CutsceneManager
        assert CutsceneManager is not None

    def test_import_ai_interpreter(self):
        from game.ai_interpreter import Intent, interpret
        assert Intent is not None
        assert interpret is not None

    def test_import_game_engine(self):
        from game.game_engine import GameEngine
        assert GameEngine is not None
