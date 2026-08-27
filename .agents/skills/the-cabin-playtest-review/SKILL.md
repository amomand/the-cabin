---
name: the-cabin-playtest-review
description: Review The Cabin through retained deterministic terminal/web transcripts, rotating exploratory probes, and the bundled-engine iOS simulator lane; publish at most three guarded issues or record a validated no-op or coverage gap. Use for manual or scheduled playtest reviews, never to implement fixes or rewrite story truth.
---

# The Cabin playtest review

Use `local-agentic-control` for the claim, exact-source worktree, evidence
binding, publication, terminal ledger state, and cleanup. Read the exact-source
`AGENTS.md` before judging the game. The reviewer identifies defects; it does
not change product files or author story truth.

## Review kind and retained run directory

The guarded evidence manifest names the run:

- `regression`: the selected source differs from the previous successful source.
- `experiential`: the weekly boundary selected the same source again.

Use one persistent directory beneath
`~/.codex/automations/friday-cabin-playtest-review/evidence/<run-id>/` for the
manifest, probe YAML, iOS evidence, result, and findings. The manifest itself
retains every baseline transcript; `result.json` retains every probe report.
Do not put credentials, raw model payloads, saves, or resume handles there.

## Prepare and read the terminal/web evidence

From the prepared worktree, run guarded `prepare-evidence` before reading any
report. Pass the persistent manifest path:

```bash
python3 ~/.codex/skills/local-agentic-control/scripts/workflow_guard.py \
  prepare-evidence \
  --workflow cabin-playtest-review \
  --claim-id <run-id> \
  --repo-path <prepared-worktree> \
  --manifest-file <run-directory>/evidence-manifest.json
```

The guard removes model credentials, runs every committed offline scenario and
the iOS simulator lane, then anchors the schema-v2 manifest hash in the claim.
The manifest records the previous source, review kind, changed paths,
change-area counts, full baseline transcripts, and the helper-produced iOS
evidence. A scenario `FAIL` remains review evidence.

Read every complete transcript, not merely its generated findings and closing
state. Judge command/response flow, authored beat order, state/prose agreement,
fear and health movement, diegesis, and terminal/web parity. Read all staged
context. Check open `playtest` issues before drafting findings; issue `#193` is
the ledger, not a product defect.

## Run two rotating probes

Every selected review runs at least two both-surface probes, even if the
baseline already looks clean.

- For a regression review, one probe targets the riskiest player-reachable
  changed area in the manifest. If the dominant change is outside terminal/web,
  state that limitation and probe the nearest shared engine boundary.
- For an experiential review, both probes explore coverage not exercised by the
  previous successful run.
- The probes must use different families chosen from `ending`, `free-text`,
  `guidance`, `movement`, `save-load`, `state-consequence`, `story-transition`,
  `surface-parity`, and `utility`.

Read the automation's `coverage-history.json` before choosing probes. Do not
repeat either of the immediately previous run's families or routes unless a
new source change directly requires it. Write YAML only in the persistent run
directory. After choosing both scenarios, make the guard run and anchor them:

```bash
python3 ~/.codex/skills/local-agentic-control/scripts/workflow_guard.py \
  prepare-probes \
  --workflow cabin-playtest-review \
  --claim-id <run-id> \
  --repo-path <prepared-worktree> \
  --manifest-file <run-directory>/probe-manifest.json \
  --probe <family>=<run-directory>/first.yaml \
  --probe <family>=<run-directory>/second.yaml
```

The guard extracts the committed probe preparer, requires exactly two unique
offline `both`-surface scenarios and families, runs them with model credentials
removed, retains their full reports, and binds the probe-manifest hash in the
live claim. Only then read the reports. Drop hypotheses that do not reproduce,
but copy the manifest's report paths, hashes, contents, and families exactly
into `result.json`.

## Run the iOS simulator lane

Guarded baseline preparation already runs the committed helper. It scrubs model
credentials, refreshes an exact-source bundled Python payload, and runs the
full XCTest suite on the `iPhone Air` simulator. That includes the real
`LocalEngineTransport` bridge into bundled Python, not only mocks. Inspect the
manifest's anchored result and retained xcodebuild log and result bundle. A
failed or unavailable lane is not a workflow crash: record `coverage-gap`
unless a concrete product finding takes precedence.

Physical-device behaviour and live-model turns remain explicit uncovered
areas. Never obtain, expose, or use a model credential from a scheduled run.

## Produce schema-v2 results

`findings.json` remains a zero-to-three item array. Each item has exactly the
string fields `title`, `body`, `severity`, `evidence`, and `reproduction`.
Severity is `diegesis`, `continuity`, `balance`, or `bug`; the publisher owns
the `[playtest]` prefix. Bodies use these headings in order:

```markdown
## What's wrong

## Evidence

## Why it matters

## Reproduction
```

`result.json` has schema version 2 and exactly these fields:

- workflow, mode, review kind, outcome, source SHA, and previous source SHA
- every reviewed baseline report
- two to four probe routes, their retained evidence, and unique probe families
- `terminal_web_status` matching the manifest runner
- the complete `ios_evidence` object returned by the helper
- `live_model_status: "not-run"`
- sorted `uncovered_areas`, always including `ios-device` and `live-model`
- a concise summary that names coverage limitations

Outcome rules:

- `issues`: one to three reproducible findings; this takes precedence over a
  simultaneous coverage gap.
- `noop`: no findings, terminal/web runner clean, and iOS simulator lane passed.
- `coverage-gap`: no findings, but terminal/web failed or the iOS lane failed or
  was unavailable. Include `ios-simulator` in `uncovered_areas` when applicable.

Validate with the committed validator before any terminal action:

```bash
python3 \
  .agents/skills/the-cabin-playtest-review/scripts/validate_result.py \
  --mode <shadow-or-active> \
  --source-sha <full-sha> \
  --manifest <run-directory>/evidence-manifest.json \
  --probe-manifest <run-directory>/probe-manifest.json \
  --result <run-directory>/result.json \
  --findings <run-directory>/findings.json
```

## Finish safely

- `noop` and `coverage-gap`: preview and apply guarded `finish`, passing the
  exact worktree, baseline manifest, probe manifest, result, and findings paths.
- Findings in shadow mode: finish as `shadow-change` with the same evidence.
- Findings in active mode: preview and apply guarded `publish-issues`, then
  finish as `issues` using only the returned URL list.
- Genuine execution or validation failure: finish as `failed`.

After terminal success, append the run to the rotation history atomically:

```bash
python3 \
  .agents/skills/the-cabin-playtest-review/scripts/record_coverage.py \
  --history ~/.codex/automations/friday-cabin-playtest-review/coverage-history.json \
  --run-id <run-id> \
  --recorded-at <ISO-8601-time> \
  --manifest <run-directory>/evidence-manifest.json \
  --probe-manifest <run-directory>/probe-manifest.json \
  --result <run-directory>/result.json \
  [--issue-url <guard-returned-url> ...]
```

The history records source SHAs, probes, lane statuses, manifest hash, outcome,
issue URLs, and evidence path. It rotates coverage but never overrides the
GitHub ledger. Do not record a run before its guarded terminal action succeeds.

Never edit tracked product files, create a branch, commit, push, comment, close
issues, implement findings, or call GitHub writes directly. Never merge. Always
attempt guarded cleanup; leave and report any unexpectedly dirty worktree.
