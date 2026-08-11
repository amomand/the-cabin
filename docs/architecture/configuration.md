# Configuration

Environment variables, read via `game/config.py` at startup:

- `OPENAI_API_KEY` - required
- `OPENAI_MODEL` - default `gpt-5.6-terra`
- `OPENAI_REASONING_EFFORT` - default `none`
- `OPENAI_TIMEOUT_SECONDS` - per-request OpenAI timeout in seconds (default `20`)
- `CABIN_DEBUG=1` - enable debug output
- `CABIN_AI_LOG=1` - record AI calls locally under `logs/`, including raw player
  input and world state; off by default and should stay off on public or shared
  deployments

Web server (`server/app.py`) variables:

- `CABIN_ALLOWED_ORIGINS` - comma-separated WebSocket `Origin` allowlist;
  defaults to the production site and localhost dev origins

Or copy `config.json.example` to `config.json`.

`.env` is read only by the entry points that call `game.env.load_game_dotenv()`:
`main.py`, `server/app.py`, and the eval harness. Importing the game package has
no environment side effects, so a harness that pops `OPENAI_API_KEY` to force an
offline run stays offline. A new entry point that needs the keys has to load them
itself.
