# OpenRouter study runbook

This is the exact checklist for the frozen `temperature-controlled-v0.2` study. The command is a
dry run unless `--execute` is present. Paid runs checkpoint after every model response and resume
from the same output directory.

## 1. Install and check the environment

From the repository root in Windows PowerShell:

```powershell
python -m pip install -e ".[dev]"
python -m playwright install chromium
shader-spec-eval doctor
shader-spec-eval selftest
```

Keep Ollama running with the local baseline installed:

```powershell
ollama pull qwen2.5-coder:14b
```

## 2. Set the key locally

Set the key in the terminal that will run the study. Do not paste it into chat, commit it, or put it
in a command saved to shell history.

```powershell
$shaderEvalKey = Read-Host "OpenRouter API key" -AsSecureString
$env:OPENROUTER_API_KEY = [Net.NetworkCredential]::new('', $shaderEvalKey).Password
```

The repository ignores `.env` files, but this workflow does not require one.

## 3. Validate the live catalog and price projection

```powershell
shader-spec-eval openrouter-study --no-open
```

This sends no model requests. It verifies that every paid route still advertises `temperature` and
`seed`, prints current catalog prices, estimates the conservative maximum, and refuses a projected
run over the manifest's $5 ceiling.

## 4. Run the pilot

```powershell
shader-spec-eval openrouter-study --execute --pilot --no-open `
  --output-dir results/openrouter-pilot-v0.2
```

The pilot runs one task once for each paid model and the local baseline. Check that:

- every route returns a shader rather than a provider error;
- `cost_usd`, token counts, resolved model, and provider are present for hosted responses;
- the local Ollama model is reachable; and
- the renderer produces verdicts and PNGs.

Do not tune task thresholds after seeing model failures. Fix only genuine infrastructure defects;
if a frozen grader changes, increment the benchmark version and rerun all affected outputs.

## 5. Run or resume the full study

```powershell
shader-spec-eval openrouter-study --execute --no-open `
  --output-dir results/openrouter-temperature-v0.2
```

If the terminal, network, or machine stops, repeat the identical command. Existing cells are read
from `shader-cells.json`; completed model/task/seed combinations are skipped. Never change the
manifest while resuming a directory.

Primary outputs are:

- `shader-cells.json` — raw responses, extracted shaders, render verdicts, sampling settings,
  usage, cost, resolved model, and provider;
- `shader-dashboard.html` — inspectable renders and scores;
- `openrouter-catalog-snapshot.json` — the catalog metadata used by preflight; and
- `run-config.json` — the frozen runtime configuration.

## 6. Preserve the evidence

Before quoting results, record the Git commit, archive the complete output directory, and inspect
provider errors separately from compile or property failures. Report first-attempt results as the
primary metric. Do not compare a repaired shader against an unrepaired shader in the same score.
