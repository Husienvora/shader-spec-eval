# Reproducible runs and result submissions

## Minimum run

Use at least three repeats for an exploratory result and five or more for comparisons:

```bash
shader-spec-eval --temperature 0.7 --seed 7 run \
  --models YOUR_MODEL \
  --repeats 5 \
  --no-open \
  --output-dir results/YOUR_MODEL
```

Run the self-test immediately beforehand. Do not submit model results from a revision where the
self-test fails.

## Record with every result

- repository commit SHA;
- exact provider model ID and revision/digest;
- quantization, when local;
- temperature, base seed, and repeat count;
- Ollama/server/provider version;
- operating system, CPU, GPU, and driver;
- Python and Playwright versions;
- whether any cell received a compile repair;
- raw `shader-cells.json`, not only the aggregate score.

For Ollama, useful commands include:

```bash
ollama list
ollama show YOUR_MODEL
```

## Comparing models

Use the same repository commit, tasks, renderer, temperature, seed sequence, and repeat count.
Run models in a randomized or interleaved order when provider conditions might change over time.
Report transient failures separately.

Do not rank gaps smaller than run-to-run uncertainty. Report property compliance, clean completion,
per-task results, and confidence intervals together.

## Regenerate a dashboard without model calls

```bash
shader-spec-eval dashboard \
  --cells results/YOUR_MODEL/shader-cells.json \
  --output results/YOUR_MODEL/shader-dashboard.html \
  --no-open
```

Cached cells preserve the property verdicts from the original run. If task definitions or grader
code change, rerun the benchmark rather than presenting an old cache as a new evaluation.
