# The Cabin

You shouldn't have come back.  
It's awake.  
It always has been.

A survival horror text adventure set in the Finnish wilderness. You move through snow and timber and memory. Something old moves with you. It prefers the quiet.

---

## What is this?

The Cabin is a Python text adventure with AI-powered natural language input. Type anything; the game answers in-world and never breaks the fourth wall. There is no "invalid command" here. There is only what happens next.

It runs in the raw terminal or through a lightweight browser client. The screen clears as you step into each new room, as if the world is rebuilt in front of you, fresh and cold.

Under the snow:

- Free-text input interpreted by AI (`gpt-5.4-mini` by default)
- Diegetic responses: no system chatter, only in-world narration
- Room-level exploration: Map -> Locations -> Rooms
- Fear, health, save/load, quest, event, and cutscene systems
- An Act I-V plotline: the wrong-layer cabin, the false-cabin night, and two endings hinged on one blue mug
- The Lyer, never fully seen, always near

## Quick start

The game needs a voice: Python 3.10+ and an OpenAI API key.

Command examples use `python`. On systems where only `python3` is available, use `python3` instead, or the interpreter from an activated virtual environment.

```bash
# Install base Python dependencies
pip install -r requirements.txt

# Set up your API key
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Walk in
python main.py
```

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

## Features

- Natural language input: type what you want and the AI interprets it
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

After `use`, start the game and load the seed by name, for example `load act3_arrival`. Current seeds: `act1_end`, `act2_mid`, `act3_arrival`, `act3_seated`, `act4_recognition`.

## Local playtest runner

The playtest runner drives real terminal or web-session game objects, checks their visible output, and writes transcripts under `reports/playtests/` (ignored by git).

```bash
python -m tools.playtest_runner
python -m tools.playtest_runner playtests/scenarios/act1_smoke.yaml
```

Scenarios live in `playtests/scenarios/` and run offline by default, so deterministic smoke paths never call the OpenAI API. Use the reports as PR evidence alongside the local diegesis and continuity review skills.

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
│   ├── map.py, player.py, room.py, item.py, wildlife.py
│   └── ai_interpreter.py   # GPT integration + rule-based command handling
├── tests/                  # Python test suite
├── playtests/scenarios/    # Local playtest scenario briefs
├── tools/playtest_runner.py # Local transcript-producing playtest runner
├── saves/                  # Save files
├── docs/
│   ├── architecture/       # Technical docs
│   ├── lore/               # Plotline and worldbuilding
│   └── game_mechanics/     # Game rules and systems
├── .codex/skills/          # Local pre-PR review skills
└── .github/workflows/      # Deploy workflow
```

## Configuration

Environment variables:

- `OPENAI_API_KEY` - required
- `OPENAI_MODEL` - default `gpt-5.4-mini`
- `OPENAI_REASONING_EFFORT` - default `none`
- `OPENAI_TIMEOUT_SECONDS` - per-request OpenAI timeout in seconds (default `20`)
- `CABIN_DEBUG=1` - enable debug output

Web server (`server/app.py`) variables:

- `CABIN_ALLOWED_ORIGINS` - comma-separated WebSocket `Origin` allowlist; defaults to the production site and localhost dev origins

Or copy `config.json.example` to `config.json`.

## Design philosophy

Diegetic immersion: all feedback is in-world, second person, present tense, no system chatter. The AI is the core experience. Creative and impossible actions get narrated failures with consequences, never "you can't do that."

Continuity matters: the story contract is protected by tests and local pre-PR review skills. Diegesis review watches for fourth-wall leaks and tone breaks; continuity review watches for contradictions between implementation, docs, and the current plotline.

For technical details, see `docs/architecture/`.

## Contributing

Keep it quiet. Fewer exclamation marks, more winter. Match the tone in `docs/lore/`. No fourth wall. If adding systems, thread them through the diegetic voice and update the architecture, plotline, and README when behaviour or canon changes.

## License

MIT

## Troubleshooting

If the narration keeps repeating itself ("You start, then think better of it..."), the game has lost its voice; the API isn't answering.

1. Check your `.env` has a valid `OPENAI_API_KEY`
2. Run with `CABIN_DEBUG=1 python main.py` to see API errors
3. Verify your key works: `curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"`

If all three pass and the voice still repeats, it isn't the API.
