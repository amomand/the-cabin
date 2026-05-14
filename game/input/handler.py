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
    LIST_SAVES = auto()
    DELETE_SAVE = auto()
    GAME_ACTION = auto()


@dataclass
class ParsedInput:
    """Result of parsing player input."""
    input_type: InputType
    raw_text: str
    slot_name: Optional[str] = None  # For save/load/delete


class InputHandler:
    """
    Handles parsing of player input into commands.

    Identifies shortcuts (quit, quest, map, save, load, saves,
    delete save) before sending to AI interpreter.
    """

    # Shortcut commands
    QUIT_COMMANDS = {"quit", "q!"}
    EXIT_COMMAND = "exit"
    QUEST_COMMANDS = {"q", "quest", "quests"}
    MAP_COMMANDS = {"m", "map"}
    SAVE_COMMANDS = {"save"}
    LOAD_COMMANDS = {"load", "restore"}
    LIST_SAVES_COMMANDS = {"saves"}
    DELETE_SAVE_COMMANDS = {"delete", "remove"}

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
        if first_token in self.QUIT_COMMANDS or (
            first_token == self.EXIT_COMMAND and len(tokens) == 1
        ):
            return ParsedInput(InputType.QUIT, text)

        # Check for quest screen
        if first_token in self.QUEST_COMMANDS and len(tokens) == 1:
            return ParsedInput(InputType.QUEST_SCREEN, text)

        # Check for map screen
        if first_token in self.MAP_COMMANDS and len(tokens) == 1:
            return ParsedInput(InputType.MAP_SCREEN, text)

        # Check for `list saves` (two-word form of `saves`).
        if (
            first_token == "list"
            and len(tokens) == 2
            and tokens[1] in self.LIST_SAVES_COMMANDS
        ):
            return ParsedInput(InputType.LIST_SAVES, text)

        # Check for `saves` (list all save slots).
        if first_token in self.LIST_SAVES_COMMANDS and len(tokens) == 1:
            return ParsedInput(InputType.LIST_SAVES, text)

        # Check for `delete save NAME` / `remove save NAME`.
        # Only treated as a system command when the second token is "save";
        # other "delete X" inputs fall through to the AI interpreter.
        if (
            first_token in self.DELETE_SAVE_COMMANDS
            and len(tokens) >= 2
            and tokens[1] == "save"
        ):
            slot_name = tokens[2] if len(tokens) > 2 else "autosave"
            return ParsedInput(InputType.DELETE_SAVE, text, slot_name=slot_name)

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
