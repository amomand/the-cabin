---
name: the-cabin-diegesis-review
description: Run a local pre-PR review of The Cabin changes for diegetic immersion issues, fourth-wall leaks, parser-style failure language, AI/system language, and player-facing prose that explains the interface instead of narrating the world.
---

# The Cabin Diegesis Review

Use this skill before opening or updating a PR when a change touches player-facing prose, authored story beats, playable HTML, input handling, rendering, or response behavior.

This is a local review skill. Do not post its output to GitHub automatically. Report the verdict in your PR summary or maintainer update.

## Scope

Review the branch diff against the mainline:

```bash
git diff --name-only origin/main...HEAD
git diff --stat origin/main...HEAD
```

If `origin/main...HEAD` is not available, use the best local base and state what you used.

Focus on:

- `game/**`
- `docs/lore/**`
- `README.md`
- top-level playable HTML files

Ignore:

- test assertions that quote forbidden examples as forbidden examples
- developer documentation that explicitly explains the diegetic contract
- mechanics documentation that is not player-facing and does not add player-visible prose
- comments or code names that are not player-facing
- ordinary implementation details that cannot reach the player
- purely visual or ordering changes that do not alter player-facing prose or input/response behavior

## Contract

The game must never admit it is a parser, command interface, AI system, model, prompt, or program while responding to the player.

- All player-facing failure should be narrated in-world.
- Impossible actions should become grounded fictional failures with sensory consequence.
- Weird, ambiguous, or playful input should receive diegetic handling, not an interface explanation.
- Player-facing prose should generally be second-person, present tense, terse, sensory, and cold.
- The Lyer should not be over-explained, trivialized, gamified, or defeated casually.

Forbidden patterns in player-facing prose:

- "Invalid command"
- "I don't understand that command"
- "You can't do that"
- "That is not a valid input"
- "As an AI"
- References to prompts, models, JSON, schemas, parsers, commands, tests, UI, or implementation details

## Review Procedure

1. Inspect the changed-file list first.
2. If the change is mechanical, rendering-only, layout-only, or test-only with no changed player-facing text or input/response behavior, return `PASS`.
3. Read only changed files and the minimum nearby context needed to decide whether changed text can reach the player.
4. Do not become a general prose critic.

## Output

Use one strict verdict:

- `PASS`: no actionable diegesis concern.
- `CONCERN`: likely problem, but not clearly game-breaking.
- `BLOCKER`: a player-facing fourth-wall leak or direct violation of the core contract.

Minor drift, polish, or low-risk observations are not findings. If those are all you find, return `PASS`.

Format:

```markdown
Diegesis Review: VERDICT

Reviewed changed files for diegetic immersion issues.

Blockers:
- None.

Concerns:
- None.

Notes:
- Reviewed changed files in scope; no other actionable diegesis findings found in this pass.
```

For findings, include the path, line when available, why it matters, and the smallest useful fix. Keep suggestions in the game's bleak, terse voice.
