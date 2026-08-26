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
    ("ALT_gradient.glsl",     "shader-gradient", set()),
    ("ALT_pulse.glsl",        "shader-pulse", set()),
    ("ALT_tile.glsl",         "shader-tile", set()),
    ("ALT_sdf.glsl",          "shader-sdf", set()),
    ("ALT_polar.glsl",        "shader-polar", set()),

    ("gradient_diagonal.glsl", "shader-gradient-diagonal", set()),
    ("ALT_gradient_diagonal.glsl", "shader-gradient-diagonal", set()),
    ("BAD_diagonal_x_only.glsl", "shader-gradient-diagonal",
     {"gradient_y_decreasing"}),
    ("BAD_wrong_axis.glsl", "shader-gradient-diagonal", {"gradient_x_increasing"}),
    ("BAD_periodic_gradient.glsl", "shader-gradient-diagonal", {"stable_over_time"}),

    ("bands.glsl", "shader-bands", set()),
    ("ALT_bands.glsl", "shader-bands", set()),
    ("BAD_bands4.glsl", "shader-bands", {"distinct_bands(5,x)"}),
    ("gradient.glsl", "shader-bands", {"distinct_bands(5,x)"}),
    ("BAD_periodic_gradient.glsl", "shader-bands", {"stable_over_time"}),

    ("stripes.glsl", "shader-stripes", set()),
    ("ALT_stripes.glsl", "shader-stripes", set()),
    ("BAD_stripes8.glsl", "shader-stripes", {"distinct_bands(6,x)"}),
    ("bands.glsl", "shader-stripes", {"tiles(6,x)"}),
    ("BAD_periodic_gradient.glsl", "shader-stripes", {"stable_over_time"}),

    ("grid.glsl", "shader-grid", set()),
    ("ALT_grid.glsl", "shader-grid", set()),
    ("BAD_grid12x8.glsl", "shader-grid",
     {"distinct_bands(6,x)", "distinct_bands(4,y)"}),
    ("tile.glsl", "shader-grid", {"distinct_bands(6,x)", "distinct_bands(4,y)"}),
    ("stripes.glsl", "shader-grid", {"distinct_bands(4,y)"}),

    ("offset_circle.glsl", "shader-offset-circle", set()),
    ("ALT_offset_circle.glsl", "shader-offset-circle", set()),
    ("BAD_offset_radius.glsl", "shader-offset-circle", {"circle_at(0.30,0.65)"}),
    ("sdf.glsl", "shader-offset-circle", {"circle_at(0.30,0.65)"}),
    ("BAD_sdf_square.glsl", "shader-offset-circle", {"circle_at(0.30,0.65)"}),

    ("ring.glsl", "shader-ring", set()),
    ("ALT_ring.glsl", "shader-ring", set()),
    ("BAD_ring_inner.glsl", "shader-ring", {"ring_radii"}),
    ("sdf.glsl", "shader-ring", {"ring_radii"}),
    ("BAD_softblob.glsl", "shader-ring", {"ring_radii"}),

    ("box.glsl", "shader-box", set()),
    ("ALT_box.glsl", "shader-box", set()),
    ("BAD_box_square.glsl", "shader-box", {"box_bounds"}),
    ("sdf.glsl", "shader-box", {"box_bounds"}),
    ("BAD_softblob.glsl", "shader-box", {"box_bounds"}),

    ("double_circle.glsl", "shader-double-circle", set()),
    ("ALT_double_circle.glsl", "shader-double-circle", set()),
    ("BAD_double_radius.glsl", "shader-double-circle",
     {"circle_at(0.30,0.50)", "circle_at(0.70,0.50)"}),
    ("sdf.glsl", "shader-double-circle",
     {"circle_at(0.30,0.50)", "circle_at(0.70,0.50)"}),
    ("BAD_sdf_square.glsl", "shader-double-circle",
     {"circle_at(0.30,0.50)", "circle_at(0.70,0.50)"}),

    ("mirror.glsl", "shader-mirror", set()),
    ("ALT_mirror.glsl", "shader-mirror", set()),
    ("BAD_mirror_centered.glsl", "shader-mirror", {"asymmetric(vertical)"}),
    ("box.glsl", "shader-mirror", {"asymmetric(vertical)"}),
    ("BAD_sdf_square.glsl", "shader-mirror", {"asymmetric(vertical)"}),

    ("motion.glsl", "shader-motion", set()),
    ("ALT_motion.glsl", "shader-motion", set()),
    ("BAD_motion_left.glsl", "shader-motion", {"centroid_moves(x,increasing)"}),
    ("BAD_motion_static.glsl", "shader-motion",
     {"animates", "centroid_moves(x,increasing)"}),
    ("BAD_static_pulse.glsl", "shader-motion", {"animates"}),
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
