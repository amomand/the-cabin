---
name: the-cabin-playtest-review
description: Review The Cabin's deterministic offline playtest transcripts, probe suspected experiential or story-state defects with new routes, de-duplicate against open playtest issues, and produce a validated no-op or at most three bounded issue findings. Use for manual or scheduled local Codex playtest reviews and guarded issue publication; never use it to implement fixes or rewrite story truth.
---

# The Cabin playtest review

Use `$local-agentic-control` for the claim, exact-source worktree, publication,
terminal ledger state, and cleanup. Read the exact-source `AGENTS.md` before
judging the game. The model reviews evidence; it does not generate story truth
or change product files.

## Prepare evidence

From the prepared worktree, run the shared guard before reading any evidence:

```bash
python3 "${HOME}/.codex/skills/local-agentic-control/scripts/workflow_guard.py" \
  prepare-evidence \
  --workflow cabin-playtest-review \
  --claim-id <run-id> \
  --repo-path <prepared-worktree> \
  --manifest-file /tmp/<run>/evidence-manifest.json
```

The guard extracts the committed preparer, runs every committed scenario with
model credentials removed, rejects any scheduled scenario that is not offline,
and records the manifest hash in the live claim before reviewer access. A
scenario `FAIL` is review evidence, not a preparation failure. Read the
manifest, then:

1. Read every listed report at `## Findings` and `## Story state at close`.
2. Read 3–4 complete transcripts: the golden path, a divergent route, and the
   reports with the strongest suspicious signal.
3. Read the staged plotline, Lyer lore, and both local review skills under
   `reports/playtests/_context/`. Do not hunt elsewhere for copies.
4. Read open `playtest` issues before drafting findings. Issue `#193` is the
   automation ledger, not a product finding.

## Judge and probe

Look for concrete player-visible or story-state failures that deterministic
assertions can miss: fourth-wall leakage, authored beats in the wrong order,
prose/state disagreement, unexplained health or fear movement, surface drift,
or narration that breaks the game's own voice rules.

Do not report the known repeated offline fallback line. Do not suggest that a
model should author story beats. Do not file a style preference or assume that
deliberate wrongness is a bug.

When a suspicion needs evidence, create a new scenario YAML beneath the
run-specific `/tmp` directory and run only that new route:

```bash
python3 -m tools.playtest_runner \
  /tmp/<run>/probe.yaml --report-dir reports/probes
```

Drop hypotheses that do not reproduce. List each probe report in the result.

## Produce and validate the result

Write `findings.json` as a JSON array containing zero to three objects with
exactly these string fields: `title`, `body`, `severity`, `evidence`, and
`reproduction`. Severity is one of `diegesis`, `continuity`, `balance`, or
`bug`. Do not include the `[playtest]` prefix; the publisher owns it.

Each non-empty issue body must use these headings and include its corresponding
evidence and reproduction text:

```markdown
## What's wrong

...

## Evidence

...

## Why it matters

...

## Reproduction

...
```

Write `result.json` with schema version 1, workflow
`cabin-playtest-review`, the live mode, outcome `noop` or `issues`, exact source
SHA, every manifest report in `reviewed_reports`, any probe report paths in
`probed_routes`, and a short summary.

Validate before any terminal action:

```bash
python3 \
  .agents/skills/the-cabin-playtest-review/scripts/validate_result.py \
  --mode <shadow-or-active> \
  --source-sha <full-sha> \
  --manifest /tmp/<run>/evidence-manifest.json \
  --result /tmp/<run>/result.json \
  --findings /tmp/<run>/findings.json
```

## Finish safely

- For a validated no-op, finish the claim as `noop`, passing `--repo-path`,
  `--manifest-file`, `--result-file`, and `--findings-file` to the guard.
- In shadow mode, finish validated findings as `shadow-change` with those same
  evidence arguments; publish nothing.
- In active mode, pass the evidence manifest, result and findings JSON to
  guarded `publish-issues` as `--manifest-file`, `--result-file` and
  `--payload-file`. Preview without `--apply`, inspect the plan, then apply the
  identical command. Finish as `issues` using the exact returned URL list.

Never edit tracked repository files, create branches, commit, push, comment,
close issues, fix findings, or call GitHub writes directly. Never merge. Always
attempt guarded cleanup; ignored evidence and probe reports are permitted, but
leave and report any worktree with unexpected tracked or unignored changes.
