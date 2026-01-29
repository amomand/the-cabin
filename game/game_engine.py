from game.player import Player
from game.map import Map
from game.cutscene import CutsceneManager
from game.quests import create_quest_manager
from game.logger import log_quest_event, log_game_action
from game.actions import create_default_registry, ActionContext
import os
import sys
import tty
import termios
import time
from game.ai_interpreter import interpret, ALLOWED_ACTIONS
from typing import Optional


class GameEngine:
    def __init__(
        self,
        player: Optional[Player] = None,
        map: Optional[Map] = None,
        cutscene_manager: Optional[CutsceneManager] = None,
        quest_manager = None,
        action_registry = None,
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
        self._last_feedback: str = ""
        self._last_room_id: str = None
        self._is_first_render: bool = True

    @property
    def items(self):
        """Access items through map (single source of truth)."""
        return self.map.items

    @property
    def wildlife(self):
        """Access wildlife through map (single source of truth)."""
        return self.map.wildlife

    def run(self):
        # Show intro sequence first
        self._show_intro()
        
        while self.running:
            self.render()

            user_input = input("> ")
            self.handle_user_input(user_input)

    def handle_user_input(self, user_input):
        tokens = user_input.strip().lower().split()
        if len(tokens) == 1 and tokens[0] == "quit":
            self.running = False
        elif len(tokens) == 1 and tokens[0] in ["q", "quest"]:
            self._show_quest_screen()
            return
        elif len(tokens) == 1 and tokens[0] in ["m", "map"]:
            self._show_map()
            return
        else:
            # AI interpreter route
            room = self.map.current_room
            context = {
                "room_name": room.name,
                "exits": list(room.exits.keys()),
                "room_items": [item.name for item in room.items],
                "room_wildlife": [animal.name for animal in room.wildlife],
                "inventory": self.player.get_inventory_names(),
                "world_flags": self.map.world_state.to_dict(),
                "allowed_actions": list(ALLOWED_ACTIONS),
            }

            intent = interpret(user_input, context)
            
            # Apply AI-suggested effects (fear/health deltas)
            self._apply_effects(intent)
            
            # Execute action via registry
            result = self.action_registry.execute(
                intent.action, self.player, self.map, intent
            )
            
            if result is None:
                # Unknown action - use fallback
                self._last_feedback = intent.reply or "You start, then think better of it. The cold in your chest makes you careful."
                return
            
            # Set feedback from action result
            self._last_feedback = result.feedback
            
            # Handle post-action events
            self._handle_action_events(result, intent)

    def _apply_effects(self, intent) -> None:
        effects = getattr(intent, "effects", None) or {}
        # Small, clamped deltas
        fear_delta = int(effects.get("fear", 0))
        health_delta = int(effects.get("health", 0))
        fear_delta = max(-2, min(2, fear_delta))
        health_delta = max(-2, min(2, health_delta))

        self.player.fear = max(0, min(100, self.player.fear + fear_delta))
        self.player.health = max(0, min(100, self.player.health + health_delta))

        # Inventory changes are authoritative here; only allow remove if owned
        inventory_remove = [str(x) for x in effects.get("inventory_remove", [])]
        for item_name in inventory_remove:
            removed_item = self.player.remove_item(item_name)
            if removed_item:
                # If the item was removed from inventory, we could add it back to the current room
                # For now, we'll just remove it
                pass

        # Allow add only if item was already known (either already owned or visible)
        inventory_add = [str(x) for x in effects.get("inventory_add", [])]
        room = self.map.current_room
        for item_name in inventory_add:
            # Check if item exists in the game and is in the current room
            if item_name in self.items and room.has_item(item_name):
                item = room.remove_item(item_name)
                if item and item.is_carryable():
                    self.player.add_item(item)

    def _handle_action_events(self, result, intent) -> None:
        """Handle events emitted by actions."""
        state_changes = result.state_changes or {}
        
        for event in result.events:
            if event == "player_moved":
                # Check for quest triggers after movement
                self._check_quest_triggers("location", {"room_id": self.map.current_room.id})
                
                # Check for cutscenes
                from_room_id = state_changes.get("from_room_id")
                to_room_id = state_changes.get("to_room_id")
                if from_room_id and to_room_id:
                    self.cutscene_manager.check_and_play_cutscenes(
                        from_room_id=from_room_id,
                        to_room_id=to_room_id,
                        player=self.player,
                        world_state=self.map.world_state
                    )
            
            elif event == "fuel_gathered":
                self._check_quest_updates("fuel_gathered", {"action": "take_firewood"}, self.player, self.map.world_state)
            
            elif event == "power_restored":
                self._check_quest_triggers("action", {"action": "turn_on_lights"})
                self._check_quest_updates("power_restored", {"action": "use_circuit_breaker"}, self.player, self.map.world_state)
            
            elif event == "fire_lit":
                self._check_quest_triggers("action", {"action": "light_fire"})
                self._check_quest_updates("fire_success", {"action": "light_fire", "success": True}, self.player, self.map.world_state)
                self._check_quest_completion()
            
            elif event == "fire_no_fuel":
                self._check_quest_triggers("action", {"action": "light_fire"})
                self._check_quest_updates("fire_no_fuel", {"action": "light_fire"}, self.player, self.map.world_state)
            
            elif event == "use_light_switch_no_power":
                self._check_quest_triggers("action", {"action": "turn_on_lights"})
            
            elif event == "use_fireplace_no_fuel":
                self._check_quest_triggers("action", {"action": "use_fireplace"})
            
            elif event == "wildlife_attack":
                # Apply damage from wildlife attack
                health_damage = state_changes.get("health_damage", 0)
                fear_increase = state_changes.get("fear_increase", 0)
                self.player.health = max(0, self.player.health - health_damage)
                self.player.fear = min(100, self.player.fear + fear_increase)
            
            elif event == "thrown_into_darkness":
                # Fear increase from throwing into darkness
                fear_increase = state_changes.get("fear_increase", 5)
                self.player.fear = min(100, self.player.fear + fear_increase)

    def _check_quest_triggers(self, trigger_type: str, trigger_data: dict) -> None:
        """Check if any quest should be triggered."""
        triggered_quest = self.quest_manager.check_triggers(trigger_type, trigger_data, self.player, self.map.world_state)
        if triggered_quest:
            self.quest_manager.activate_quest(triggered_quest)
            log_quest_event("quest_triggered", {
                "quest_id": triggered_quest.quest_id,
                "trigger_type": trigger_type,
                "trigger_data": trigger_data
            })
            self._show_quest_screen(triggered_quest.opening_text)

    def _check_quest_updates(self, event_name: str, event_data: dict, player, world_state) -> None:
        """Check if any active quest should be updated."""
        update_text = self.quest_manager.check_updates(event_name, event_data, player, world_state)
        if update_text:
            log_quest_event("quest_updated", {
                "event_name": event_name,
                "event_data": event_data,
                "update_text": update_text
            })
            self._last_feedback = f"Quest Update: {update_text}"

    def _check_quest_completion(self) -> None:
        """Check if the active quest is completed."""
        completion_text = self.quest_manager.check_completion(self.player, self.map.world_state)
        if completion_text:
            log_quest_event("quest_completed", {
                "completion_text": completion_text,
                "world_state": self.map.world_state.to_dict()
            })
            self._last_feedback = f"Quest Complete: {completion_text}"

    def _show_quest_screen(self, custom_text: str = None) -> None:
        """Show the quest screen."""
        self.clear_terminal()
        
        # Show narrative text
        print("*You take a breath and focus...*")
        print()
        
        if custom_text:
            print(custom_text)
        else:
            print(self.quest_manager.get_active_quest_display())
        
        print("\nPress any key to continue...")
        
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
                input("Press Enter to continue...")
            except EOFError:
                pass  # Handle EOF gracefully
        
        # After closing quest screen, show room description again
        self._last_room_id = None  # Force room re-render

    def _show_map(self) -> None:
        """Show the ASCII map of visited areas."""
        self.clear_terminal()
        
        # Show narrative text
        print("*You close your eyes and retrace your steps…*")
        print()
        
        # Get visited rooms and display map
        visited_rooms = self.map.get_visited_rooms()
        map_display = self.map.display_map(visited_rooms)
        print(map_display)
        
        print("\nPress any key to continue...")
        
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
                input("Press Enter to continue...")
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
            "You shouldn't have come back.",
            "It's awake.",
            "It always has been."
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
                input("Press Enter to continue...")
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
            print(self._last_feedback)
            print()
            self._last_feedback = ""

        # Status + prompt (always)
        print(f"Health: {self.player.health}    Fear: {self.player.fear}\n")
        print("What would you like to do?")

# The Lyer watches silently. Nothing escapes its notice.
