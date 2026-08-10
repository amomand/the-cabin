# The Cabin

At ten past four, Nika's shop was still lit.
You kept your eyes on the junction and drove through.

A survival horror text adventure set in the Finnish wilderness. You move through snow and timber and memory. Something old moves with you. It prefers the quiet.

**[Play online](https://the-cabin-api.fly.dev/game.html)** — no setup and no personal API key. The door is already open.

---

## What is this?

The Cabin is a Python text adventure with AI-powered natural language input. Say what you would try; the AI interprets it inside an authored, deterministic world. It does not invent the plot or improvise new rules. The game answers in-world and never breaks the fourth wall. There is no "invalid command" here. There is only what happens next.

It runs in the raw terminal or through a lightweight browser client. The screen clears as you step into each new room, as if the world is rebuilt in front of you, fresh and cold.

Under the snow:

- Free-text input interpreted by AI (`gpt-5.6-terra` by default)
- Diegetic responses: no system chatter, only in-world narration
- Room-level exploration: Map -> Locations -> Rooms
- Fear, health, save/load, quest, event, and cutscene systems
- An Act I-V plotline: the wrong-layer cabin, the false-cabin night, and two endings hinged on one blue mug
- The Lyer, never fully seen, always near

## Run locally

The hosted game needs no setup or personal API key. To run your own copy, the game needs a voice: Python 3.10+ and an OpenAI API key.

Command examples use `python`. On systems where only `python3` is available, use `python3` instead, or the interpreter from an activated virtual environment.

```bash
# Keep the cold contained
python -m venv .venv
source .venv/bin/activate

# Install base Python dependencies
pip install -r requirements.txt

# Set up your API key
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Walk in
python main.py
```

On Windows, activate the environment with `.venv\Scripts\activate` instead.

To run the web client locally:

```bash
pip install -r requirements-server.txt
python -m uvicorn server.app:app --reload --port 8080
```

In another terminal, serve the browser client from the repo root:

```bash
python -m http.server 8000
```

Then open `http://localhost:8000/play.html` in a browser.

## Development checks

The full suite wants the full environment: terminal game, web server, pytest, and the playtest runner dependencies CI uses.

```bash
pip install -r requirements-dev.txt
python -m pytest
python -m tools.playtest_runner
python -m pytest --cov=game --cov=server --cov-report=term-missing
```

Put terminal/shared dependencies in `requirements.txt`, server dependencies in
`requirements-server.txt`, and development-only packages in
`requirements-dev.txt`.

## Features

- Natural language input mapped into an authored action and story system
- Diegetic handling for creative, impossible, save/load, and help paths
- `save` and `load` commands with named slots
- Dev seed saves that jump to known story beats
- Local playtest scenarios that drive terminal or web sessions and capture transcripts
- A Python test suite covering actions, story beats, web session flow, persistence, and AI hardening
- Modular architecture: actions, events, rendering, input, persistence, and web sessions are separated
- Response caching, so repeated commands are fast
- Local PR review skills for diegesis and continuity, catching immersion drift before it lands

## Story and lore

The main plotline lives in `docs/lore/plotline.md`, the canon beat reference for the Act I-V arc: the wrong cabin, the knowing, the refusal, the walk out. Supporting worldbuilding sits alongside it in `docs/lore/`: `characters.md`, `environment-setting.md`, and `the_lyer.md`. Read that last one with the lights on.

## Dev seed saves

Named seeds make playtesting the later acts easier, if easier is the word.

```bash
python -m game.devtools.seed_saves list
python -m game.devtools.seed_saves generate
python -m game.devtools.seed_saves use act3_arrival
```

After `use`, start the game and load the seed by name, for example
`load act3_arrival`. Run `python -m game.devtools.seed_saves list` whenever you
need the current names; the registry, not this README, owns them.

## Local playtest runner

The playtest runner drives real terminal, web-session, or both-at-once game objects, checks their visible output, and writes transcripts under `reports/playtests/` (ignored by git).

```bash
python -m tools.playtest_runner
python -m tools.playtest_runner playtests/scenarios/act1_smoke.yaml
```

Scenarios live in `playtests/scenarios/` and run offline by default, so deterministic smoke paths never call the OpenAI API. Use the reports as PR evidence alongside the local diegesis and continuity review skills.

### Cross-surface scenarios

A scenario's `surface:` can be `terminal`, `web`, or `both`.

`both` plays the same command script through `GameEngine` and `WebGameSession`
together and fails if they disagree about anything the player can see: the
rendered text of every turn, and the full story-state snapshot after every turn.
The game's promise is that it is the same thing whichever way you play it.
`game/turn.py` makes both surfaces *decide* a turn through one implementation
and `tests/test_turn_parity.py` pins that at unit level; neither covers
rendering, which is where the remaining risk lives.

The comparison normalises away differences that are presentation rather than
disagreement — hard wrapping, how many frames a turn is split into, the
terminal's trailing prompt, asterisk emphasis on overlay cues, and save
timestamps. Everything that survives is something a player would notice. See
`DifferentialScenarioDriver` in `tools/playtest_runner.py`.

`both` is the right surface for anything touching rendering, overlays, or save
state. It costs roughly double the runtime of a single-surface scenario, so the
narrower story scenarios stay on `web`.

Each report ends with a `## Story state at close` block: the engine's story state
(world layer, reunion stage, ending, wrongness log, flags, health and fear) captured
when the scenario finished. Scenarios can assert against it with `expected_state`
entries, each a `key=value` line matching the block:

```yaml
expected_state:
  - world_layer=wrong
  - reunion_stage=arrival
```

A mismatch is a finding, so story-state contracts fail CI the same way a forbidden
phrase does.

## Command interpretation regression harness

`python -m tools.command_interpretation_eval --check` runs the production
interpreter offline against the fixed corpus in
`evals/command_interpretation_corpus.json`, checking exact action and argument
accuracy, routing, and rejection of impossible inventory targets. The recorded
`evals/command_interpretation_baseline.json` preserves the pre-hardening result
and pins the corpus hash; current tests require every case and constraint to pass,
so corpus or baseline changes must be deliberate.

## Model evaluation harness

Compares candidate interpreter models (OpenAI and Anthropic) on the production
prompt path: latency (TTFT and total, avg/P95), deterministic mechanical checks
(routing, guardrails, Lyer-naming), and pairwise LLM judging of prose quality
against the incumbent. Outputs land under `reports/model_eval/` (ignored by
git), including a blind A/B sheet for a human read.

```bash
python -m game.devtools.model_eval --all --dry-run                    # plan without spending
python -m game.devtools.model_eval --runs 1 --no-judge                # smoke test
python -m game.devtools.model_eval --all --runs 10 --judge-runs 10    # decision run
```

One run per scenario is a smoke test, not a decision input. Judge win-rates
are reported with a scenario-cluster bootstrap 95% CI; a challenger only
counts as a prose improvement when the interval's lower bound clears 0.5.
Because verdicts cluster on scenarios, extra runs mostly sharpen latency and
routing numbers — widening the judged *scenario* pool is what narrows the
prose interval. Requires `OPENAI_API_KEY` (and `ANTHROPIC_API_KEY` for
Anthropic candidates) in `.env`. Evaluation history and the standing decision
rule live in the maintainer's notes.

## Project layout

```text
the-cabin/
├── main.py                 # Terminal entry point
├── play.html               # Browser client
├── server/                 # FastAPI WebSocket session server
├── config.json.example     # Configuration template
├── requirements-dev.txt    # Development/test dependency set
├── game/
│   ├── game_engine.py      # Main orchestrator
│   ├── actions/            # 16 action classes, including the Act V dawn choice
│   ├── events/             # EventBus + listeners
│   ├── input/              # InputHandler + legacy parser helpers
│   ├── persistence/        # SaveManager
│   ├── devtools/           # Playtest seed-save tools
│   ├── story/cutscenes/    # Authored runtime cutscene text
│   ├── map.py, player.py, room.py, item.py
│   └── ai_interpreter.py   # GPT integration + rule-based command handling
├── tests/                  # Python test suite
├── playtests/scenarios/    # Local playtest scenario briefs
├── tools/playtest_runner.py # Local transcript-producing playtest runner
├── saves/                  # Save files
├── docs/
│   ├── architecture/       # Technical docs
│   ├── lore/               # Plotline and worldbuilding
│   └── game_mechanics/     # Game rules and systems
├── .agents/skills/          # Local pre-PR review skills
└── .github/workflows/      # Deploy workflow
```

## Configuration

Environment variables:

- `OPENAI_API_KEY` - required
- `OPENAI_MODEL` - default `gpt-5.6-terra`
- `OPENAI_REASONING_EFFORT` - default `none`
- `OPENAI_TIMEOUT_SECONDS` - per-request OpenAI timeout in seconds (default `20`)
- `CABIN_DEBUG=1` - enable debug output
- `CABIN_AI_LOG=1` - record AI calls locally, including raw player input; off by default

Web server (`server/app.py`) variables:

- `CABIN_ALLOWED_ORIGINS` - comma-separated WebSocket `Origin` allowlist; defaults to the production site and localhost dev origins

Or copy `config.json.example` to `config.json`.

`.env` is read only by the entry points that call `game.env.load_game_dotenv()`:
`main.py`, `server/app.py`, and the eval harness. Importing the game package has
no environment side effects, so a harness that pops `OPENAI_API_KEY` to force an
offline run stays offline. A new entry point that needs the keys has to load them
itself.

## Design philosophy

Diegetic immersion: all feedback is in-world, second person, present tense, no system chatter. The AI is the core experience. Creative and impossible actions get narrated failures with consequences, never "you can't do that."

Continuity matters: the story contract is protected by tests and local pre-PR review skills. Diegesis review watches for fourth-wall leaks and tone breaks; continuity review watches for contradictions between implementation, docs, and the current plotline.

For technical details, see `docs/architecture/`.

## Contributing

Keep it quiet. Fewer exclamation marks, more winter. Match the tone in `docs/lore/`. No fourth wall. If adding systems, thread them through the diegetic voice and update the architecture, plotline, and README when behaviour or canon changes.

## License

MIT

## Troubleshooting

If free-form actions keep returning the same short, deterministic replies while
basic commands still work, the game has lost its voice; the interpreter is
probably using its offline fallback.

1. Check your `.env` has a valid `OPENAI_API_KEY`
2. Run with `CABIN_DEBUG=1 python main.py` to see API errors
3. Verify your key works: `curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"`

For a local diagnosis, `CABIN_AI_LOG=1 python main.py` writes AI-call details
under `logs/`. Those records include raw player input and world state, so the
switch is off by default and should stay off on public or shared deployments.
