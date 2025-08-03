from game.player import Player
from game.map import Map
from game.game_ui import GameUI
import os

class GameEngine:
    def __init__(self):
        self.running = True
        self.player = Player()
        self.map = Map()
        self.ui = GameUI()

    def run(self):
        self.ui.update_status(self.player.health, self.player.fear)
        self.ui.update_room(self.map.current_room.name, self.map.current_room.description)

        while self.running:
            self.ui.update_status(self.player.health, self.player.fear)
            self.ui.update_room(self.map.current_room.name, self.map.current_room.description)
            self.clear_terminal()
            self.ui.render()

            user_input = input("> ")
            self.handle_user_input(user_input)

    def handle_user_input(self, user_input):
        # Simple movement parser: expects commands like 'go north'
        tokens = user_input.strip().lower().split()
        if len(tokens) == 2 and tokens[0] == "go":
            direction = tokens[1]
            current_room = self.map.current_room
            if direction in current_room.exits:
                self.map.current_room = current_room.exits[direction]

    @staticmethod
    def clear_terminal():
        os.system('cls' if os.name == 'nt' else 'clear')

# The Lyer watches silently. Nothing escapes its notice.
