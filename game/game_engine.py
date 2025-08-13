from game.player import Player
from game.map import Map
import os
from game.ai_interpreter import interpret, ALLOWED_ACTIONS

class GameEngine:
    def __init__(self):
        self.running = True
        self.player = Player()
        self.map = Map()
        self._last_feedback: str = ""
        self._last_room_id: str = None
        self._is_first_render: bool = True

    def run(self):
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
                "room_items": [],  # placeholder until items are modeled
                "inventory": list(self.player.inventory),
                "world_flags": dict(self.map.world_state),
                "allowed_actions": list(ALLOWED_ACTIONS),
            }

            intent = interpret(user_input, context)

            if intent.action == "move":
                direction = intent.args.get("direction")
                if not direction:
                    self._last_feedback = "You angle your body and stop. Where?"
                    return
                moved, message = self.map.move(direction)
                if moved:
                    # Apply any tiny effects and prefer AI reply under the fresh room description
                    self._apply_effects(intent)
                    self._last_feedback = intent.reply or ""
                else:
                    # If AI guessed a non-existent exit, keep it gentle and in-world
                    self._apply_effects(intent)
                    self._last_feedback = intent.reply or message or "You test that way. The path isn't there."
            elif intent.action == "look":
                self._apply_effects(intent)
                # Prefer AI reply; otherwise repeat room description
                self._last_feedback = intent.reply or room.get_description(self.player, self.map.world_state)
            elif intent.action == "inventory":
                self._apply_effects(intent)
                if intent.reply:
                    self._last_feedback = intent.reply
                else:
                    if self.player.inventory:
                        items = ", ".join(str(i) for i in self.player.inventory)
                        self._last_feedback = f"You check your bag: {items}."
                    else:
                        self._last_feedback = "You check your bag. Just air and lint."
            elif intent.action == "help":
                self._apply_effects(intent)
                if intent.reply:
                    self._last_feedback = intent.reply
                else:
                    exits = ", ".join(context["exits"]) or "nowhere"
                    self._last_feedback = (
                        f"Keep it simple. Try 'go <direction>' — exits: {exits}. "
                        "You can also 'look' or check 'inventory'."
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
        for item in inventory_remove:
            if item in self.player.inventory:
                self.player.inventory.remove(item)

        # Allow add only if item was already known (either already owned or visible). No room items yet, so skip.
        # This keeps us conservative until items are modeled.

    @staticmethod
    def clear_terminal():
        os.system('cls' if os.name == 'nt' else 'clear')

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
