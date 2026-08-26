# Research plan: temperature-controlled shader-spec evaluation

Status: pre-run design document  
Model/pricing snapshot: 2026-08-24

## Purpose

This study tests a reference-free coding-evaluation format: a model receives a natural-language
visual specification, generates a GLSL ES 3.0 shader, and is graded on properties measured from
controlled renders. The first public study is intended to establish strong groundwork, not a
definitive leaderboard or a general measure of spatial intelligence.

## Research questions

1. Can rendered properties accept independently written valid implementations without one
   reference image or an LLM judge?
2. Can the graders reject plausible near misses such as a wrong tile count, radius, direction, or
   rotational order?
3. Do model families differ in compile rate, clean completion, and partial property compliance?
4. How much does performance vary across repeated samples at a recorded nonzero temperature?

## Frozen sampling policy

The primary comparison includes only OpenRouter routes whose live catalog advertises both
`temperature` and `seed` support when the run is frozen.

- Temperature: `0.7`
- Seeds: ten distinct recorded seeds per task and model
- `top_p`: not changed; temperature and `top_p` are not tuned together
- Requests: stateless, with no tools, history, reference shader, render, or grader feedback
- Provider fallback: disabled
- Primary metric: first-attempt output
- Compiler repair: optional secondary metric, never merged into the primary score
- Transport errors: retry and report separately; never regenerate a valid low-scoring response

Nonzero temperature is this study's design choice for measuring output variability. It is not a
universal professional requirement. Deterministic evaluations are also legitimate. The important
professional practice is to define, record, and hold the decoding policy constant for the
comparison being claimed.

OpenAI's API documentation describes temperature as controlling randomness and recommends tuning
temperature or `top_p`, not both. OpenRouter exposes a per-model `supported_parameters` list; this
study uses that list as an eligibility gate instead of assuming that every provider honors the
same request fields.

## Primary model matrix

The machine-readable source of truth is
[`research/openrouter-temperature-study.json`](../research/openrouter-temperature-study.json).
On the snapshot date it selected:

| Route | Role | Input / 1M | Output / 1M |
| --- | --- | ---: | ---: |
| `google/gemini-3.7-flash` | Google family | $0.375 | $1.875 |
| `x-ai/grok-4.5` | xAI family | $2.00 | $6.00 |
| `qwen/qwen3-coder` | large coding model | $0.30 | $1.00 |
| `deepseek/deepseek-v3.2` | inexpensive independent family | $0.26 | $0.38 |
| `z-ai/glm-4.7-flash` | inexpensive independent family | $0.06 | $0.40 |
| `moonshotai/kimi-k2.7-code` | coding-oriented independent family | $0.67 | $3.40 |
| `ollama:qwen2.5-coder:14b` | existing local baseline | local | local |

Prices are planning observations, not permanent constants. The preflight command must save a new
catalog snapshot and refuse routes that no longer advertise the required parameters.

### Exclusions

`openai/gpt-5.6-sol` and `anthropic/claude-sonnet-5` are excluded from the primary comparison
because their OpenRouter entries did not advertise temperature support on the snapshot date. They
may be evaluated later under a clearly labeled provider-native protocol, but those results must
not be mixed into this temperature-controlled ranking.

## Run size and budget

The initial frozen target is 15 tasks, seven models including the local baseline, and ten samples:

```text
15 tasks x 7 models x 10 samples = 1,050 generated shaders
```

Current prompts and shader outputs are short. The six-model OpenRouter portion is expected to cost
less than $1 under the observed prices, but the operational ceiling remains $5 to cover reasoning
tokens, pilots, and price changes.

- Deposit no more than $5 of inference credit.
- Run catalog validation and a one-task pilot first.
- Store returned per-request tokens, cost, provider, and resolved model.
- Stop the runner when the configured cost ceiling is reached.
- Do not enable tools, web search, or unbounded output.

## Task controls

Every frozen task should include at least two independently structured valid shaders, two targeted
invalid shaders, and one plausible near miss. The second valid implementation tests implementation
independence. Near misses test whether the grader measures the exact requested property rather than
broad visual similarity.

Task definitions, thresholds, renderer settings, and controls must be frozen before paid outputs
are examined. A grader defect discovered later creates a new benchmark version and a complete
rerun, not a silent threshold change.

## Metrics

Report compile rate, clean completion, task-macro-averaged property compliance, per-task and
per-property results, failure categories, within-model variation, task-level 95% confidence
intervals, paired comparisons, tokens, latency, and cost.

Properties within one output are correlated and must not be presented as independent samples.
Small rank differences should not be interpreted when task-level uncertainty does not support the
ordering.

## Claims and limitations

The study may support claims that the project implements behavioral shader evaluation, accepts
multiple valid implementations, uses adversarial grader controls, and provides an initial small
cross-family comparison under an explicit sampling policy.

It must not claim that this is the first shader evaluation, that it measures general spatial
intelligence, that 15 tasks represent shader programming broadly, or that it establishes a
permanent model ranking.

## Required public artifacts

- frozen commit and release tag;
- tasks and control shaders;
- OpenRouter catalog snapshot;
- exact request configuration and provider policy;
- raw responses, shaders, compiler logs, renders, and property verdicts;
- environment and renderer metadata;
- analysis code and confidence intervals; and
- community result-submission instructions.

## Sources

- [OpenRouter model catalog and supported parameters](https://openrouter.ai/docs/guides/overview/models)
- [OpenRouter model-list API](https://openrouter.ai/docs/api/api-reference/models/get-models)
- [OpenRouter reasoning-token controls](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens)
- [OpenRouter pricing and credit fees](https://openrouter.ai/docs/faq)
- [OpenAI response sampling parameters](https://developers.openai.com/api/reference/cli/resources/responses/methods/create)

