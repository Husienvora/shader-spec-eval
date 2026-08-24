"""Validate the eval itself.

An eval nobody has checked is not a measurement, it is a rumour. This renders
shaders whose answers are already known and asserts the harness agrees:

  * reference shaders must PASS every property in their spec
  * deliberately broken shaders must FAIL the specific property they violate

If a known-good shader fails here, the harness is wrong — not the model. Run
this before trusting a single benchmark number, and run it on camera.

    python -m shader_spec_eval.shader.selftest
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .assertions import evaluate
from .render import render

REF = Path(__file__).parent / "reference"
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_TASKS = PACKAGE_ROOT.parent / "tasks"
TASKS = REPOSITORY_TASKS if REPOSITORY_TASKS.is_dir() else PACKAGE_ROOT / "tasks"


def load_spec(task_id: str) -> dict:
    return json.loads((TASKS / task_id / "seed" / "shader_spec.json").read_text(encoding="utf-8"))


# (shader file, spec from this task, properties expected to fail)
CASES: list[tuple[str, str, set[str]]] = [
    ("pulse.glsl",            "shader-pulse",    set()),
    ("gradient.glsl",         "shader-gradient", set()),
    ("BAD_blank.glsl",        "shader-pulse",    {"not_blank", "radial_falloff",
                                                  "dominant_channel(b)", "animates"}),
    ("BAD_static_pulse.glsl", "shader-pulse",    {"animates"}),
    ("BAD_inverted_pulse.glsl", "shader-pulse",  {"radial_falloff"}),
    ("BAD_wrong_axis.glsl",   "shader-gradient", {"gradient_x_increasing"}),
    ("BAD_periodic_gradient.glsl", "shader-gradient", {"stable_over_time"}),
    ("tile.glsl",             "shader-tile",     set()),
    ("sdf.glsl",              "shader-sdf",      set()),
    ("polar.glsl",            "shader-polar",    set()),
    ("BAD_tile4.glsl",        "shader-tile",     {"tiles(8,x)", "tiles(8,y)"}),
    ("BAD_tile16.glsl",       "shader-tile",     {"distinct_bands(8,x)",
                                                    "distinct_bands(8,y)"}),
    ("BAD_softblob.glsl",     "shader-sdf",      {"sharp_edges"}),
    ("BAD_sdf_square.glsl",   "shader-sdf",      {"circle_radius"}),
    ("BAD_polar5.glsl",       "shader-polar",    {"rotational_symmetry(6)"}),
    ("BAD_polar12.glsl",      "shader-polar",    {"rotational_symmetry(6)"}),
]


def main() -> int:
    print("shader eval self-test\n" + "=" * 62)
    problems: list[str] = []

    for filename, task_id, expect_fail in CASES:
        path = REF / filename
        spec = load_spec(task_id)
        source = path.read_text(encoding="utf-8")

        result = render(source, times=spec.get("times", [0.0]), size=spec.get("size", 256))
        if result.error:
            print(f"\n{filename}: RENDERER ERROR\n{result.error}")
            return 2
        if not result.ok:
            bad = next(f for f in result.frames if not f.ok)
            print(f"\n{filename}: did not render ({bad.stage})\n{bad.log}")
            problems.append(f"{filename} failed to render")
            continue

        checks = evaluate(result, spec.get("properties", []))
        actually_failed = {c.name for c in checks if not c.passed}

        kind = "reference" if not expect_fail else "broken"
        print(f"\n{filename}  [{kind}, spec: {task_id}]")
        for c in checks:
            print(f"   [{'pass' if c.passed else 'FAIL'}] {c.name:<26} {c.detail}")

        if expect_fail:
            missed = expect_fail - actually_failed
            if missed:
                problems.append(
                    f"{filename}: expected these to FAIL but they passed -> {sorted(missed)}")
        else:
            if actually_failed:
                problems.append(
                    f"{filename}: reference shader failed -> {sorted(actually_failed)}")

    print("\n" + "=" * 62)
    if problems:
        print("SELF-TEST FAILED — the harness is not trustworthy yet:\n")
        for p in problems:
            print(f"  * {p}")
        print("\nFix the thresholds in assertions.py or the reference shaders,")
        print("then re-run. Do not benchmark a model until this passes.")
        return 1

    print("SELF-TEST PASSED")
    print("Reference shaders satisfy every property; broken shaders fail the")
    print("targeted property they violate. The grader discriminates these controls.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
