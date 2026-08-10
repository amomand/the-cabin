# Contributing to The Cabin

This is the shared project guidance for human contributors and coding agents.
Read it before making code, narrative, documentation, or workflow changes.
Agent-specific instruction files should point here rather than copy these rules.

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

**Data flow:** User Input → InputHandler (system commands) → `turn.take_turn()` → AI Interpreter (`_rule_based` for obvious commands, model for creative input) → ActionRegistry → `turn.apply_effects()` → EventBus → per-surface render.

**Key modules under `game/`:**

- `game_engine.py` — Main orchestrator. Coordinates render → input → AI → action → effects → events → render.
- `ai_interpreter.py` — OpenAI integration. Parses free-text input into `Intent(action, args, confidence, reply, effects)`. LRU response cache. Falls back to rule-based parsing for trivial commands. Defaults to `gpt-5.6-terra`; supports older models via param compatibility shim.
- `actions/` — Action classes implementing the `Action` ABC (`base.py`). Each has `execute(ctx: ActionContext) -> ActionResult`. Dispatched by `ActionRegistry`. Registered in `actions/__init__.py` via `create_default_registry()`.
- `events/` — Pub/sub `EventBus`. Actions emit events; listeners in `events/listeners/` handle quest progression and cutscenes.
- `input/` — `InputHandler` routes system commands (quit/save/load). Runtime intent parsing then goes through `ai_interpreter.interpret()`, which handles trivial commands with `_rule_based()` and sends creative input to AI.
- `turn.py` — **Surface-agnostic turn core.** `take_turn()` runs one command (interpret → execute → apply effects → emit events); `apply_effects()` applies bounded fear/health/inventory changes. Both `GameEngine` and `WebGameSession` call it, so a turn decides the same thing on either surface. Change turn behaviour here, never in a surface.
- `save_commands.py` — Shared save/load/list/delete decisions and their diegetic lines, for the same reason.
- `game_engine.py::_apply_effects()` — Thin wrapper over `turn.apply_effects()`, kept as the terminal surface's entry point.
- `game_engine.py::render()` — Displays rooms, feedback, and status in the terminal.
- `persistence/save_manager.py` — JSON-based save/load in `saves/`.
- `game_state.py` / `world_state.py` — Typed state. `WorldState` has explicit fields (e.g. `fire_lit`, `voicemail_heard`, `world_layer`, `reunion_stage`, `wrongness`) plus dict-like access for ad-hoc flags.
- `story/` — Story data: `AnomalyID` enum + `ANOMALY_DESCRIPTIONS` in `anomalies.py`; `log_tell()` helper in `tells.py`. **Use these — never use raw anomaly ID strings.**
- `devtools/seed_saves.py` — Dev-only tool for jumping to known story beats during playtesting.
- `config.py` — Loads from env vars and `config.json`. Access via `get_config()`.
- `env.py` — `load_game_dotenv()`, called by entry points only (`main.py`, `server/app.py`, `model_eval`). Importing the game package must never load `.env` itself, or harnesses that pop `OPENAI_API_KEY` make live calls anyway (issue #178). Imports nothing else from `game`, so it can run before modules that read env at import scope.

**Dependency injection:** All major components accept dependencies via constructors, enabling unit testing without mocks. Test fixtures are in `tests/conftest.py`.

## Story state model (current)

The Acts I–V flow is governed by these fields on `WorldState`:

- `fire_lit`, `voicemail_heard`, `footage_reviewed`, `sauna_used`, `first_morning` — Act I gates.
- `wrongness: WrongnessLog` — accumulating observed anomalies (deduped by ID). Use `log_tell(world_state, AnomalyID.X)` to record one.
- `lyer_encountered` — set when the Act II climax fires.
- `world_layer: "real" | "wrong"` — flipped by `enter_wrong_layer()` / `exit_wrong_layer()`.
- `reunion_stage: "none" | "arrival" | "tended" | "seated" | "complete" | "consented" | "bedded" | "night" | "dawn"` — spans the false-cabin reunion, night, knowing, and dawn offer.
- `consent_given` — set by the consent-door beat after the completed reunion.
- `recognition` — set when the authored knowing lands at the night-seam threshold. Required with the night seams for either dawn ending.
- `ending: "none" | "escaped" | "stayed"` — records the dawn choice. Legacy `accepted` and `refused` values still load.
- `coda_stage: "none" | "home" | "called" | "scraping" | "end"` — advances the escape coda after the walk out.
- `wrong_outside_seen` — legacy v1 save field; no current beat sets it.

The refusal leaves Elli in the wrong layer for the playable walk out. Arrival
home calls `exit_wrong_layer()`, which resets `reunion_stage`,
`wrong_outside_seen`, and `consent_given`.

## Extending the game

- **New action:** subclass `Action` in `game/actions/` → register in `actions/__init__.py` → add to `ALLOWED_ACTIONS` in `ai_interpreter.py` → write tests in `tests/actions/`.
- **New event:** define in `game/events/types.py` → emit via `ActionResult.events` → handle in `game/turn.py::handle_action_events()` → subscribe a listener if needed. Handle it in the shared core, not in a surface, or the two surfaces drift (see issue #113).
- **New quest:** add to `game/quests.py` → subscribe a listener in `game/events/listeners/`.
- **New room:** add to a location in `game/map.py`. Rooms support `description_fn` and `wrong_description_fn` for layer-aware rendering, and `denial_text` / `wrong_denial_text` for the refusal a direction gets when the room does not offer it. Set `is_indoors=True` on interiors so the default refusal is a wall rather than a treeline.
- **New anomaly:** add to `AnomalyID` + `ANOMALY_DESCRIPTIONS` in `game/story/anomalies.py`. Use `log_tell()` to record.

## Diegetic Immersion (Critical Design Constraint)

All player-facing text must stay in-world. Fourth-wall breaks are bugs.

- **Voice:** second person, present tense, sensory, terse, bleak. Sentences land short.
- **Failures are narrated, not labelled.** Impossible actions get sensory consequences (fear/health, narrated denial), never "you can't do that here", "invalid command", or "Error:".
- **Rule-based parsing is narrow.** Only trivially obvious commands (movement, inventory, look/help) should be handled before the model. When in doubt, let the AI handle it.
- **The Lyer is implied, never explained, never named in player-facing fiction.** No in-game glossary, no stat screen, no in-world description that reduces it. It is presence, attention, and wrongness — that's all. This rule applies to surfaces the player or reader of the fiction consumes: in-game text, story prose, published lore. It does **not** apply to internal contributor surfaces in this repo — mechanics docs, code, comments, commit messages, design notes — where the Lyer should be named plainly so the engineering stays precise. Field/method names like `lyer_encountered` and the lore doc `docs/lore/the_lyer.md` already do this; mechanics docs should too.
- **Story beats use authored prose, not AI prose.** For story-critical beats (the Act I reopening ritual, voicemail, camera, sauna, bed, reunion, tells, consent door, night seams, the knowing, dawn choice, walk out, coda), the hardcoded narration is canonical. AI is for *intent parsing*, not for rewriting authored scenes. Generic item-use can still fall back to AI flavour.
- **Anti-patterns:** "Invalid command", "You can't do that", "Error:", third-person narration, explaining game mechanics, narrating in past tense, breaking present-tense intimacy.

## Anti-patterns specific to this codebase

- **Magic anomaly strings.** Use `AnomalyID.X.value`, not `"fox_tracks"`.
- **Dual narration drift.** Don't reintroduce `ctx.ai_reply or "hardcoded"` in story beats. Authored prose is the single source of truth there.
- **Silent flag flips for narrative beats.** If recognition or a layer change happens, narrate it. Don't just set the flag inside an `on_enter` callback.
- **Bundling unrelated changes.** Commits should do one thing. Don't change contributor guidance or `.gitignore` inside a fix commit unless that's explicitly the fix.

## Pull request workflow

### Required checks

The `.github/workflows/ci.yml` workflow runs `pytest` and the playtest runner on
every pull request. This is **mechanical regression coverage only** — it does not
replace the domain review below. Diegesis and continuity remain the job of the
local review skills and the maintainer; a green CI run says nothing about voice or
story-state correctness.

Run the tests relevant to the change before opening a pull request. When no
local test applies, record `N/A` with the reason in the pull request instead of
claiming a test pass.

### Local domain reviews

Run each applicable local review skill against the final candidate diff before
opening a pull request:

- `.agents/skills/the-cabin-diegesis-review/SKILL.md` for player-facing prose,
  authored story beats, playable HTML, input handling, rendering, or response
  behavior.
- `.agents/skills/the-cabin-continuity-review/SKILL.md` for behavior, tests,
  configuration, documentation, lore, mechanics, public commands, web-session
  behavior, or story-state contracts.

Record each applicable verdict in the pull request summary or maintainer
update. Record `N/A` with a reason for a review that does not apply. Rerun a
review only after a substantive commit changes something within that review's
scope. Metadata edits, discussion replies, and mechanical changes outside its
scope do not require another pass.

These skills are bounded project self-checks, not independent approval. The
authoring agent runs them in its own context. The maintainer remains the
deciding voice.

### Review scale

Every pull request gets the applicable local self-reviews, green CI and the
maintainer's decision. Agent-authored pull requests also declare the strongest
review depth touched by the change:

- **Routine:** documentation, test-only or mechanical work that does not change
  runtime behaviour, authored story truth, a public contract, validation or
  proof meaning, workflows, permissions, credentials, publication or another
  trust boundary. An automatic hosted review is welcome but advisory; do not
  wait for one or request another pass solely to complete this lane.
- **Material:** runtime behaviour, player-facing output, authored story truth,
  public contracts or operational contributor guidance outside the high-risk
  boundaries below. Obtain one completed outside read of the exact current head
  by a reviewer outside every authoring family.
- **High-risk:** a change touching any named boundary below. Complete the
  Material lane and add an adversarial execution review against an exact
  committed target.

Mixed changes use the strongest applicable lane. Record every authoring family
and the review depth once in the pull request's `Review provenance` section. A
reviewer from an authoring family does not count as independent. Human-only
changes are exempt from the outside and adversarial lanes.

Run applicable agent-side review work in draft, then mark the pull request ready
for review once that work and CI are green. Only the maintainer merges.

For Material and High-risk changes, the outside read is a single asynchronous
pass by default. An empty review completes the lane. Every finding gets a
visible reply recording the decision: fixed, already covered, outdated or
overridden with the reason. Batch review fixes before requesting one follow-up
pass; reply-only and resolution-only work does not require another review. Keep
looping only while passes return findings that change behaviour, and stop when a
pass returns nothing real. The user-level `copilot-pr-review-loop` skill
implements this bounded cycle.

This repository deliberately narrows the user-level universal outside-review
default for Routine work. If a hosted review of a Routine change uncovers a
material concern, reclassify the pull request and complete the Material lane.

These are roles, not tools. The outside read is currently Copilot's hosted
review, with Codex cloud as the fallback when Copilot shares a family with an
author; the adversarial reviewer is whichever second model the skill selects.
Migrating the tooling swaps the implementation of a role and does not change
this policy.

The `independent-review` commit status reads the authoring families and review
depth from the pull request body. It passes Routine work without waiting and,
for Material or High-risk work, verifies a completed review of the exact head
by a non-author family. The `main` ruleset requires `test`; the review status can
be required without turning Routine work into a blocking outside-review lane.
Do not infer Material or High-risk coverage from an outstanding request or a
review of an older commit.

### High-risk review boundaries

- **Authored story truth.** Flag any path that lets a model generate authored
  beats, advance story state, or bypass a gate. The safe path is model-assisted
  intent parsing followed by deterministic actions, authored narration, and
  explicit state transitions.
- **Shared turn and state contracts.** Flag terminal/web divergence or
  story-state changes implemented in only one surface. Shared decisions belong
  in `game/turn.py`; every meaningful gate or layer transition must remain both
  deterministic and narrated.
- **Offline isolation.** Flag imports or harness changes that can load `.env` or
  make live model calls during tests, seeds, or offline playtests. Entry points
  own environment loading; deterministic tooling must remain credential-free.
- **Proof and publication boundaries.** Flag changes to validation meaning,
  evidence provenance, credentials, write permissions, destructive behaviour or
  guarded publication. These changes require adversarial review because a green
  result is itself part of the trusted output.

### Stacked pull requests

For stacked pull requests, a merged badge is not the completion condition.
Never merge a child while its base still names another feature branch. After
the parent merges, wait until GitHub visibly retargets the child to `main`, or
retarget it manually and update the child branch before merging. GitHub's
retargeting can lag behind the parent merge, which is the dangerous window.

After the stack merges, check every intended child head or feature commit
against a freshly fetched `origin/main`:

```bash
python -m tools.verify_main_reachability <commit> [<commit> ...]
```

Record the passing result in the maintainer update before closing the tracking
issue. The PR template keeps this post-merge check on the maintainer checklist.

## Scheduled playtest review

The hosted gh-aw workflows are disabled and retained only as rollback source.
The weekly playtest review runs as a local Codex Scheduled task against an exact
`origin/main` worktree. Its repo-local skill is
`.agents/skills/the-cabin-playtest-review/SKILL.md`; claims, terminal state and
the at-most-three-issue publisher live behind the shared
`local-agentic-control` guard and ledger issue `#193`. See
`docs/architecture/agentic-playtest-review.md` for the boundaries.

The guard owns evidence preparation as well as publication: it anchors the
manifest before reviewer access, and successful terminal outcomes must match
that anchor. Every committed scheduled scenario is offline and the evidence
subprocess receives no model credential.

This scheduled workflow is independent of pull request review and is never a
pull request gate.
