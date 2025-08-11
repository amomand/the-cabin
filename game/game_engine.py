from game.player import Player
from game.map import Map
import os

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
        # Simple movement parser: expects commands like 'go north'
        tokens = user_input.strip().lower().split()
        if len(tokens) == 2 and tokens[0] == "go":
            direction = tokens[1]
            moved, message = self.map.move(direction)
            if moved:
                self._last_feedback = ""
            else:
                self._last_feedback = message
        elif len(tokens) == 1 and tokens[0] == "quit":
            self.running = False
        else:
            # Valid command but no movement (future-proofing)
            self._last_feedback = "You hesitate. Keep it simple: try 'go north', 'go south', 'go cabin'."

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
