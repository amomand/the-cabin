---
name: the-cabin-continuity-review
description: Run a local pre-PR review of The Cabin changes for concrete drift between implementation, tests, configuration, README, architecture docs, mechanics docs, lore docs, and story contracts.
---

# The Cabin Continuity Review

Use this skill before opening or updating a PR when a change touches behavior, tests, configuration, documentation, lore, mechanics, public commands, web-session behavior, or story-state contracts.

This is a local review skill. Do not post its output to GitHub automatically. Report the verdict in your PR summary or maintainer update.

## Scope

Review the branch diff against the mainline:

```bash
git diff --name-only origin/main...HEAD
git diff --stat origin/main...HEAD
```

If `origin/main...HEAD` is not available, use the best local base and state what you used.

Inspect only files changed by the branch, plus nearby authoritative files needed to verify a claimed contract.

Useful anchors:

- `game/config.py`
- `config.json.example`
- `README.md`
- `docs/architecture/architecture.md`
- `docs/architecture/developer-guide.md`
- `docs/game_mechanics/**`
- `docs/lore/plotline.md`
- `game/actions/**`
- `game/events/**`
- `game/world_state.py`
- `game/map.py`
- `server/session.py`
- `tests/**`

## What Counts

Report a finding only when the branch creates or preserves a specific contradiction that a maintainer can act on quickly.

High-signal examples:

- documented default model, env var, command, action list, or config key disagrees with code
- README or architecture docs describe behavior changed by the branch
- mechanics docs say a quest, item, event, room, save path, or state flag works differently from implementation
- lore or plot docs contradict newly added authored story beats
- tests lock in behavior that conflicts with docs the branch also touches
- server/web-session behavior diverges from terminal engine behavior where docs imply parity
- a renamed action, event, world-state field, room, item, or quest is updated in code but not in adjacent docs

## What Does Not Count

Ignore:

- docs that are merely incomplete
- docs that could be more polished
- TODOs or open questions unless the branch makes them false
- historical prose that is clearly background, not a current contract
- examples of old behavior used explicitly as "before" or "forbidden" examples
- broad architectural preferences
- purely visual or ordering changes that update their adjacent docs/tests consistently
- test-only changes that do not alter or contradict a documented contract
- diegetic tone issues unless there is also a concrete continuity contradiction

If the concern is only "this could use more documentation", do not report it.

## Review Procedure

1. Inspect the changed-file list first.
2. If the change is mechanical, rendering-only, layout-only, or test-only with no changed public contract, return `PASS`.
3. Open nearby authoritative files only when needed to verify a concrete suspected contradiction.
4. Do not expand into a general documentation review.

## Output

Use one strict verdict:

- `PASS`: no concrete continuity drift found.
- `CONCERN`: likely drift with a clear file-level fix.
- `BLOCKER`: drift that will mislead contributors or players about current behavior.

Minor drift, polish, or low-risk observations are not findings. If those are all you find, return `PASS`.

Format:

```markdown
Continuity Review: VERDICT

Reviewed changed files for continuity drift.

Blockers:
- None.

Concerns:
- None.

Notes:
- Reviewed changed files in scope; no other actionable continuity findings found in this pass.
```

For findings, include the conflicting paths, line numbers when available, what disagrees, why it matters, and the smallest useful fix.
