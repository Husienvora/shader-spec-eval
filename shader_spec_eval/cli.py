"""Command-line interface for Shader Spec Eval."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
import webbrowser
from dataclasses import replace
from pathlib import Path

from .config import Config
from .registry import describe, parse_spec
from .shader.analysis import base_name
from .shader.bench import load_cells, reference_cell, run_cell, save_cells
from .shader.dashboard import write_dashboard
from .shader.selftest import main as run_selftest

PACKAGE_ROOT = Path(__file__).resolve().parent
ROOT = PACKAGE_ROOT.parent
REPOSITORY_TASKS = ROOT / "tasks"
TASKS = REPOSITORY_TASKS if REPOSITORY_TASKS.is_dir() else PACKAGE_ROOT / "tasks"
DEFAULT_TASKS = ["shader-gradient", "shader-pulse", "shader-tile",
                 "shader-sdf", "shader-polar"]
REFERENCES = {
    "shader-gradient": "gradient.glsl",
    "shader-pulse": "pulse.glsl",
    "shader-tile": "tile.glsl",
    "shader-sdf": "sdf.glsl",
    "shader-polar": "polar.glsl",
}


def cmd_doctor(args, cfg: Config) -> int:
    failures = 0
    print("Shader Spec Eval doctor\n")
    try:
        with urllib.request.urlopen(f"{cfg.ollama_host}/api/tags", timeout=3) as response:
            models = json.loads(response.read()).get("models", [])
        print(f"  [ok] Ollama reachable: {len(models)} model(s) installed")
        for model in models:
            print(f"       {model.get('name', '?')}")
    except Exception as exc:  # noqa: BLE001
        print(f"  [warn] Ollama unavailable: {exc}")

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            browser.close()
        print("  [ok] Playwright and Chromium available")
    except Exception as exc:  # noqa: BLE001
        failures += 1
        print(f"  [FAIL] Playwright/Chromium: {exc}")
        print("         Run: python -m playwright install chromium")

    missing = [task for task in DEFAULT_TASKS
               if not (TASKS / task / "task.json").exists()]
    if missing:
        failures += 1
        print(f"  [FAIL] Missing tasks: {', '.join(missing)}")
    else:
        print(f"  [ok] {len(DEFAULT_TASKS)} task(s) available")
    return 1 if failures else 0


def cmd_run(args, cfg: Config) -> int:
    tasks = args.tasks or DEFAULT_TASKS
    unknown = [task for task in tasks if not (TASKS / task).is_dir()]
    if unknown:
        print(f"Unknown task(s): {', '.join(unknown)}", file=sys.stderr)
        return 2

    specs = [parse_spec(model) for model in args.models]
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    cells_path = output_dir / "shader-cells.json"
    dashboard_path = output_dir / "shader-dashboard.html"

    cells = []
    rows = []
    if not args.no_reference:
        rows.append("reference (human)")
        for task in tasks:
            print(f"  reference / {task} ...", flush=True)
            cells.append(reference_cell(task, REFERENCES[task]))

    print(f"  sampling: temperature={cfg.sampling_temperature:g}, "
          f"base_seed={cfg.sampling_seed}; seed increments per repeat")
    for spec in specs:
        print(f"  [{spec.display}] {describe(spec)}")
        for repeat in range(args.repeats):
            run_cfg = replace(cfg, sampling_seed=cfg.sampling_seed + repeat)
            label = spec.display if args.repeats == 1 else f"{spec.display} #{repeat + 1}"
            rows.append(label)
            for task in tasks:
                print(f"  {label} / {task} ...", end="", flush=True)
                cell = run_cell(spec, task, run_cfg)
                cell.model = label
                cells.append(cell)
                if cell.error:
                    print(f" ERROR {cell.error[:80]}")
                elif not cell.compiled:
                    print(" did not compile")
                else:
                    print(f" {cell.passed}/{cell.total}")

    save_cells(cells, cells_path)
    write_dashboard(cells, tasks, rows, dashboard_path)

    print("\nmodel                         properties    clean")
    print("-" * 55)
    for spec in specs:
        model_cells = [cell for cell in cells if base_name(cell.model) == spec.display]
        if not model_cells:
            continue
        property_score = sum(cell.score for cell in model_cells) / len(model_cells)
        clean = sum(cell.perfect for cell in model_cells)
        print(f"{spec.display:<30}{property_score:>7.1%}{clean:>8}/{len(model_cells)}")
    print(f"\nRaw cells:  {cells_path}")
    print(f"Dashboard:  {dashboard_path}")
    if not args.no_open:
        webbrowser.open(dashboard_path.as_uri())
    return 0


def cmd_dashboard(args, cfg: Config) -> int:
    cells_path = Path(args.cells).resolve()
    cells = load_cells(cells_path)
    tasks = list(dict.fromkeys(cell.task for cell in cells))
    rows = list(dict.fromkeys(cell.model for cell in cells))
    output = Path(args.output).resolve()
    write_dashboard(cells, tasks, rows, output)
    print(f"Dashboard: {output}")
    if not args.no_open:
        webbrowser.open(output.as_uri())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="shader-spec-eval",
        description="Evaluate generated GLSL against rendered behavioral properties.")
    parser.add_argument("--temperature", type=float, default=0.7,
                        help="explicit sampling temperature (default: 0.7)")
    parser.add_argument("--seed", type=int, default=7,
                        help="base seed; repeats increment it (default: 7)")
    parser.add_argument("--ollama-host", default="http://127.0.0.1:11434")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="check renderer and local model setup")
    doctor.set_defaults(function=cmd_doctor)

    selftest = sub.add_parser("selftest", help="run known-good and adversarial controls")
    selftest.set_defaults(function=lambda args, cfg: run_selftest())

    run = sub.add_parser("run", help="run one or more models across the task ladder")
    run.add_argument("--models", nargs="+", required=True,
                     help="Ollama tags or provider:model specifications")
    run.add_argument("--tasks", nargs="*", choices=DEFAULT_TASKS)
    run.add_argument("--repeats", type=int, default=3)
    run.add_argument("--no-reference", action="store_true")
    run.add_argument("--no-open", action="store_true")
    run.add_argument("--output-dir", default=str(Path.cwd() / "results" / "latest"))
    run.set_defaults(function=cmd_run)

    dashboard = sub.add_parser("dashboard", help="rebuild a dashboard from cached cells")
    dashboard.add_argument("--cells", required=True)
    dashboard.add_argument("--output", default="shader-dashboard.html")
    dashboard.add_argument("--no-open", action="store_true")
    dashboard.set_defaults(function=cmd_dashboard)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if getattr(args, "repeats", 1) < 1:
        raise SystemExit("--repeats must be at least 1")
    cfg = Config(ollama_host=args.ollama_host,
                 sampling_temperature=args.temperature,
                 sampling_seed=args.seed)
    return args.function(args, cfg)


if __name__ == "__main__":
    raise SystemExit(main())
