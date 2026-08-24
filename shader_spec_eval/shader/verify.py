"""Verify entry point for shader tasks.

A shader task's `verify` command is:

    python -m shader_spec_eval.shader.verify spec.json

It renders `shader.glsl` from the workspace, runs the properties listed in the
spec, prints a readable report, and exits non-zero if any property fails —
which is exactly the contract every other task type already follows.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .assertions import evaluate
from .render import render, save_png


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    spec_path = Path(argv[0]) if argv else Path("shader_spec.json")

    if not spec_path.exists():
        print(f"FAIL  spec not found: {spec_path}")
        return 2
    spec = json.loads(spec_path.read_text(encoding="utf-8"))

    target = Path(spec.get("file", "shader.glsl"))
    if not target.exists():
        print(f"FAIL  shader not found: {target}")
        return 2

    source = target.read_text(encoding="utf-8")
    if not source.strip():
        print(f"FAIL  {target} is empty")
        return 2

    times = spec.get("times", [0.0])
    size = spec.get("size", 256)

    result = render(source, times=times, size=size)

    if result.error:
        print(f"FAIL  renderer error\n{result.error}")
        return 2

    if not result.ok:
        bad = next((f for f in result.frames if not f.ok), None)
        print("FAIL  shader did not render")
        if bad:
            print(f"      stage: {bad.stage}")
            print(f"      log:\n{bad.log}")
        return 1

    # Optional artefact for the video — a picture of what the model produced.
    if spec.get("save_png"):
        out = Path(spec["save_png"])
        if save_png(result.first, out):
            print(f"      wrote {out}")

    checks = evaluate(result, spec.get("properties", []))

    print(f"rendered {len(result.frames)} frame(s) at {size}x{size}, times={times}\n")
    width = max((len(c.name) for c in checks), default=10)
    failed = 0
    for c in checks:
        mark = "pass" if c.passed else "FAIL"
        if not c.passed:
            failed += 1
        print(f"  [{mark}] {c.name:<{width}}  {c.detail}")

    total = len(checks)
    print(f"\n{total - failed}/{total} properties satisfied")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
