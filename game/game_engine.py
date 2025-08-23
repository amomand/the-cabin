from game.player import Player
from game.map import Map
from game.item import create_items
from game.wildlife import create_wildlife
from game.cutscene import CutsceneManager
import os
import sys
import tty
import termios
import time
from game.ai_interpreter import interpret, ALLOWED_ACTIONS

class GameEngine:
    def __init__(self):
        self.running = True
        self.player = Player()
        self.map = Map()
        self.items = create_items()  # All available items in the game
        self.wildlife = create_wildlife()  # All available wildlife in the game
        self.cutscene_manager = CutsceneManager()  # Cut-scene management
        self._last_feedback: str = ""
        self._last_room_id: str = None
        self._is_first_render: bool = True

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
                
                moved, message = self.map.move(direction)
                if moved:
                    # Check for cut-scenes after successful movement
                    to_room_id = self.map.current_room.id
                    cutscene_played = self.cutscene_manager.check_and_play_cutscenes(
                        from_room_id=from_room_id,
                        to_room_id=to_room_id,
                        player=self.player,
                        world_state=self.map.world_state
                    )
                    
                    # Apply any tiny effects and prefer AI reply under the fresh room description
                    self._apply_effects(intent)
                    self._last_feedback = intent.reply or ""
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
            elif intent.action == "help":
                self._apply_effects(intent)
                if intent.reply:
                    self._last_feedback = intent.reply
                else:
                    exits = ", ".join(context["exits"]) or "nowhere"
                    self._last_feedback = (
                        f"Keep it simple. Try 'go <direction>' — exits: {exits}. "
                        "You can also 'look', 'listen', check 'inventory', 'take' items, or 'throw' things."
                    )
            else:
                self._apply_effects(intent)
                self._last_feedback = intent.reply or "You start, then think better of it. The cold in your chest makes you careful."

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
        
        # Save terminal settings
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        
        try:
            # Set terminal to raw mode
            tty.setraw(sys.stdin.fileno())
            # Wait for any key
            sys.stdin.read(1)
        finally:
            # Restore terminal settings
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

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
