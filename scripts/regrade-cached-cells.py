"""Re-render cached model sources without making provider requests."""

from __future__ import annotations

import argparse
from pathlib import Path

from shader_spec_eval.shader.assertions import evaluate
from shader_spec_eval.shader.bench import _png_b64, load_cells, load_task, save_cells
from shader_spec_eval.shader.render import render


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("cells", type=Path)
    args = parser.parse_args()

    cells = load_cells(args.cells)
    changed = 0
    for cell in cells:
        # Provider/transport failures have no model source to regrade.
        if cell.error:
            if cell.error.startswith(("TimeoutError:", "URLError:")):
                cell.transient = True
            continue

        _, shader_spec = load_task(cell.task)
        result = render(
            cell.source,
            times=shader_spec.get("times", [0.0]),
            size=shader_spec.get("size", 256),
        )
        cell.compiled = False
        cell.compile_log = ""
        cell.checks = []
        cell.png_b64 = ""

        if result.error:
            cell.transient = True
            cell.error = result.error
        elif result.ok:
            cell.compiled = True
            cell.checks = evaluate(result, shader_spec.get("properties", []))
            cell.png_b64 = _png_b64(result.first)
        else:
            bad = next(frame for frame in result.frames if not frame.ok)
            cell.compile_log = f"[{bad.stage}] {bad.log}"
        changed += 1

    save_cells(cells, args.cells)
    print(f"Regraded {changed} cached sources in {args.cells}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
