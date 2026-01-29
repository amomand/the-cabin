"""Input handling for The Cabin."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


class InputType(Enum):
    """Types of player input."""
    QUIT = auto()
    QUEST_SCREEN = auto()
    MAP_SCREEN = auto()
    SAVE = auto()
    LOAD = auto()
    GAME_ACTION = auto()


@dataclass
class ParsedInput:
    """Result of parsing player input."""
    input_type: InputType
    raw_text: str
    slot_name: Optional[str] = None  # For save/load


class InputHandler:
    """
    Handles parsing of player input into commands.
    
    Identifies shortcuts (quit, quest, map, save, load) before
    sending to AI interpreter.
    """
    
    # Shortcut commands
    QUIT_COMMANDS = {"quit", "exit", "q!"}
    QUEST_COMMANDS = {"q", "quest", "quests"}
    MAP_COMMANDS = {"m", "map"}
    SAVE_COMMANDS = {"save"}
    LOAD_COMMANDS = {"load", "restore"}
    
    def parse(self, user_input: str) -> ParsedInput:
        """
        Parse user input into a ParsedInput.
        
        Args:
            user_input: Raw input from the player
            
        Returns:
            ParsedInput with the identified type and raw text
        """
        text = user_input.strip()
        tokens = text.lower().split()
        
        if not tokens:
            return ParsedInput(InputType.GAME_ACTION, text)
        
        first_token = tokens[0]
        
        # Check for quit
        if first_token in self.QUIT_COMMANDS:
            return ParsedInput(InputType.QUIT, text)
        
        # Check for quest screen
        if first_token in self.QUEST_COMMANDS and len(tokens) == 1:
            return ParsedInput(InputType.QUEST_SCREEN, text)
        
        # Check for map screen
        if first_token in self.MAP_COMMANDS and len(tokens) == 1:
            return ParsedInput(InputType.MAP_SCREEN, text)
        
        # Check for save
        if first_token in self.SAVE_COMMANDS:
            slot_name = tokens[1] if len(tokens) > 1 else "autosave"
            return ParsedInput(InputType.SAVE, text, slot_name=slot_name)
        
        # Check for load
        if first_token in self.LOAD_COMMANDS:
            slot_name = tokens[1] if len(tokens) > 1 else "autosave"
            return ParsedInput(InputType.LOAD, text, slot_name=slot_name)
        
        # Default to game action
        return ParsedInput(InputType.GAME_ACTION, text)
