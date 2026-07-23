# Agentic playtest review

The weekly playtest review is the one hosted agentic workflow in this repo. It
borrows the shape that worked in Custodian's repair loop, deliberately stopping
at the first stage: a scheduled reviewer that files issues, and nothing that
writes code.

## What it does

`.github/workflows/playtest-review.md` (compiled to `playtest-review.lock.yml`
by gh-aw) runs weekly and on manual dispatch:

1. A deterministic pre-step runs every scenario in `playtests/scenarios/`
   offline and writes full reports — transcript, findings, and the
   `## Story state at close` block — to `reports/playtests/`. A failing
   scenario still reaches the reviewer; a FAIL report is evidence.
2. The same pre-step stages a source pack under `reports/playtests/_context/`:
   the story-truth modules, the plotline snapshot, the Lyer lore doc, and both
   local review skills. The reviewer reads staged files instead of exploring
   the tree (Custodian's first hosted run spent about half its turns hunting
   source).
3. The agent reads the evidence, probes hypotheses by writing NEW ad-hoc
   scenario files and re-running the runner, checks open issues to avoid
   re-filing, and files at most three `[playtest]`-labelled issues with
   evidence, reproduction, and a severity (`diegesis`, `continuity`,
   `balance`, `bug`).

## Boundaries

- **Evidence first.** The model never generates the transcripts it reviews.
  Playtest evidence comes from the deterministic offline runner; the agent's
  job is judgement over that evidence. This mirrors the game's own rule:
  authored prose is canonical, AI interprets.
- **Read-only, one write path.** Workflow permissions are read-only; the only
  safe output is issue creation. No pushes, no PRs, no comments, no merges.
- **Out of the PR critical path.** This is not a guard workflow and does not
  gate anything. The hosted gh-aw guard reviewers remain disabled; pre-PR
  review stays with the local skills and Copilot per `CLAUDE.md`.
- **Off switch.** Delete or disable the workflow file; nothing else depends on
  it.

## Deliberately not borrowed from Custodian

Custodian's loop continues past issues: an implementer opens draft fix PRs,
specialist reviewers and Copilot review them, a deterministic barrier joins the
reviews, an adjudicator resolves threads, and a doorbell flips clean PRs to
ready. The Cabin does not adopt any of that, for three reasons:

- The Cabin's fix surface is mostly authored prose and story beats, where the
  maintainer is the deciding voice. Agent-authored fix PRs would sit badly with
  that.
- The local-skills-plus-Copilot loop already covers PR review here.
- The machinery cost Custodian several hardening PRs (token routing, barrier
  crashes, watchdog escalation) before it ran clean. That tax only pays when
  the fixes are mechanical and frequent.

If an implementer ever earns its place, scope it to mechanical findings only
(state contracts, flag logic, save handling) — never voice or story beats — and
adopt Custodian's deterministic-join and terminal-state design as-is rather
than reinventing it.

## Operating notes

- Edit the `.md` workflow, never the generated `.lock.yml`. Recompile with the
  current gh-aw release: `gh aw compile --validate`.
- The workflow needs one repository secret: `COPILOT_GITHUB_TOKEN`, a
  fine-grained PAT whose only permission is the account-level
  `Copilot Requests: Read`. It is the inference credential for the Copilot
  engine; repository writes use the per-run `GITHUB_TOKEN` under the compiled
  safe-output permissions.
- The runner scenarios the reviewer reads are the same ones CI runs, so a
  scenario added for CI regression coverage automatically widens the weekly
  review's evidence.
