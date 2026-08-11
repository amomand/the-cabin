from game.player import Player
from game.map import Map
from game.cutscene import CutsceneManager
from game.config import get_config
from game.overlay_cues import (
    MAP_SCREEN_ENTER,
    MAP_SCREEN_EXIT,
    QUEST_SCREEN_ENTER,
    QUEST_SCREEN_EXIT,
)
from game.quests import create_quest_manager
from game.logger import log_quest_event
from game.actions import create_default_registry
from game.events import EventBus
from game.events.listeners.quest_listener import QuestEventListener
from game.events.listeners.cutscene_listener import CutsceneEventListener
from game.persistence import SaveManager
from game.input.handler import InputHandler, InputType
import os
import sys
import tty
import termios
from pathlib import Path
from game import save_commands
from game.ai_context import build_ai_context
from game.turn import apply_effects, handle_action_events, take_turn
from game.death import (
    DEATH_LINE_FADE,
    DEATH_LINE_FEAR_COLLAPSE,
    death_line_for,
)
from game.ending import ending_line_for, ending_reached
from typing import Optional


class GameEngine:
    def __init__(
        self,
        player: Optional[Player] = None,
        map: Optional[Map] = None,
        cutscene_manager: Optional[CutsceneManager] = None,
        quest_manager = None,
        action_registry = None,
        event_bus: Optional[EventBus] = None,
    ):
        """
        Initialize the game engine.
        
        All parameters are optional and will be created with defaults if not provided.
        This enables dependency injection for testing.
        """
        self.running = True
        self.player = player if player is not None else Player()
        self.map = map if map is not None else Map()
        self.cutscene_manager = cutscene_manager if cutscene_manager is not None else CutsceneManager()
        self.quest_manager = quest_manager if quest_manager is not None else create_quest_manager()
        self.action_registry = action_registry if action_registry is not None else create_default_registry()
        self.event_bus = event_bus if event_bus is not None else EventBus()
        self.save_manager = SaveManager(save_dir=Path(get_config().save_directory))
        self.input_handler = InputHandler()
        self._last_feedback: str = ""
        self._last_room_id: str = None
        self._is_first_render: bool = True
        
        # Set up event listeners
        self._setup_event_listeners()

    def _setup_event_listeners(self) -> None:
        """Set up event listeners for cutscenes and quests.

        Cutscenes register first, so they run first on a shared event. A
        cutscene sets the scene the quest then reacts to: walking into the cold
        cabin plays the entry scene, and only after that does the quest say the
        lights don't respond. Registered the other way round, the quest spoke
        about a room the player had not yet been told she had stepped into.

        `WebGameSession._setup_event_listeners` keeps the same order for the
        same reason. The two must not drift.
        """
        # Cutscene listener
        self._cutscene_listener = CutsceneEventListener(
            cutscene_manager=self.cutscene_manager,
            get_player=lambda: self.player,
            get_world_state=lambda: self.map.world_state,
        )
        self._cutscene_listener.register(self.event_bus)

        # Quest listener
        self._quest_listener = QuestEventListener(
            quest_manager=self.quest_manager,
            get_player=lambda: self.player,
            get_world_state=lambda: self.map.world_state,
            on_quest_triggered=self._on_quest_triggered,
            on_quest_updated=self._on_quest_updated,
            on_quest_completed=self._on_quest_completed,
        )
        self._quest_listener.register(self.event_bus)
    
    def _on_quest_triggered(self, opening_text: str) -> None:
        """Callback when a quest is triggered."""
        self._show_quest_screen(opening_text)
    
    def _on_quest_updated(self, update_text: str) -> None:
        """Callback when a quest is updated."""
        self._last_feedback = update_text
    
    def _on_quest_completed(self, completion_text: str) -> None:
        """Callback when a quest is completed."""
        log_quest_event("quest_completed", {
            "completion_text": completion_text,
            "world_state": self.map.world_state.to_dict()
        })
        self._last_feedback = completion_text

    @property
    def items(self):
        """Access items through map (single source of truth)."""
        return self.map.items

    def run(self):
        # Show intro sequence first
        self._show_intro()
        
        while self.running:
            self.render()

            user_input = input("> ")
            self.handle_user_input(user_input)

    def handle_user_input(self, user_input):
        # A blank command is not a turn — the loop re-renders the prompt
        # rather than sending empty text through the interpreter.
        if not user_input.strip():
            return

        parsed = self.input_handler.parse(user_input)
        
        if parsed.input_type == InputType.QUIT:
            self.running = False
            return
        elif parsed.input_type == InputType.QUEST_SCREEN:
            self._show_quest_screen()
            return
        elif parsed.input_type == InputType.MAP_SCREEN:
            self._show_map()
            return
        elif parsed.input_type == InputType.SAVE:
            self._save_game(parsed.slot_name)
            return
        elif parsed.input_type == InputType.LOAD:
            self._load_game(parsed.slot_name)
            # A loaded save may already be at the death threshold, or the
            # story may already be finished (stayed, or the coda complete).
            if not self._check_death():
                self._check_story_end()
            return
        elif parsed.input_type == InputType.LIST_SAVES:
            self._list_saves()
            return
        elif parsed.input_type == InputType.DELETE_SAVE:
            self._delete_save(parsed.slot_name)
            return
        
        # Game action: shared turn core, one implementation for both surfaces
        take_turn(
            user_input,
            player=self.player,
            game_map=self.map,
            quest_manager=self.quest_manager,
            action_registry=self.action_registry,
            event_bus=self.event_bus,
            set_feedback=self._set_feedback,
        )

        if not self._check_death():
            self._check_story_end()

    def _check_story_end(self) -> bool:
        """End the run when the story has finished (stayed, or coda complete).

        Mirrors `_check_death`; the closing lines come from
        `game.ending.ending_line_for` so terminal and web stay in sync.
        """
        line = ending_line_for(self.map.world_state)
        if not ending_reached(self.map.world_state):
            return False

        if self._last_feedback:
            print()
            print(self._last_feedback)
            self._last_feedback = ""

        if line is not None:
            print()
            print(line)
            print()
        self.running = False
        return True

    def _check_death(self) -> bool:
        """End the run when fear or health crosses the threshold.

        Returns True if death fired. Precedence and lines come from
        `game.death.death_line_for` so terminal and web surfaces stay
        in sync.
        """
        line = death_line_for(self.player)
        if line is None:
            return False

        # Flush any pending action feedback so the closing line lands last.
        if self._last_feedback:
            print()
            print(self._last_feedback)
            self._last_feedback = ""

        print()
        print(line)
        print()
        self.running = False
        return True
    
    def _set_feedback(self, text: str) -> None:
        """Feedback channel handed to the shared turn core."""
        self._last_feedback = text

    def _save_game(self, slot_name: str) -> None:
        """Save the current game state."""
        self._last_feedback = save_commands.save_game(
            self.save_manager,
            slot_name,
            player=self.player,
            game_map=self.map,
            quest_manager=self.quest_manager,
            cutscene_manager=self.cutscene_manager,
        )

    def _list_saves(self) -> None:
        """Show the player every save slot they have on disk."""
        self._last_feedback = save_commands.list_saves(self.save_manager)

    def _delete_save(self, slot_name: str) -> None:
        """Delete a save slot, if it exists."""
        self._last_feedback = save_commands.delete_save(self.save_manager, slot_name)

    def _build_ai_context(self):
        """Build the context payload sent to the AI interpreter."""
        return build_ai_context(self.player, self.map, self.quest_manager)

    def _load_game(self, slot_name: str) -> None:
        """Load a game from a save slot."""
        outcome = save_commands.load_game(
            self.save_manager,
            slot_name,
            player=self.player,
            game_map=self.map,
            quest_manager=self.quest_manager,
            cutscene_manager=self.cutscene_manager,
        )
        self._last_feedback = outcome.feedback
        if outcome.loaded:
            # Force room re-render
            self._last_room_id = None

    def _apply_effects(self, intent, skip_inventory: bool = False) -> None:
        """Apply an intent's effects. Thin wrapper over the shared turn core.

        Retained as a per-surface seam for tests, which is what lets the
        parity suite compare the two surfaces; production goes through
        `turn.take_turn` directly.
        """
        apply_effects(intent, self.player, self.map, skip_inventory=skip_inventory)

    def _handle_action_events(self, result, intent=None) -> None:
        """Emit an action result's events. Thin wrapper over the shared turn core.

        Retained as a per-surface seam for tests, which is what lets the
        parity suite compare the two surfaces; production goes through
        `turn.take_turn` directly.
        """
        handle_action_events(result, self.player, self.map, self.event_bus)

    def _show_quest_screen(self, custom_text: str = None) -> None:
        """Show the quest screen."""
        self.clear_terminal()
        
        # Show narrative text
        print(QUEST_SCREEN_ENTER)
        print()
        
        if custom_text:
            print(custom_text)
        else:
            print(self.quest_manager.get_active_quest_display())
        
        print("\n" + QUEST_SCREEN_EXIT)
        
        # Wait for any key press with error handling
        try:
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            tty.setraw(sys.stdin.fileno())
            sys.stdin.read(1)
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        except (termios.error, OSError, EOFError):
            # Fallback for non-interactive terminals or compatibility issues
            try:
                input("")
            except EOFError:
                pass  # Handle EOF gracefully
        
        # After closing quest screen, show room description again
        self._last_room_id = None  # Force room re-render

    def _show_map(self) -> None:
        """Show the ASCII map of visited areas."""
        self.clear_terminal()
        
        # Show narrative text
        print(MAP_SCREEN_ENTER)
        print()
        
        # Get visited rooms and display map
        visited_rooms = self.map.get_visited_rooms()
        map_display = self.map.display_map(visited_rooms)
        print(map_display)
        
        print("\n" + MAP_SCREEN_EXIT)
        
        # Wait for any key press with error handling
        try:
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            tty.setraw(sys.stdin.fileno())
            sys.stdin.read(1)
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        except (termios.error, OSError, EOFError):
            # Fallback for non-interactive terminals or compatibility issues
            try:
                input("")
            except EOFError:
                pass  # Handle EOF gracefully
        
        # After closing map, show room description again
        self._last_room_id = None  # Force room re-render

    @staticmethod
    def clear_terminal():
        os.system('cls' if os.name == 'nt' else 'clear')

    def _show_intro(self):
        """Display the intro text and wait for player input."""
        self.clear_terminal()
        
        intro_text = [
            "At ten past four, Nika's shop was still lit.",
            "You kept your eyes on the junction and drove through."
        ]
        
        # Display all lines at once for atmospheric effect
        for line in intro_text:
            print(line)
        
        print()  # Add blank line for better cursor positioning
        
        # Wait for any key press without instruction
        
        # Save terminal settings with error handling
        try:
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            # Set terminal to raw mode
            tty.setraw(sys.stdin.fileno())
            # Wait for any key
            sys.stdin.read(1)
            # Restore terminal settings
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        except (termios.error, OSError, EOFError):
            # Fallback for non-interactive terminals or compatibility issues
            try:
                input("")
            except EOFError:
                pass  # Handle EOF gracefully

    def render(self):
        room = self.map.current_room
        room_changed = room.id != self._last_room_id or self._is_first_render

        if room_changed:
            self.clear_terminal()
            self._last_room_id = room.id
            self._is_first_render = False
            description = room.get_description(self.player, self.map.world_state)
            # Header + room description on room change only
            print(f"{room.name}\n" + ("-" * len(room.name)))
            print(description)
            print()

        # Feedback (one-shot) - only if there's feedback to show
        if self._last_feedback:
            if not room_changed:
                print()
            print(self._last_feedback)
            print()
            self._last_feedback = ""

        # Status + prompt (always)
        print(f"Health: {self.player.health}    Fear: {self.player.fear}\n")
        print("What would you like to do?")

# The Lyer watches silently. Nothing escapes its notice.
