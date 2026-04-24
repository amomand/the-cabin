# AI Model Evaluation

Use the model evaluation harness to compare interpreter models against fixed
diegetic-input scenarios.

The harness measures:

- latency per request
- JSON/schema success
- expected action classification
- expected fear/health effect presence
- rough tone fit
- rough interestingness

The tone and interestingness scores are heuristics, not truth. Treat them as a
triage signal, then read the sample replies in `summary.md`.

## Run

```bash
python -m game.devtools.model_eval --runs 1
```

By default this compares:

- `gpt-4.1-mini`
- `gpt-5-mini:minimal`
- `gpt-5-mini:low`
- `gpt-5.4-mini:none`
- `gpt-5.4-nano:none`

`gpt-5.5:none` is intentionally not in the default sweep because it is a
larger model and can make routine comparison runs noisier and more expensive.
Add it explicitly when you want to test the non-reasoning path:

```bash
python -m game.devtools.model_eval \
  --models gpt-4.1-mini,gpt-5.4-mini:none,gpt-5.5:none \
  --runs 1
```

Outputs are written to a timestamped directory under `reports/model_eval/`:

- `summary.md` for human review
- `summary.json` for aggregate numbers
- `raw_results.jsonl` for every raw model response

## Custom Runs

```bash
python -m game.devtools.model_eval \
  --models gpt-4.1-mini,gpt-5.4-mini:none \
  --runs 3
```

Model specs are `model`, `model:reasoning_effort`, or
`provider:model:reasoning_effort`. Only `openai` is implemented in phase one,
but the provider field is already part of the data model for Anthropic/Gemini
adapters later.

For a cheap smoke test:

```bash
python -m game.devtools.model_eval \
  --models gpt-4.1-mini,gpt-5-mini:minimal \
  --max-scenarios 1 \
  --runs 1
```

For a no-cost check of what would run:

```bash
python -m game.devtools.model_eval --dry-run
```

## Reading Results

Prioritize in this order:

1. OK rate should be 1.0.
2. Action match should be high. Misclassifying `look`, movement, or `none`
   can change gameplay behavior.
3. Latency should stay below the point where the terminal feels stalled.
4. Tone and interestingness should be checked by reading the sample replies,
   because the numeric score cannot judge the actual voice.

If a model is fast but misclassifies creative input, keep it as an experiment,
not the default.
