# Codex Instructions

This repository's broader project guidance lives in `CLAUDE.md`. Read it before
making code, narrative, or documentation changes here; it contains the current
architecture notes, story constraints, commands, and anti-patterns.

## Pull Request Workflow

The hosted gh-aw guard workflows are disabled in this repo. Before raising a
pull request, run the relevant local review skills and include their verdicts in
your PR summary or maintainer update:

- `.codex/skills/the-cabin-diegesis-review/SKILL.md` for player-facing prose,
  authored story beats, playable HTML, input handling, rendering, or response
  behavior.
- `.codex/skills/the-cabin-continuity-review/SKILL.md` for behavior, tests,
  configuration, documentation, lore, mechanics, public commands, web-session
  behavior, or story-state contracts.

When raising a pull request for this repository, follow this loop by default:

1. Describe the intended flow briefly, including which local review skills apply.
2. Run tests and the relevant local review skills before pushing.
3. Push the branch and open the PR.
4. Request a GitHub Copilot review immediately after the PR is opened.
5. Wait for the Copilot review on the latest head commit before telling the
   maintainer the PR is done.
6. Read and synthesise all Copilot feedback.
7. Action anything that is genuinely needed.
8. Reply on each actionable review comment with what changed.
9. If a concern is mistaken or not worth changing, override it explicitly in the
   same comment thread with the reason.
10. Escalate to the maintainer for a decision when there is a meaningful
    disagreement with Copilot, or when overriding feels like the wrong call.

Request Copilot with GitHub CLI:

```bash
gh pr edit <N> --add-reviewer copilot-pull-request-reviewer
```

Then verify the requested reviewer through the REST API, because `gh pr view
--json reviewRequests` may omit bot reviewers:

```bash
gh api repos/{owner}/{repo}/pulls/<N>/requested_reviewers
```

The maintainer is the deciding voice. Treat local review skills as disciplined
self-review and Copilot review as a serious outside read, not a command.
