# Harness amendment: versioned `mainImage` responses

The Kimi compatibility gate revealed that the renderer prepended its GLSL
prelude to responses containing both a leading `#version` directive and a
`mainImage` function. That produced two version directives and a compiler
error even though the model had returned substantive shader source.

The harness now removes only a leading `#version` line before wrapping a
`mainImage` response. It does not remove uniform declarations, repair syntax,
or otherwise change generated code. Full shaders containing `main()` continue
to run as supplied.

This is a harness correction, so cached sources must be re-rendered under the
amended harness before final aggregation. Model API responses do not need to
be regenerated. The original sources, responses, token usage, cost, and
pre-amendment compile logs remain recoverable from checkpoint backups.
