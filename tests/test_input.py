"""Tests for InputHandler."""

import pytest
from game.input.handler import InputHandler, InputType, ParsedInput


class TestInputHandler:
    """Tests for InputHandler."""
    
    @pytest.fixture
    def handler(self):
        return InputHandler()
    
    def test_quit_command(self, handler):
        """quit command is recognized."""
        result = handler.parse("quit")
        
        assert result.input_type == InputType.QUIT
        assert result.raw_text == "quit"
    
    def test_exit_command(self, handler):
        """exit command is recognized as quit."""
        result = handler.parse("exit")
        
        assert result.input_type == InputType.QUIT
    
    def test_quest_shortcut(self, handler):
        """q shows quest screen."""
        result = handler.parse("q")
        
        assert result.input_type == InputType.QUEST_SCREEN
    
    def test_quest_command(self, handler):
        """quest shows quest screen."""
        result = handler.parse("quest")
        
        assert result.input_type == InputType.QUEST_SCREEN
    
    def test_map_shortcut(self, handler):
        """m shows map screen."""
        result = handler.parse("m")
        
        assert result.input_type == InputType.MAP_SCREEN
    
    def test_map_command(self, handler):
        """map shows map screen."""
        result = handler.parse("map")
        
        assert result.input_type == InputType.MAP_SCREEN
    
    def test_save_command(self, handler):
        """save command is recognized."""
        result = handler.parse("save")
        
        assert result.input_type == InputType.SAVE
        assert result.slot_name == "autosave"
    
    def test_save_with_slot(self, handler):
        """save with slot name is recognized."""
        result = handler.parse("save mysave")
        
        assert result.input_type == InputType.SAVE
        assert result.slot_name == "mysave"
    
    def test_load_command(self, handler):
        """load command is recognized."""
        result = handler.parse("load")
        
        assert result.input_type == InputType.LOAD
        assert result.slot_name == "autosave"
    
    def test_load_with_slot(self, handler):
        """load with slot name is recognized."""
        result = handler.parse("load mysave")
        
        assert result.input_type == InputType.LOAD
        assert result.slot_name == "mysave"
    
    def test_restore_command(self, handler):
        """restore is alias for load."""
        result = handler.parse("restore")
        
        assert result.input_type == InputType.LOAD
    
    def test_game_action(self, handler):
        """Regular input is game action."""
        result = handler.parse("go north")
        
        assert result.input_type == InputType.GAME_ACTION
        assert result.raw_text == "go north"
    
    def test_empty_input(self, handler):
        """Empty input is game action."""
        result = handler.parse("")
        
        assert result.input_type == InputType.GAME_ACTION
    
    def test_whitespace_preserved(self, handler):
        """Whitespace is stripped but preserved in raw_text."""
        result = handler.parse("  look around  ")
        
        assert result.input_type == InputType.GAME_ACTION
        assert result.raw_text == "look around"
    
    def test_case_insensitive(self, handler):
        """Commands are case-insensitive."""
        result = handler.parse("QUIT")
        
        assert result.input_type == InputType.QUIT
