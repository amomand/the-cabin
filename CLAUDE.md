# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repository.

## Project

**The Cabin** is a survival horror text adventure (Python 3.10+) with AI-powered natural language input. Set in the Finnish wilderness, it uses OpenAI's chat models for diegetic (in-world) responses. The game never breaks the fourth wall — there is no "invalid command", only narrated in-world outcomes.

Story plotline lives at `~/obsidian/Fiction Writing/The Cabin/The Cabin - Plotline.md`. Phase plan and progress notes live at `~/obsidian/Projects/the-cabin/`. Read them before doing narrative work.

The game code lives under `game/`, `server/`, `tests/`, `main.py`. Anything outside those is either build/deploy plumbing (`Dockerfile`, `fly.toml`, etc.) or the static site served from the Fly app via `_mount_site()` in `server/app.py` (`index.html`, `game.html`, `play.html`, `stories.html`, `the-cabin.html`/`no-further.html`, with prose snapshots under `stories/` — see `stories/README.md`).

## Commands

```bash
# Install development/test dependencies
pip install -r requirements-dev.txt

# Run the game
python main.py

# Run with debug output
CABIN_DEBUG=1 python main.py

# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=game --cov=server --cov-report=term-missing

# Specific test file or module
python -m pytest tests/actions/test_move.py -v
python -m pytest tests/actions -v

# Generate dev save seeds for playtesting story beats
python -m game.devtools.seed_saves           # regenerate all
python -m game.devtools.seed_saves list      # list available seeds
python -m game.devtools.seed_saves use NAME  # copy seed into saves/ for in-game `load NAME`
```

Requires `OPENAI_API_KEY` in `.env` to run the game (not needed for tests).
The full test suite imports the web server entrypoint, so install
`requirements-dev.txt` before running `pytest`.

## Architecture

**Data flow:** User Input → InputHandler (system commands) → AI Interpreter (`_rule_based` for obvious commands, model for creative input) → ActionRegistry → `GameEngine._apply_effects()` → EventBus → `GameEngine.render()`.

**Key modules under `game/`:**

- `game_engine.py` — Main orchestrator. Coordinates render → input → AI → action → effects → events → render.
- `ai_interpreter.py` — OpenAI integration. Parses free-text input into `Intent(action, args, confidence, reply, effects)`. LRU response cache. Falls back to rule-based parsing for trivial commands. Defaults to `gpt-5.4-mini`; supports older models via param compatibility shim.
- `actions/` — Action classes implementing the `Action` ABC (`base.py`). Each has `execute(ctx: ActionContext) -> ActionResult`. Dispatched by `ActionRegistry`. Registered in `actions/__init__.py` via `create_default_registry()`.
- `events/` — Pub/sub `EventBus`. Actions emit events; listeners in `events/listeners/` handle quest progression and cutscenes.
- `input/` — `InputHandler` routes system commands (quit/save/load). Runtime intent parsing then goes through `ai_interpreter.interpret()`, which handles trivial commands with `_rule_based()` and sends creative input to AI.
- `game_engine.py::_apply_effects()` — Applies bounded fear/health/inventory changes from interpreted intents.
- `game_engine.py::render()` — Displays rooms, feedback, and status in the terminal.
- `persistence/save_manager.py` — JSON-based save/load in `saves/`.
- `game_state.py` / `world_state.py` — Typed state. `WorldState` has explicit fields (e.g. `fire_lit`, `voicemail_heard`, `world_layer`, `reunion_stage`, `wrongness`) plus dict-like access for ad-hoc flags.
- `story/` — Story data: `AnomalyID` enum + `ANOMALY_DESCRIPTIONS` in `anomalies.py`; `log_tell()` helper in `tells.py`. **Use these — never use raw anomaly ID strings.**
- `devtools/seed_saves.py` — Dev-only tool for jumping to known story beats during playtesting.
- `config.py` — Loads from env vars and `config.json`. Access via `get_config()`.

**Dependency injection:** All major components accept dependencies via constructors, enabling unit testing without mocks. Test fixtures are in `tests/conftest.py`.

## Story state model (current)

The Acts I–V flow is governed by these fields on `WorldState`:

- `fire_lit`, `voicemail_heard`, `footage_reviewed`, `sauna_used`, `first_morning` — Act I gates.
- `wrongness: WrongnessLog` — accumulating observed anomalies (deduped by ID). Use `log_tell(world_state, AnomalyID.X)` to record one.
- `lyer_encountered` — set when the Act II climax fires.
- `world_layer: "real" | "wrong"` — flipped by `enter_wrong_layer()` / `exit_wrong_layer()`.
- `reunion_stage: "none" | "arrival" | "seated" | "complete"` — gates the Act III tells behind the scripted Nika reunion.
- `wrong_outside_seen` — fires the "this isn't where I drove to" pivot once.
- `recognition` — set when the correction-turn beat lands. Required (with wrongness threshold) to refuse.

Refusal (`exit_wrong_layer()`) resets `reunion_stage` and `wrong_outside_seen`.

## Extending the game

- **New action:** subclass `Action` in `game/actions/` → register in `actions/__init__.py` → add to `ALLOWED_ACTIONS` in `ai_interpreter.py` → write tests in `tests/actions/`.
- **New event:** define in `game/events/types.py` → emit via `ActionResult.events` → handle in `game_engine.py::_handle_action_events()` → subscribe a listener if needed.
- **New quest:** add to `game/quests.py` → subscribe a listener in `game/events/listeners/`.
- **New room:** add to a location in `game/map.py`. Rooms support `description_fn` and `wrong_description_fn` for layer-aware rendering.
- **New anomaly:** add to `AnomalyID` + `ANOMALY_DESCRIPTIONS` in `game/story/anomalies.py`. Use `log_tell()` to record.

## Diegetic Immersion (Critical Design Constraint)

All player-facing text must stay in-world. Fourth-wall breaks are bugs.

- **Voice:** second person, present tense, sensory, terse, bleak. Sentences land short.
- **Failures are narrated, not labelled.** Impossible actions get sensory consequences (fear/health, narrated denial), never "you can't do that here", "invalid command", or "Error:".
- **Rule-based parsing is narrow.** Only trivially obvious commands (movement, inventory, look/help) should be handled before the model. When in doubt, let the AI handle it.
- **The Lyer is implied, never explained, never named in player-facing fiction.** No in-game glossary, no stat screen, no in-world description that reduces it. It is presence, attention, and wrongness — that's all. This rule applies to surfaces the player or reader of the fiction consumes: in-game text, story prose, published lore. It does **not** apply to internal contributor surfaces in this repo — mechanics docs, code, comments, commit messages, design notes — where the Lyer should be named plainly so the engineering stays precise. Field/method names like `lyer_encountered` and the lore doc `docs/lore/the_lyer.md` already do this; mechanics docs should too.
- **Story beats use authored prose, not AI prose.** For story-critical beats (voicemail, camera, sauna, bed, reunion, tells, correction-turn, refusal), the hardcoded narration is canonical. AI is for *intent parsing*, not for rewriting authored scenes. Generic item-use can still fall back to AI flavour.
- **Anti-patterns:** "Invalid command", "You can't do that", "Error:", third-person narration, explaining game mechanics, narrating in past tense, breaking present-tense intimacy.

## Anti-patterns specific to this codebase

- **Magic anomaly strings.** Use `AnomalyID.X.value`, not `"fox_tracks"`.
- **Dual narration drift.** Don't reintroduce `ctx.ai_reply or "hardcoded"` in story beats. Authored prose is the single source of truth there.
- **Silent flag flips for narrative beats.** If recognition or a layer change happens, narrate it. Don't just set the flag inside an `on_enter` callback.
- **Bundling unrelated changes.** Commits should do one thing. Don't delete `CLAUDE.md` or change `.gitignore` inside a fix commit unless that's explicitly the fix.

## Pull request reviews

The `.github/workflows/ci.yml` workflow runs `pytest` and the playtest runner on
every pull request. This is **mechanical regression coverage only** — it does not
replace the domain review below. Diegesis and continuity remain the job of the
local review skills and the maintainer; a green CI run says nothing about voice or
story-state correctness.

The hosted gh-aw guard workflows are disabled in this repo. Before raising a PR,
run the relevant local review skills and include their verdicts in your PR
summary or maintainer update:

- `.codex/skills/the-cabin-diegesis-review/SKILL.md` for player-facing prose,
  authored story beats, playable HTML, input handling, rendering, or response
  behavior.
- `.codex/skills/the-cabin-continuity-review/SKILL.md` for behavior, tests,
  configuration, documentation, lore, mechanics, public commands, web-session
  behavior, or story-state contracts.

When raising a PR in this repo, the review loop has three voices:

- **Local review skills** provide disciplined pre-PR self-review.
- **GitHub Copilot** must be added as a reviewer when the PR is opened.
- **The maintainer** is the deciding voice.

Expected behaviour for agent-raised PRs:

1. Before pushing, describe the intended flow briefly, run tests, and run the
   relevant local review skills.
2. After pushing the branch and opening the PR, request a Copilot review.
   Use GitHub CLI, then verify through the REST API because `gh pr view
   --json reviewRequests` may omit bot reviewers:

   ```bash
   gh pr edit <N> --add-reviewer copilot-pull-request-reviewer
   gh api repos/{owner}/{repo}/pulls/<N>/requested_reviewers
   ```
3. Wait for Copilot review on the latest head commit before declaring the PR
   ready.
4. Treat the review as input, not command. Read all of it. Synthesise.
5. Reply on each actionable review comment with what changed.
6. Overriding a reviewer is allowed when they have misread the change. Say so
   in the same comment thread or PR conversation with the reason; don't override
   silently.
7. Escalate to the maintainer when there is a meaningful disagreement with
   Copilot, or when overriding alone feels like the wrong call.

The point isn't deference. It's making sure every agent-raised PR gets a local
domain review before it opens and a hosted outside read before it ships.
