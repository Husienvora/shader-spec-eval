# Eligibility amendment: GLM response-budget incompatibility

The full v0.3 run was paused after 87 `z-ai/glm-4.7-flash` cells. GLM is
excluded from the primary model comparison because the fixed response budget
was primarily consumed by its default reasoning process:

- 52 of 87 responses reached the 2,048-token response cap;
- 46 emitted no shader source;
- the completed GLM cells averaged 1,539 reported reasoning tokens at the
  time the issue was diagnosed.

This pattern confounds shader-generation ability with route-specific default
reasoning overhead. The 87 cells remain in the raw evidence and must be
reported as a protocol-compatibility finding, not silently deleted or scored
as an ordinary model ranking. No GLM cell will be regenerated under a changed
budget or reasoning configuration in v0.3.
