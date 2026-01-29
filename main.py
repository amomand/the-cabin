import os
import sys
from pathlib import Path

# Load .env from project root before any game imports
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    loaded = load_dotenv(env_path)
    # Debug: show if key loaded (only when CABIN_DEBUG=1)
    if os.getenv("CABIN_DEBUG") == "1":
        key = os.getenv("OPENAI_API_KEY")
        print(f"[DEBUG] .env path: {env_path}", file=sys.stderr)
        print(f"[DEBUG] .env exists: {env_path.exists()}", file=sys.stderr)
        print(f"[DEBUG] load_dotenv returned: {loaded}", file=sys.stderr)
        print(f"[DEBUG] OPENAI_API_KEY loaded: {key is not None and len(key) > 10}", file=sys.stderr)
except ImportError:
    pass  # dotenv is optional

from game.game_engine import GameEngine

if __name__ == "__main__":
    game = GameEngine()
    try:
        game.run()
    except KeyboardInterrupt:
        print("\nThe cold watches you go...\n")