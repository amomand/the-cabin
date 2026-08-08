# Agentic playtest review

The weekly playtest review runs locally through Codex Scheduled tasks. It keeps
the useful stopping point of the former gh-aw workflow: the reviewer may file a
small number of issues, but it never changes the game or implements a fix.

The disabled `.github/workflows/playtest-review.md` and compiled lock file stay
in the repository as a reversible fallback. They are design history, not a
second live writer.

## Flow

1. The daily local sweep reads ledger issue `#193` and selects at most one due
   workflow. It never claims or publishes by itself.
2. The Friday Scheduled task acquires the exact selected `origin/main` SHA and
   prepares a clean detached worktree through `local-agentic-control`.
3. `.agents/skills/the-cabin-playtest-review/scripts/prepare_evidence.py` runs
   every committed scenario offline, writes transcript reports, and stages the
   story-truth source pack beneath `reports/playtests/_context/`.
4. Codex reads every report at findings/state level, reads the most revealing
   full transcripts, checks the staged story constraints and open playtest
   issues, then probes only suspected gaps with new routes.
5. The repo-local validator binds the result and evidence manifest to the exact
   claim and permits a no-op or at most three structured findings.
6. `local-agentic-control publish-issues` rechecks the clean source, live branch
   SHA, claim, title prefix, label, count and duplicate fingerprints before it
   can create issues. A separate terminal update records only the URLs returned
   by that publisher.

## Boundaries

- **Evidence first.** Transcripts come from the deterministic offline runner.
  FAIL reports remain evidence for the reviewer.
- **One write path.** The Scheduled task cannot push, open pull requests,
  comment, close issues or merge. Its only product output is zero to three open
  `[playtest]` issues created by the guarded publisher.
- **Exact source.** Claims, evidence, validation and publication must agree on
  the same current `origin/main` commit.
- **No story ownership.** The reviewer may identify a concrete break but may
  not ask a model to author scenes, rewrite voice, or decide story truth.
- **Quiet success.** A clean run updates the ledger as `noop` and creates no
  issue.
- **Human stop.** Two failures against the same source move the ledger to
  `needs-human`. The old workflow remains disabled until a maintainer chooses
  rollback.

## Operations

The task is scheduled for Friday at 19:20 Europe/London. Local execution means
the Mac and desktop app must be running. Missed schedules coalesce through the
daily sweep; they never replay as a backlog.

The skill expects the repository virtual environment at
`/Users/alexomand/repos/the-cabin/.venv`. It writes reports and probe artifacts
only to ignored repository paths and run-specific `/tmp` paths. The prepared
worktree is removed after a clean terminal outcome.

Rollback is deliberately small: pause the Scheduled task, move ledger `#193`
back to `shadow` or `inactive` with writes disabled, and re-enable the retained
GitHub workflow. Never run both issue writers at once.
