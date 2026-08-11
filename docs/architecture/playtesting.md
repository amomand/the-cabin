# Playtesting and Model Evaluation

How to drive real game sessions locally, assert on what they show the player,
and evaluate candidate interpreter models. Content moved here from the README;
CONTRIBUTING.md covers the day-to-day commands.

## Local playtest runner

The playtest runner drives real terminal, web-session, or both-at-once game
objects, checks their visible output, and writes transcripts under
`reports/playtests/` (ignored by git).

```bash
python -m tools.playtest_runner
python -m tools.playtest_runner playtests/scenarios/act1_smoke.yaml
```

Scenarios live in `playtests/scenarios/` and run offline by default, so
deterministic smoke paths never call the OpenAI API. Use the reports as PR
evidence alongside the local diegesis and continuity review skills.

## Cross-surface scenarios

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

## Story-state assertions

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

## Dev seed saves

Named seeds jump playtests to known story beats. Commands and the seed list
live in CONTRIBUTING.md; the tool is `game/devtools/seed_saves.py`.

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
