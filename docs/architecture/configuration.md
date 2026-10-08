# Configuration

Game settings, read via `game/config.py` at startup:

- `CABIN_MODEL_PROVIDER` - `anthropic` (default) or `openai`. The provider
  and its key are read from the environment on every model call, so a harness
  that pops the keys stays offline.
- `ANTHROPIC_API_KEY` - required for the default provider
- `ANTHROPIC_MODEL` - default `claude-sonnet-5-5`
- `ANTHROPIC_THINKING` - default `off`; otherwise an adaptive effort level
  (`low`, `medium`, `high`). `off` sends `between_tools` on Sonnet 5.5, which
  rejects `disabled`, and `disabled` elsewhere. Anthropic is reached over
  httpx on every surface, including the iOS bundle; there is no SDK to ship.
- `OPENAI_API_KEY` - required when the provider is `openai`
- `OPENAI_MODEL` - default `gpt-5.6-terra`
- `OPENAI_REASONING_EFFORT` - default `none`; on models that reject `none`
  (`gpt-6-astra`, the `gpt-6.1` line) the call runs at `low` instead
- `OPENAI_TIMEOUT_SECONDS` - total production model-call budget in seconds
  for either provider (default `20`), including at most one short retry for
  a connection failure, `429`, `5xx`, or malformed JSON response. A timeout
  itself, a refusal, and other `4xx` responses fall back immediately.
- `CABIN_DEBUG=1` - enable debug output
- `CABIN_AI_LOG=1` - record AI calls locally under `logs/`, including raw player
  input and world state; off by default and should stay off on public or shared
  deployments

Web server (`server/`) variables, read from the environment where they are
used rather than through `game/config.py`:

- `CABIN_ALLOWED_ORIGINS` - comma-separated `Origin` allowlist for both the
  WebSocket and HTTP surfaces; defaults to the production site and localhost
  dev origins
- `CABIN_SAVE_ROOT` - root directory for the durable per-client save
  directories (default `saves`); point it at a mounted volume in any
  deployment that offers durable saves. Throwaway session directories are not
  affected: `WebGameSession` picks its own relative path and deletes it on
  release.
- `CABIN_SAVE_RETENTION_DAYS` - how long a durable client save directory
  survives without being written to (default `30`); `0` disables pruning
  rather than deleting everything

Or copy `config.json.example` to `config.json`.

`.env` is read only by the entry points that call `game.env.load_game_dotenv()`:
`main.py`, `server/app.py`, and the eval harness. Importing the game package has
no environment side effects, so a harness that pops the model keys (every name
in `game.env.MODEL_API_KEY_VARS`) to force an offline run stays offline. A new
entry point that needs the keys has to load them itself.
