# Agentic playtest review

The weekly playtest review and its daily missed-run recovery both run locally
through Codex scheduled tasks. The guard, ledger and publishers remain
runner-agnostic. Together they keep
the useful stopping point of the former gh-aw workflow: the reviewer may file a
small number of issues, but it never changes the game or implements a fix.

The disabled `.github/workflows/playtest-review.md` and compiled lock file stay
in the repository as a reversible fallback. They are design history, not a
second live writer.

## Flow

1. The Friday task and daily recovery read both ledgers and select at most one due
   workflow. A null result stops quietly. A selected `now-rollup` is reported
   without action; a selected `cabin-playtest-review` continues through the
   same guarded review contract as Friday.
2. The Friday scheduled task or daily recovery acquires the exact selected
   `origin/main` SHA and prepares a clean detached worktree through
   `local-agentic-control`.
3. Guarded `prepare-evidence` extracts the committed repo preparer, rejects
   non-offline scheduled scenarios, removes model credentials from the runner,
   writes the transcript and context pack, runs the full iOS XCTest lane, then
   anchors the manifest digest in the live claim before reviewer access.
4. The reviewer reads every full transcript, checks the staged story
   constraints and open playtest issues, then chooses two rotation-tracked
   probes. Guarded `prepare-probes` runs exactly those offline both-surface
   scenarios and anchors a second manifest digest in the live claim. A changed
   source produces a regression review; the same source at a new weekly
   boundary produces an experiential review rather than being suppressed.
5. The anchored iOS lane runs on an iPhone Air simulator and includes the real
   `LocalEngineTransport` bridge into bundled Python. Live model turns and
   physical-device behaviour remain separate human boundaries.
6. The repo-local validator binds the result, retained baseline and probe
   transcript contents, transcript hashes, iOS log, and staged context blobs to
   the two guard-owned manifests and exact claim. It permits a no-op, a
   first-class coverage gap, or at most three structured findings.
7. `local-agentic-control publish-issues` first requires the manifest to match
   the guard-owned digest, then extracts the trusted validator from that source
   and rechecks the result, findings, clean worktree, live branch SHA, claim,
   title prefix, label, count and duplicate fingerprints before it can create
   issues. Guarded no-op and shadow terminal updates enforce the same evidence
   binding. A published terminal update records only the URLs returned by the
   publisher.

## Boundaries

- **Evidence first.** Transcripts come from the deterministic offline runner.
  FAIL reports remain evidence for the reviewer.
- **One write path.** The scheduled task cannot push, open pull requests,
  comment, close issues or merge. Its only product output is zero to three open
  `[playtest]` issues created by the guarded publisher.
- **Exact source.** Claims, evidence, validation and publication must agree on
  the same current `origin/main` commit.
- **Pre-review evidence anchor.** The reviewer cannot replace its transcript
  pack and still record a successful terminal outcome or publish a finding.
- **Post-review evidence anchor.** The reviewer chooses probe scenarios but
  cannot write their reports or assert an iOS pass. The guard runs both lanes
  and binds their manifests before terminal success or publication.
- **Durable evidence.** The local run directory survives worktree cleanup. Its
  manifest retains every baseline transcript; its result retains probe reports,
  and the iOS lane retains the xcodebuild log and result bundle.
- **No story ownership.** The reviewer may identify a concrete break but may
  not ask a model to author scenes, rewrite voice, or decide story truth.
- **Quiet success.** A clean run updates the ledger as `noop` and creates no
  issue.
- **Honest gaps.** A clean finding set with an unavailable or failed automated
  lane records `coverage-gap`, never `noop`.
- **Human stop.** Two failures against the same source move the ledger to
  `needs-human`. The old workflow remains disabled until a maintainer chooses
  rollback.

## Operations

The ledger boundary is Friday at 19:20 Europe/London. The normal Codex task
runs after that boundary; the daily Codex task recovers a missed boundary.
Local execution means the Mac and desktop app must be running. Missed schedules
coalesce into one overdue candidate rather than replaying as a backlog. The
daily recovery may claim and complete that Cabin candidate on its next local
run; it never recovers the Now roll-up.

The guard's `sweep` command remains read-only. Recovery authority belongs to
the scheduled task after it receives the sweep's exact candidate and source
SHA. It may not use `manual-claim`, change lifecycle configuration, or bypass
the guarded publication path.

The shared guard lives at `~/.claude/skills/local-agentic-control`; the Codex
path is a symlink to that canonical copy. The repo-local judgement skill is
committed under `.agents/skills/` and discovered by Codex from the checkout.

The skill expects the repository virtual environment at
`/Users/alexomand/repos/the-cabin/.venv`. It writes reports and probe artifacts
to ignored repository paths. Durable run evidence and the machine-readable
coverage history live under the Friday automation directory. The prepared
worktree is removed after a clean terminal outcome.

Rollback is deliberately small: pause the scheduled task, move ledger `#193`
back to `shadow` or `inactive` with writes disabled, and re-enable the retained
GitHub workflow. Never run both issue writers at once.
