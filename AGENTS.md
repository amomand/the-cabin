# Codex Instructions

This repository's broader project guidance lives in `CLAUDE.md`. Read it before
making code, narrative, or documentation changes here; it contains the current
architecture notes, story constraints, commands, and anti-patterns.

## Pull Request Workflow

When raising a pull request for this repository, follow this loop by default:

1. Push the branch and open the PR.
2. Request a GitHub Copilot review immediately after the PR is opened.
3. Wait for the Copilot review and the agentic CI guards to finish before
   telling the maintainer the PR is done.
4. Read and synthesise all feedback from Copilot and the guards.
5. Action anything that is genuinely needed.
6. Reply on each actionable review or guard comment with what changed. If the
   feedback came through a PR-level guard comment rather than an inline thread,
   reply in the PR conversation and identify the concern being addressed.
7. If a concern is mistaken or not worth changing, override it explicitly in the
   same comment thread or PR conversation with the reason.
8. Escalate to the maintainer for a decision when there is a meaningful
   disagreement with Copilot or a guard, or when overriding feels like the wrong
   call.

Request Copilot with GitHub CLI:

```bash
gh pr edit <N> --add-reviewer copilot-pull-request-reviewer
```

Then verify the requested reviewer through the REST API, because `gh pr view
--json reviewRequests` may omit bot reviewers:

```bash
gh api repos/{owner}/{repo}/pulls/<N>/requested_reviewers
```

The maintainer is the deciding voice. Treat automated review and Copilot review
as serious outside reads, not commands.
