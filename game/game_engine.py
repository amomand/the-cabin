from game.player import Player
from game.map import Map
import os

class GameEngine:
    def __init__(self):
        self.running = True
        self.player = Player()
        self.map = Map()

    def run(self):
        self.clear_terminal()
        print(self.map.current_room.description)
        while self.running:
            user_input = input("\nWhat would you like to do? ")
            self.handle_user_input(user_input)

    def handle_user_input(self, user_input):
        # Simple movement parser: expects commands like 'go north'
        tokens = user_input.strip().lower().split()
        if len(tokens) == 2 and tokens[0] == "go":
            direction = tokens[1]
            current_room = self.map.current_room
            if direction in current_room.exits:
                self.map.current_room = current_room.exits[direction]
                print(f"\n{self.map.current_room.description}")
            else:
                print("You can't go that way.")
        else:
            print("Are you sure you want to do that?")

    @staticmethod
    def clear_terminal():
        os.system('cls' if os.name == 'nt' else 'clear')

# The Lyer watches silently. Nothing escapes its notice.
