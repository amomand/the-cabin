from game.player import Player
from game.map import Map
from game.cutscene import CutsceneManager
from game.quests import create_quest_manager
from game.logger import log_quest_event, log_game_action
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
            # Show quest screen
            self._show_quest_screen()
            return
        elif len(tokens) == 1 and tokens[0] in ["m", "map"]:
            # Show map
            self._show_map()
            return
        else:
            # AI interpreter route
            room = self.map.current_room
            context = {
                "room_name": room.name,
                "exits": list(room.exits.keys()),
                "room_items": [item.name for item in room.items],  # Items in current room
                "room_wildlife": [animal.name for animal in room.wildlife],  # Wildlife in current room
                "inventory": self.player.get_inventory_names(),  # Items in player inventory
                "world_flags": dict(self.map.world_state),
                "allowed_actions": list(ALLOWED_ACTIONS),
            }

            intent = interpret(user_input, context)

            if intent.action == "move":
                direction = intent.args.get("direction")
                if not direction:
                    self._last_feedback = "You angle your body and stop. Where?"
                    return
                
                # Store current room ID before moving
                from_room_id = self.map.current_room.id
                
                moved, message = self.map.move(direction, self.player)
                if moved:
                    # Check for quest triggers after successful movement
                    self._check_quest_triggers("location", {"room_id": self.map.current_room.id})
                    
                    # Check for cut-scenes after successful movement
                    to_room_id = self.map.current_room.id
                    cutscene_played = self.cutscene_manager.check_and_play_cutscenes(
                        from_room_id=from_room_id,
                        to_room_id=to_room_id,
                        player=self.player,
                        world_state=self.map.world_state
                    )
                    
                    # Apply any tiny effects but suppress AI reply during movement to avoid contradictory messages
                    self._apply_effects(intent)
                    self._last_feedback = ""  # No AI message during movement - let room description speak for itself
                else:
                    # If AI guessed a non-existent exit, keep it gentle and in-world
                    self._apply_effects(intent)
                    self._last_feedback = intent.reply or message or "You test that way. The path isn't there."
            elif intent.action == "look":
                self._apply_effects(intent)
                # If AI provided a reply, use it; otherwise combine room description with items and visible wildlife
                if intent.reply:
                    self._last_feedback = intent.reply
                else:
                    base_description = room.get_description(self.player, self.map.world_state)
                    items_description = room.get_items_description()
                    
                    # Add visible wildlife descriptions
                    visible_wildlife = room.get_visible_wildlife()
                    wildlife_description = ""
                    if visible_wildlife:
                        wildlife_descriptions = [animal.visual_description for animal in visible_wildlife]
                        wildlife_description = " " + " ".join(wildlife_descriptions)
                    
                    # Combine all descriptions
                    full_description = base_description
                    if items_description:
                        full_description += items_description
                    if wildlife_description:
                        full_description += wildlife_description
                    
                    self._last_feedback = full_description
            elif intent.action == "listen":
                self._apply_effects(intent)
                # If AI provided a reply, use it; otherwise describe wildlife sounds
                if intent.reply:
                    self._last_feedback = intent.reply
                else:
                    audible_wildlife = room.get_audible_wildlife()
                    if audible_wildlife:
                        sound_descriptions = [animal.sound_description for animal in audible_wildlife]
                        self._last_feedback = " ".join(sound_descriptions)
                    else:
                        self._last_feedback = "You listen carefully, but hear only the wind through the trees."
            elif intent.action == "inventory":
                self._apply_effects(intent)
                if intent.reply:
                    self._last_feedback = intent.reply
                else:
                    if self.player.inventory:
                        items = ", ".join(item.name for item in self.player.inventory)
                        self._last_feedback = f"You check your bag: {items}."
                    else:
                        self._last_feedback = "You check your bag. Just air and lint."
            elif intent.action == "take":
                self._apply_effects(intent)
                item_name = intent.args.get("item")
                if not item_name:
                    self._last_feedback = intent.reply or "Take what?"
                    return
                
                # Try to take the item from the room
                item = room.remove_item(item_name)
                if item and item.is_carryable():
                    self.player.add_item(item)
                    
                    # Check for quest updates when taking firewood
                    if item.name.lower() == "firewood":
                        self._check_quest_updates("fuel_gathered", {"action": "take_firewood"}, self.player, self.map.world_state)
                    
                    self._last_feedback = intent.reply or f"You pick up the {item.name}. {item.name.title()} added to inventory."
                elif item and not item.is_carryable():
                    # Put the item back in the room
                    room.add_item(item)
                    self._last_feedback = intent.reply or f"That {item.name} can't be picked up."
                else:
                    # Clean the item name for better error messages
                    clean_name = room._clean_item_name(item_name)
                    self._last_feedback = intent.reply or f"There's no {clean_name} here to pick up."
            elif intent.action == "throw":
                self._apply_effects(intent)
                item_name = intent.args.get("item")
                target_name = intent.args.get("target")
                
                if not item_name:
                    self._last_feedback = intent.reply or "Throw what?"
                    return
                
                # Check if player has the item in inventory
                item = self.player.get_item(item_name)
                if not item:
                    clean_name = self.player._clean_item_name(item_name)
                    self._last_feedback = intent.reply or f"You don't have a {clean_name} to throw."
                    return
                
                if not item.is_throwable():
                    self._last_feedback = intent.reply or f"The {item.name} isn't something you can throw."
                    return
                
                # Remove item from inventory
                self.player.remove_item(item_name)
                
                # If throwing at a specific target (wildlife)
                if target_name and room.has_wildlife(target_name):
                    animal = room.get_wildlife(target_name)
                    if animal:
                        result = animal.provoke()
                        
                        if result["action"] == "attack":
                            # Animal attacks
                            self.player.health = max(0, self.player.health - result["health_damage"])
                            self.player.fear = min(100, self.player.fear + result["fear_increase"])
                            self._last_feedback = result["message"]
                        elif result["action"] in ["flee", "wander"]:
                            # Animal leaves the room
                            if result["remove_from_room"]:
                                room.remove_wildlife(target_name)
                            self._last_feedback = result["message"]
                        else:
                            # Animal ignores
                            self._last_feedback = result["message"]
                    else:
                        self._last_feedback = f"You throw the {item.name} at the {target_name}, but miss."
                else:
                    # Throwing into darkness (no specific target)
                    if intent.reply:
                        self._last_feedback = intent.reply
                    else:
                        self._last_feedback = f"The {item.name} flies into the dark. You hear a dull thunk in the distance... and something else."
                        # Increase fear for throwing into darkness
                        self.player.fear = min(100, self.player.fear + 5)
            elif intent.action == "drop":
                self._apply_effects(intent)
                item_name = intent.args.get("item")
                if not item_name:
                    self._last_feedback = intent.reply or "Drop what?"
                    return

                item = self.player.remove_item(item_name)
                if not item:
                    clean_name = self.player._clean_item_name(item_name)
                    self._last_feedback = intent.reply or f"You don't have a {clean_name} to drop."
                    return

                room.add_item(item)
                self._last_feedback = intent.reply or f"You set the {item.name} down."
            elif intent.action == "use_circuit_breaker":
                self._apply_effects(intent)
                # Check if circuit breaker is in the current room
                room = self.map.current_room
                if room.has_item("circuit breaker"):
                    # Restore power
                    self.map.world_state["has_power"] = True
                    self._check_quest_triggers("action", {"action": "turn_on_lights"})
                    self._check_quest_updates("power_restored", {"action": "use_circuit_breaker"}, self.player, self.map.world_state)
                    self._last_feedback = intent.reply or "With a satisfying thunk, the circuit breaker clicks into place. Power hums through the cabin."
                else:
                    self._last_feedback = intent.reply or "There's no circuit breaker here to use."
                    
            elif intent.action == "turn_on_lights":
                self._apply_effects(intent)
                room = self.map.current_room
                if not room.has_item("light switch"):
                    self._last_feedback = intent.reply or "There's no light switch here."
                elif self.map.world_state.get("has_power", False):
                    self._last_feedback = intent.reply or "The lights flicker on, filling the cabin with warm illumination."
                else:
                    # No power - trigger quest if not already active
                    self._check_quest_triggers("action", {"action": "turn_on_lights"})
                    self._last_feedback = intent.reply or "The light switch is unresponsive; the room remains shrouded in darkness."
                    
            elif intent.action == "light":
                self._apply_effects(intent)
                target = intent.args.get("target", "").lower()
                
                if "fire" in target or "fireplace" in target:
                    if self.player.has_item("firewood"):
                        if self.player.has_item("matches"):
                            self.map.world_state["fire_lit"] = True
                            self._check_quest_updates("fire_success", {"action": "light_fire", "success": True}, self.player, self.map.world_state)
                            self._check_quest_completion()
                            self._last_feedback = intent.reply or "The matches catch and the firewood ignites. Warmth spreads through the cabin."
                        else:
                            self._last_feedback = intent.reply or "You need matches to light the fire."
                    else:
                        # No fuel - trigger quest if not already active
                        self._check_quest_triggers("action", {"action": "use_fireplace"})
                        self._last_feedback = intent.reply or "You can't light a fire without kindling or fuel."
                else:
                    self._last_feedback = intent.reply or f"You can't light {target}."
                    
            elif intent.action == "use":
                self._apply_effects(intent)
                item_name = intent.args.get("item")
                if not item_name:
                    self._last_feedback = intent.reply or "Use what?"
                    return
                
                # Check if player has the item
                item = self.player.get_item(item_name)
                if not item:
                    clean_name = self.player._clean_item_name(item_name)
                    self._last_feedback = intent.reply or f"You don't have a {clean_name} to use."
                    return
                
                # Handle specific item uses
                if item.name.lower() == "circuit breaker":
                    self.map.world_state["has_power"] = True
                    self._check_quest_triggers("action", {"action": "turn_on_lights"})
                    self._check_quest_updates("power_restored", {"action": "use_circuit_breaker"}, self.player, self.map.world_state)
                    self._last_feedback = intent.reply or "The circuit breaker clicks into place. Power hums through the cabin."
                elif item.name.lower() == "matches" and self.player.has_item("firewood"):
                    self.map.world_state["fire_lit"] = True
                    self._check_quest_triggers("action", {"action": "light_fire"})
                    self._check_quest_updates("fire_success", {"action": "light_fire", "success": True}, self.player, self.map.world_state)
                    self._check_quest_completion()
                    self._last_feedback = intent.reply or "The matches catch and the firewood ignites. Warmth spreads through the cabin."
                elif item.name.lower() == "matches" and not self.player.has_item("firewood"):
                    self._check_quest_triggers("action", {"action": "light_fire"})
                    self._check_quest_updates("fire_no_fuel", {"action": "light_fire"}, self.player, self.map.world_state)
                    self._last_feedback = intent.reply or "You strike a match, but you have nothing to light."
                elif item.name.lower() == "light switch":
                    # Check if power is available
                    if self.map.world_state.get("has_power", False):
                        self._last_feedback = intent.reply or "The light switch clicks and the cabin fills with warm light."
                    else:
                        # No power - trigger quest
                        self._check_quest_triggers("action", {"action": "use_light_switch"})
                        self._last_feedback = intent.reply or "You flip the switch, but nothing happens. The cabin remains dark."
                elif item.name.lower() == "fireplace":
                    # Check if fuel is available
                    if self.player.has_item("firewood"):
                        self._last_feedback = intent.reply or "You could light a fire here if you had matches."
                    else:
                        # No fuel - trigger quest
                        self._check_quest_triggers("action", {"action": "use_fireplace"})
                        self._last_feedback = intent.reply or "The fireplace is cold and empty. You need fuel to start a fire."
                else:
                    self._last_feedback = intent.reply or f"You use the {item.name}."
            elif intent.action == "help":
                self._apply_effects(intent)
                if intent.reply:
                    self._last_feedback = intent.reply
                else:
                    exits = ", ".join(context["exits"]) or "nowhere"
                    self._last_feedback = (
                        f"Keep it simple. Try 'go <direction>' — exits: {exits}. "
                        "You can also 'look', 'listen', check 'inventory', 'take' items, 'use' items, or 'throw' things."
                    )
            else:
                self._apply_effects(intent)
                
                # If the AI provided a reply, use it; otherwise use the fallback
                if intent.reply:
                    self._last_feedback = intent.reply
                else:
                    self._last_feedback = "You start, then think better of it. The cold in your chest makes you careful."

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
                "world_state": dict(self.map.world_state)
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
