# Protocol amendment: v0.3 output allowance

The v0.2 one-task pilot was completed and preserved in
`results/openrouter-pilot-v0.2`. No full v0.2 study was started.

The pilot showed that the 1,024-token response allowance can include hidden
reasoning tokens. `z-ai/glm-4.7-flash` used all 1,024 completion tokens, of
which 853 were reported as reasoning tokens, and emitted no shader source.
This would confound shader-generation ability with whether a route's default
reasoning process fits inside an unusually small response budget.

Before any full study calls, v0.3 changes only `max_output_tokens` from 1,024
to 2,048. Temperature, seed schedule, prompts, tasks, graders, provider
fallback policy, and first-attempt scoring remain unchanged. The v0.2 pilot
cells are not reused in v0.3. The conservative catalog projection remains
below the predeclared $5 ceiling.
