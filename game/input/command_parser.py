"""
Command parser for trivially obvious commands.

This parser handles ONLY:
- Movement: "go north", "n", "north", "go n"
- Inventory: "inventory", "i", "take X", "drop X", "get X"
- Observation: "look", "l", "listen"
- System: "quit", "exit", "save", "load", "help", "h"

EVERYTHING ELSE goes to the AI interpreter. When in doubt, return None.

The AI is the core experience - this parser just saves API calls for
trivially obvious commands.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, List, Dict, Set


class CommandType(Enum):
    """Types of commands the parser can recognize."""
    MOVE = auto()
    LOOK = auto()
    LISTEN = auto()
    INVENTORY = auto()
    TAKE = auto()
    DROP = auto()
    HELP = auto()
    UNKNOWN = auto()  # Must go to AI


@dataclass
class ParsedCommand:
    """Result of parsing a command."""
    command_type: CommandType
    action: str  # The normalized action name
    args: Dict[str, str]  # Arguments (e.g., direction, item name)
    confidence: float  # How confident we are (0.0-1.0)
    raw_text: str  # Original input
    
    @property
    def should_use_ai(self) -> bool:
        """Whether this should be routed to AI instead."""
        return self.command_type == CommandType.UNKNOWN or self.confidence < 0.95


# Direction mappings
DIRECTION_ALIASES: Dict[str, str] = {
    "n": "north", "north": "north",
    "s": "south", "south": "south",
    "e": "east", "east": "east",
    "w": "west", "west": "west",
    "u": "up", "up": "up",
    "d": "down", "down": "down",
    "ne": "northeast", "northeast": "northeast",
    "nw": "northwest", "northwest": "northwest",
    "se": "southeast", "southeast": "southeast",
    "sw": "southwest", "southwest": "southwest",
}

VALID_DIRECTIONS: Set[str] = set(DIRECTION_ALIASES.values())

# Movement verb aliases
MOVE_VERBS: Set[str] = {"go", "move", "walk", "head", "travel"}

# Look aliases
LOOK_ALIASES: Set[str] = {"look", "l", "examine", "x"}

# Listen aliases  
LISTEN_ALIASES: Set[str] = {"listen"}

# Inventory aliases
INVENTORY_ALIASES: Set[str] = {"inventory", "i", "inv"}

# Take aliases
TAKE_ALIASES: Set[str] = {"take", "get", "grab", "pick"}

# Drop aliases
DROP_ALIASES: Set[str] = {"drop", "put", "discard", "leave"}

# Help aliases
HELP_ALIASES: Set[str] = {"help", "h", "?", "commands"}


class CommandParser:
    """
    Parser for trivially obvious commands.
    
    Returns ParsedCommand with high confidence only for unambiguous input.
    Anything creative, ambiguous, or complex returns UNKNOWN → AI route.
    """
    
    def __init__(self, known_items: Optional[List[str]] = None) -> None:
        """
        Initialize parser.
        
        Args:
            known_items: List of known item names for validation
        """
        self.known_items = set(known_items or [])
    
    def update_known_items(self, items: List[str]) -> None:
        """Update the list of known items."""
        self.known_items = set(items)
    
    def parse(self, text: str) -> ParsedCommand:
        """
        Parse input text into a command.
        
        Returns UNKNOWN for anything ambiguous - prefer AI over false positives.
        """
        raw = text
        text = text.strip().lower()
        
        if not text:
            return self._unknown(raw)
        
        tokens = text.split()
        
        # Single token commands
        if len(tokens) == 1:
            return self._parse_single_token(tokens[0], raw)
        
        # Multi-token commands
        return self._parse_multi_token(tokens, raw)
    
    def _parse_single_token(self, token: str, raw: str) -> ParsedCommand:
        """Parse a single-word command."""
        
        # Direction shortcuts: "n", "north", etc.
        if token in DIRECTION_ALIASES:
            direction = DIRECTION_ALIASES[token]
            return ParsedCommand(
                command_type=CommandType.MOVE,
                action="move",
                args={"direction": direction},
                confidence=1.0,
                raw_text=raw
            )
        
        # Look shortcuts
        if token in LOOK_ALIASES:
            return ParsedCommand(
                command_type=CommandType.LOOK,
                action="look",
                args={},
                confidence=1.0,
                raw_text=raw
            )
        
        # Listen
        if token in LISTEN_ALIASES:
            return ParsedCommand(
                command_type=CommandType.LISTEN,
                action="listen",
                args={},
                confidence=1.0,
                raw_text=raw
            )
        
        # Inventory
        if token in INVENTORY_ALIASES:
            return ParsedCommand(
                command_type=CommandType.INVENTORY,
                action="inventory",
                args={},
                confidence=1.0,
                raw_text=raw
            )
        
        # Help
        if token in HELP_ALIASES:
            return ParsedCommand(
                command_type=CommandType.HELP,
                action="help",
                args={},
                confidence=1.0,
                raw_text=raw
            )
        
        # Unknown single word - could be creative, send to AI
        return self._unknown(raw)
    
    def _parse_multi_token(self, tokens: List[str], raw: str) -> ParsedCommand:
        """Parse multi-word commands."""
        verb = tokens[0]
        rest = tokens[1:]
        
        # Movement: "go north", "walk east", etc.
        if verb in MOVE_VERBS and len(rest) == 1:
            direction_token = rest[0]
            if direction_token in DIRECTION_ALIASES:
                return ParsedCommand(
                    command_type=CommandType.MOVE,
                    action="move",
                    args={"direction": DIRECTION_ALIASES[direction_token]},
                    confidence=1.0,
                    raw_text=raw
                )
        
        # Take: "take rope", "get stick", "grab stone"
        if verb in TAKE_ALIASES and len(rest) >= 1:
            item_name = " ".join(rest)
            # Only high confidence if item is known
            confidence = 1.0 if item_name in self.known_items else 0.8
            return ParsedCommand(
                command_type=CommandType.TAKE,
                action="take",
                args={"item": item_name},
                confidence=confidence,
                raw_text=raw
            )
        
        # Drop: "drop rope", "put down stick"
        if verb in DROP_ALIASES and len(rest) >= 1:
            item_name = " ".join(rest)
            confidence = 1.0 if item_name in self.known_items else 0.8
            return ParsedCommand(
                command_type=CommandType.DROP,
                action="drop",
                args={"item": item_name},
                confidence=confidence,
                raw_text=raw
            )
        
        # Look at something: "look at rope" - send to AI for richer response
        if verb in LOOK_ALIASES and len(rest) >= 1:
            # "look around" is just look
            if rest == ["around"]:
                return ParsedCommand(
                    command_type=CommandType.LOOK,
                    action="look",
                    args={},
                    confidence=1.0,
                    raw_text=raw
                )
            # "look at X" should go to AI for detailed description
            return self._unknown(raw)
        
        # Unknown multi-word - likely creative, send to AI
        return self._unknown(raw)
    
    def _unknown(self, raw: str) -> ParsedCommand:
        """Return an unknown command that will be routed to AI."""
        return ParsedCommand(
            command_type=CommandType.UNKNOWN,
            action="",
            args={},
            confidence=0.0,
            raw_text=raw
        )
