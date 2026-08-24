# Adding tasks and properties

## Task layout

Create:

```text
tasks/shader-example/
├── task.json
└── seed/
    ├── shader.glsl
    └── shader_spec.json
```

`task.json` contains the public natural-language prompt:

```json
{
  "id": "shader-example",
  "description": "What capability this task isolates.",
  "prompt": "Write a GLSL ES 3.0 fragment shader ...",
  "context": ["*.glsl", "*.json"],
  "verify": ["python", "-m", "shader_spec_eval.shader.verify", "shader_spec.json"]
}
```

`shader_spec.json` selects render conditions and properties:

```json
{
  "file": "shader.glsl",
  "size": 256,
  "times": [0.0, 0.7, 1.4],
  "properties": [
    {"check": "not_blank"},
    {"check": "stable_over_time", "max_delta": 3.0}
  ]
}
```

Add the task ID and its reference file to `DEFAULT_TASKS` and `REFERENCES` in
`shader_spec_eval/cli.py`.

## Adding a property

1. Implement a function returning `Check` in `shader_spec_eval/shader/assertions.py`.
2. Register it in `FRAME_CHECKS` or `RESULT_CHECKS`.
3. Add it to a task specification.
4. Add at least one known-good reference and one deliberately broken control.
5. Register those controls in `shader_spec_eval/shader/selftest.py`.
6. Run `shader-spec-eval selftest` before benchmarking a model.

Choose thresholds using development controls, then evaluate them on separate held-out controls.
Do not tune a threshold until one preferred model passes.

## Property design checklist

A useful property should:

- follow directly from words in the public prompt;
- permit multiple valid GLSL implementations;
- reject plausible near misses;
- tolerate small rasterization differences;
- avoid relying on one pixel when a region statistic is possible;
- state its threshold and measured detail in the result;
- have adversarial positive and negative tests.
