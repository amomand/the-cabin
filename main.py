import os
from pathlib import Path

# Load .env from project root before any game imports
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    load_dotenv(env_path)
except ImportError:
    pass  # dotenv is optional

from game.game_engine import GameEngine

if __name__ == "__main__":
    game = GameEngine()
    try:
        game.run()
    except KeyboardInterrupt:
        print("\nThe cold watches you go...\n")