# Codex Instructions

This repository's broader project guidance lives in `CLAUDE.md`. Read it before
making code, narrative, or documentation changes here; it contains the current
architecture notes, story constraints, commands, and anti-patterns.

## Pull Request Workflow

The hosted gh-aw guard workflows are disabled in this repo. Before raising or
updating a pull request, run the relevant local review skills and include their
verdicts in the PR summary or maintainer update:

- `.agents/skills/the-cabin-diegesis-review/SKILL.md` for player-facing prose,
  authored story beats, playable HTML, input handling, rendering, or response
  behavior.
- `.agents/skills/the-cabin-continuity-review/SKILL.md` for behavior, tests,
  configuration, documentation, lore, mechanics, public commands, web-session
  behavior, or story-state contracts.

Additional review is need-driven, not a default pull request gate:

- Use the user-level `adversarial-review` skill when the maintainer requests an
  independent second-model review. Also offer it before publishing material
  changes with meaningful failure modes, as its trigger rules describe. Skip it
  for copy-only or mechanical changes unless the maintainer explicitly asks.
- Use the user-level `copilot-pr-review-loop` skill only when the maintainer asks
  to put an existing pull request through a Copilot review cycle. Follow its
  bounded loop and never merge unless explicitly asked.
- Do not request `@codex review` by default or block pull request readiness on a
  hosted Codex review. The presence of either optional skill does not make an
  outside review mandatory.

The maintainer is the deciding voice.

## Code Review Rules

### Authored story truth

- Flag any path that lets a model generate authored beats, advance story state,
  or bypass a gate. The safe path is model-assisted intent parsing followed by
  deterministic actions, authored narration, and explicit state transitions.

### Shared turn and state contracts

- Flag terminal/web divergence or story-state changes implemented in only one
  surface. Shared decisions belong in `game/turn.py` and every meaningful gate
  or layer transition must remain both deterministic and narrated.

### Offline isolation

- Flag imports or harness changes that can load `.env` or make live model calls
  during tests, seeds, or offline playtests. Entry points own environment
  loading; deterministic tooling must remain credential-free.

### Stacked pull requests

GitHub's merged badge only proves that a pull request reached its selected
base. It does not prove that the work reached `main`.

1. Do not merge a stacked child while its base still names another feature
   branch.
2. After the parent merges, wait until GitHub visibly retargets the child to
   `main`. If it does not, retarget it manually and update the child branch
   before merging. This wait still applies when the parent has just merged;
   GitHub's retargeting can lag behind the merge.
3. After the stack merges, verify every intended child head or feature commit:

   ```bash
   python -m tools.verify_main_reachability <commit> [<commit> ...]
   ```

   The command fetches `origin/main` before checking ancestry. Record the
   passing result in the maintainer update, then close the tracking issue.
