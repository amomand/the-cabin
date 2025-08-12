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
                    self._last_feedback = ""
                else:
                    # If AI guessed a non-existent exit, keep it gentle and in-world
                    self._last_feedback = message or "You test that way. The path isn't there."
            elif intent.action == "look":
                # Repeat the current room description without clearing screen
                desc = room.get_description(self.player, self.map.world_state)
                self._last_feedback = desc
            elif intent.action == "inventory":
                if self.player.inventory:
                    items = ", ".join(str(i) for i in self.player.inventory)
                    self._last_feedback = f"You check your bag: {items}."
                else:
                    self._last_feedback = "You check your bag. Just air and lint."
            elif intent.action == "help":
                exits = ", ".join(context["exits"]) or "nowhere"
                self._last_feedback = (
                    f"Keep it simple. Try 'go <direction>' — exits: {exits}. "
                    "You can also 'look' or check 'inventory'."
                )
            else:
                self._last_feedback = "You start, then think better of it. The cold in your chest makes you careful."

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
