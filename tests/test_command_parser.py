"""Tests for CommandParser."""

import pytest
from game.input.command_parser import CommandParser, CommandType, ParsedCommand


class TestCommandParser:
    """Tests for CommandParser."""
    
    @pytest.fixture
    def parser(self):
        return CommandParser(known_items=["rope", "stick", "stone", "matches"])
    
    # --- Movement tests ---
    
    def test_direction_shortcut_n(self, parser):
        """'n' parses to move north."""
        result = parser.parse("n")
        
        assert result.command_type == CommandType.MOVE
        assert result.action == "move"
        assert result.args["direction"] == "north"
        assert result.confidence == 1.0
    
    def test_direction_full_word(self, parser):
        """'north' parses to move north."""
        result = parser.parse("north")
        
        assert result.command_type == CommandType.MOVE
        assert result.args["direction"] == "north"
    
    def test_go_direction(self, parser):
        """'go east' parses to move east."""
        result = parser.parse("go east")
        
        assert result.command_type == CommandType.MOVE
        assert result.args["direction"] == "east"
    
    def test_walk_direction(self, parser):
        """'walk south' parses to move south."""
        result = parser.parse("walk south")
        
        assert result.command_type == CommandType.MOVE
        assert result.args["direction"] == "south"
    
    def test_all_directions(self, parser):
        """All direction shortcuts work."""
        shortcuts = ["n", "s", "e", "w", "u", "d", "ne", "nw", "se", "sw"]
        for shortcut in shortcuts:
            result = parser.parse(shortcut)
            assert result.command_type == CommandType.MOVE
            assert result.confidence == 1.0
    
    # --- Look/Listen tests ---
    
    def test_look(self, parser):
        """'look' parses correctly."""
        result = parser.parse("look")
        
        assert result.command_type == CommandType.LOOK
        assert result.action == "look"
        assert result.confidence == 1.0
    
    def test_look_shortcut(self, parser):
        """'l' parses to look."""
        result = parser.parse("l")
        
        assert result.command_type == CommandType.LOOK
    
    def test_look_around(self, parser):
        """'look around' parses to look."""
        result = parser.parse("look around")
        
        assert result.command_type == CommandType.LOOK
        assert result.confidence == 1.0
    
    def test_look_at_goes_to_ai(self, parser):
        """'look at rope' should go to AI for detailed description."""
        result = parser.parse("look at rope")
        
        assert result.should_use_ai
    
    def test_listen(self, parser):
        """'listen' parses correctly."""
        result = parser.parse("listen")
        
        assert result.command_type == CommandType.LISTEN
        assert result.action == "listen"
    
    # --- Inventory tests ---
    
    def test_inventory(self, parser):
        """'inventory' parses correctly."""
        result = parser.parse("inventory")
        
        assert result.command_type == CommandType.INVENTORY
        assert result.action == "inventory"
    
    def test_inventory_shortcut(self, parser):
        """'i' parses to inventory."""
        result = parser.parse("i")
        
        assert result.command_type == CommandType.INVENTORY
    
    # --- Take/Drop tests ---
    
    def test_take_known_item(self, parser):
        """'take rope' with known item has high confidence."""
        result = parser.parse("take rope")
        
        assert result.command_type == CommandType.TAKE
        assert result.action == "take"
        assert result.args["item"] == "rope"
        assert result.confidence == 1.0
    
    def test_take_unknown_item(self, parser):
        """'take sword' with unknown item has lower confidence."""
        result = parser.parse("take sword")
        
        assert result.command_type == CommandType.TAKE
        assert result.args["item"] == "sword"
        assert result.confidence < 1.0  # Lower confidence for unknown items
    
    def test_get_item(self, parser):
        """'get stick' parses as take."""
        result = parser.parse("get stick")
        
        assert result.command_type == CommandType.TAKE
        assert result.args["item"] == "stick"
    
    def test_drop_item(self, parser):
        """'drop stone' parses correctly."""
        result = parser.parse("drop stone")
        
        assert result.command_type == CommandType.DROP
        assert result.action == "drop"
        assert result.args["item"] == "stone"
    
    # --- Help tests ---
    
    def test_help(self, parser):
        """'help' parses correctly."""
        result = parser.parse("help")
        
        assert result.command_type == CommandType.HELP
        assert result.action == "help"
    
    def test_help_shortcut(self, parser):
        """'h' parses to help."""
        result = parser.parse("h")
        
        assert result.command_type == CommandType.HELP
    
    def test_question_mark(self, parser):
        """'?' parses to help."""
        result = parser.parse("?")
        
        assert result.command_type == CommandType.HELP
    
    # --- Unknown/AI route tests ---
    
    def test_creative_input_goes_to_ai(self, parser):
        """Creative input should be marked for AI."""
        result = parser.parse("do a handstand")
        
        assert result.command_type == CommandType.UNKNOWN
        assert result.should_use_ai
    
    def test_empty_input_goes_to_ai(self, parser):
        """Empty input goes to AI."""
        result = parser.parse("")
        
        assert result.should_use_ai
    
    def test_complex_sentence_goes_to_ai(self, parser):
        """Complex sentences go to AI."""
        result = parser.parse("I want to carefully examine the rope while listening for sounds")
        
        assert result.should_use_ai
    
    def test_impossible_action_goes_to_ai(self, parser):
        """Impossible actions go to AI for diegetic response."""
        result = parser.parse("fly into the sky")
        
        assert result.should_use_ai
    
    def test_roleplay_input_goes_to_ai(self, parser):
        """Roleplay input goes to AI."""
        result = parser.parse("breathe deeply and steady my nerves")
        
        assert result.should_use_ai
    
    # --- Edge cases ---
    
    def test_case_insensitive(self, parser):
        """Commands are case-insensitive."""
        result = parser.parse("LOOK")
        
        assert result.command_type == CommandType.LOOK
    
    def test_whitespace_handling(self, parser):
        """Whitespace is handled correctly."""
        result = parser.parse("   north   ")
        
        assert result.command_type == CommandType.MOVE
        assert result.args["direction"] == "north"
    
    def test_update_known_items(self, parser):
        """Known items can be updated."""
        parser.update_known_items(["lantern", "key"])
        
        result1 = parser.parse("take lantern")
        result2 = parser.parse("take rope")  # No longer known
        
        assert result1.confidence == 1.0
        assert result2.confidence < 1.0
    
    def test_should_use_ai_low_confidence(self, parser):
        """Low confidence triggers AI route."""
        result = parser.parse("take mysterious_artifact")  # Unknown item
        
        assert result.should_use_ai  # confidence < 0.95
