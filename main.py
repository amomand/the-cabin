import os
import sys

# Load .env before any other game import. game.env pulls in nothing else from
# the package, so this really does run first (issue #178).
from game.env import load_game_dotenv

env_path = load_game_dotenv()

# Debug: show if key loaded (only when CABIN_DEBUG=1)
if os.getenv("CABIN_DEBUG") == "1":
    key = os.getenv("OPENAI_API_KEY")
    print(f"[DEBUG] .env path: {env_path or 'none found'}", file=sys.stderr)
    print(f"[DEBUG] OPENAI_API_KEY loaded: {key is not None and len(key) > 10}", file=sys.stderr)

from game.game_engine import GameEngine

if __name__ == "__main__":
    game = GameEngine()
    try:
        game.run()
    except KeyboardInterrupt:
        print("\nThe cold watches you go...\n")