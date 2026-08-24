# Evaluation design

## What the score means

Each task begins with a natural-language specification and a machine-readable list of properties.
The model returns one GLSL ES 3.0 `mainImage` implementation. Chromium's SwiftShader renderer
evaluates it at controlled dimensions and time values. Property functions inspect the rendered
frames rather than comparing source code or requiring one reference image.

This establishes **behavioral compliance at the sampled points**. It does not establish the
model's internal reasoning process, aesthetic quality, or universal correctness at every
resolution and time.

## Why property checks?

A reference-image metric has two symmetrical failure modes:

1. It penalizes a valid implementation for harmless pixel-level differences.
2. A visually similar result can hide a wrong period, radius, direction, or time dependency.

Properties target claims from the prompt directly. Examples include:

- brightness increases along the x-axis;
- a centered boundary has radius 0.30 in every sampled direction;
- a rotation by 60 degrees preserves angular structure, while 30 degrees does not;
- shifting by the requested tile period preserves the image;
- frames differ or remain stable across controlled time samples.

## Controls

`shader-spec-eval selftest` is a test of the grader, not a model benchmark. Known-good reference
shaders must satisfy every property. Deliberately broken shaders must fail the intended property.

Controls include both obvious failures and near misses. The latter matter most: an early version
accepted a 16×16 checkerboard as exactly 8×8, a centered square as a circle, and a 12-fold flower
as exactly six-fold. Those cases remain in the repository as regression tests.

## Sampling policy

The default temperature is explicitly `0.7`. Repeated runs increment a recorded base seed. A
fixed seed and temperature zero would measure deterministic replay rather than normal output
variance.

Transient provider failures are excluded from model-quality aggregates. Compile failures may
receive one repair attempt containing both the compiler log and previous shader source. A low
property score never triggers a retry.

## Aggregation

Properties are averaged within a task, then tasks are averaged within a run. This prevents a task
with more checks from automatically dominating the aggregate. Always report clean completions
beside property compliance: the checks are correlated and generic sanity checks can inflate a
partial score.

## What would make this a validated benchmark?

The current project is exploratory. Stronger evidence requires a larger held-out task set,
positive and negative controls for every checker, multiple model families, repeated seeds,
cross-platform renderer checks, confidence intervals, rank-stability analysis, and comparison
with independent spatial and coding evaluations.
