# Operational amendment: hosted-model execution order

After 100 of 150 Gemini cells had been checkpointed, the hosted-model execution
order was changed to prioritize inexpensive routes under the fixed $5 ceiling.
No prompt, seed, temperature, response allowance, task, grader, or scoring rule
changed. No completed cell was discarded or regenerated.

The resumed order is:

1. finish `google/gemini-3.7-flash`;
2. `z-ai/glm-4.7-flash`;
3. `moonshotai/kimi-k2.7-code`;
4. `x-ai/grok-4.5`;
5. `deepseek/deepseek-v3.2`;
6. `qwen/qwen3-coder`;
7. the local `qwen2.5-coder:14b` baseline.

The checkpoint was paused at a valid 115-cell file: 15 human references and
100 Gemini generations. A pre-change backup is stored beside the live results
as `shader-cells.pre-reorder-backup.json`.
