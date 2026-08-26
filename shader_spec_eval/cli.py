"""Command-line interface for Shader Spec Eval."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
import webbrowser
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from .config import Config
from .registry import describe, parse_spec
from .shader.analysis import base_name
from .shader.bench import load_cells, reference_cell, run_cell, save_cells
from .shader.dashboard import write_dashboard
from .shader.selftest import main as run_selftest
from .study import (
    catalog_snapshot,
    fetch_openrouter_catalog,
    load_study,
    pricing_per_million,
    validate_catalog,
)

PACKAGE_ROOT = Path(__file__).resolve().parent
ROOT = PACKAGE_ROOT.parent
REPOSITORY_TASKS = ROOT / "tasks"
TASKS = REPOSITORY_TASKS if REPOSITORY_TASKS.is_dir() else PACKAGE_ROOT / "tasks"
DEFAULT_TASKS = [
    "shader-gradient", "shader-gradient-diagonal", "shader-bands", "shader-stripes",
    "shader-tile", "shader-grid", "shader-sdf", "shader-offset-circle", "shader-ring",
    "shader-box", "shader-double-circle", "shader-mirror", "shader-pulse", "shader-motion",
    "shader-polar",
]
REFERENCES = {
    "shader-gradient": "gradient.glsl",
    "shader-gradient-diagonal": "gradient_diagonal.glsl",
    "shader-bands": "bands.glsl",
    "shader-stripes": "stripes.glsl",
    "shader-pulse": "pulse.glsl",
    "shader-tile": "tile.glsl",
    "shader-grid": "grid.glsl",
    "shader-sdf": "sdf.glsl",
    "shader-offset-circle": "offset_circle.glsl",
    "shader-ring": "ring.glsl",
    "shader-box": "box.glsl",
    "shader-double-circle": "double_circle.glsl",
    "shader-mirror": "mirror.glsl",
    "shader-motion": "motion.glsl",
    "shader-polar": "polar.glsl",
}
REPOSITORY_RESEARCH = ROOT / "research"
RESEARCH = REPOSITORY_RESEARCH if REPOSITORY_RESEARCH.is_dir() else PACKAGE_ROOT / "research"
DEFAULT_STUDY = RESEARCH / "openrouter-temperature-study.json"


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

    cells = load_cells(cells_path) if getattr(args, "resume", False) and cells_path.exists() else []
    rows = list(dict.fromkeys(cell.model for cell in cells))
    completed = {(cell.model, cell.task, cell.sampling_seed)
                 for cell in cells if cell.scorable}
    spent_usd = sum(cell.cost_usd for cell in cells)
    new_cells = 0
    if not args.no_reference:
        if "reference (human)" not in rows:
            rows.append("reference (human)")
        for task in tasks:
            if any(cell.model == "reference (human)" and cell.task == task for cell in cells):
                continue
            print(f"  reference / {task} ...", flush=True)
            cells.append(reference_cell(task, REFERENCES[task]))
            save_cells(cells, cells_path)

    print(f"  sampling: temperature={cfg.sampling_temperature:g}, "
          f"base_seed={cfg.sampling_seed}; seed increments per repeat")
    for spec in specs:
        print(f"  [{spec.display}] {describe(spec)}")
        for repeat in range(args.repeats):
            run_cfg = replace(cfg, sampling_seed=cfg.sampling_seed + repeat)
            label = spec.display if args.repeats == 1 else f"{spec.display} #{repeat + 1}"
            if label not in rows:
                rows.append(label)
            for task in tasks:
                key = (label, task, run_cfg.sampling_seed)
                if key in completed:
                    print(f"  {label} / {task} ... cached")
                    continue
                if cfg.max_cost_usd is not None and spent_usd >= cfg.max_cost_usd:
                    save_cells(cells, cells_path)
                    write_dashboard(cells, tasks, rows, dashboard_path)
                    print(f"\nCost guard reached ${spent_usd:.4f}; stopping before next call.",
                          file=sys.stderr)
                    return 3
                print(f"  {label} / {task} ...", end="", flush=True)
                cell = run_cell(spec, task, run_cfg)
                cell.model = label
                cells.append(cell)
                completed.add(key)
                spent_usd += cell.cost_usd
                save_cells(cells, cells_path)
                if cell.error:
                    print(f" ERROR {cell.error[:80]}")
                elif not cell.compiled:
                    print(" did not compile")
                else:
                    suffix = f"  ${cell.cost_usd:.4f}" if cell.cost_usd else ""
                    print(f" {cell.passed}/{cell.total}{suffix}")
                new_cells += 1
                max_new_cells = getattr(args, "max_new_cells", None)
                if max_new_cells is not None and new_cells >= max_new_cells:
                    write_dashboard(cells, tasks, rows, dashboard_path)
                    print(f"\nCompatibility gate reached after {new_cells} new cells.")
                    return 0

    save_cells(cells, cells_path)
    write_dashboard(cells, tasks, rows, dashboard_path)

    print("\nmodel                         properties    clean")
    print("-" * 55)
    for spec in specs:
        model_cells = [cell for cell in cells
                       if base_name(cell.model) == spec.display and cell.scorable]
        if not model_cells:
            continue
        property_score = sum(cell.score for cell in model_cells) / len(model_cells)
        clean = sum(cell.perfect for cell in model_cells)
        print(f"{spec.display:<30}{property_score:>7.1%}{clean:>8}/{len(model_cells)}")
    print(f"\nRaw cells:  {cells_path}")
    print(f"Dashboard:  {dashboard_path}")
    print(f"Provider cost recorded: ${spent_usd:.4f}")
    if not args.no_open:
        webbrowser.open(dashboard_path.as_uri())
    return 0


def cmd_openrouter_study(args, cfg: Config) -> int:
    manifest = Path(args.manifest).resolve()
    plan = load_study(manifest)
    catalog = fetch_openrouter_catalog()
    selected = validate_catalog(plan, catalog)
    tasks = [DEFAULT_TASKS[0]] if args.pilot else DEFAULT_TASKS
    repeats = 1 if args.pilot else plan.repeats

    print(f"Study: {plan.study_id}")
    print(f"Sampling: temperature={plan.temperature:g}, seeds "
          f"{plan.base_seed}..{plan.base_seed + repeats - 1}")
    all_models = [*plan.models, *plan.local_models]
    print(f"Tasks: {len(tasks)}  paid models: {len(selected)}  "
          f"local models: {len(plan.local_models)}  repeats: {repeats}")
    print(f"Planned paid calls: {len(tasks) * len(selected) * repeats}")
    print("\nEligible OpenRouter routes:")
    worst_case = 0.0
    for item in selected:
        input_rate, output_rate, reasoning_rate = pricing_per_million(item)
        # Planning bound: 512 input tokens and the configured maximum output.
        per_call = (512 * input_rate + plan.max_output_tokens *
                    max(output_rate, reasoning_rate)) / 1_000_000
        worst_case += per_call * len(tasks) * repeats
        print(f"  {item['id']:<38} in ${input_rate:g}/M  out ${output_rate:g}/M")
    print(f"\nConservative catalog-price projection: ${worst_case:.2f}")
    print(f"Configured study ceiling: ${plan.max_cost_usd:.2f}")
    if worst_case > plan.max_cost_usd:
        print("Projection exceeds the study ceiling; refusing to execute.", file=sys.stderr)
        return 2

    if not args.execute:
        print("\nDRY RUN ONLY. No model requests were sent.")
        print("Use --execute after setting OPENROUTER_API_KEY.")
        return 0

    if not os.environ.get("OPENROUTER_API_KEY"):
        print("OPENROUTER_API_KEY is not set.", file=sys.stderr)
        return 2
    if run_selftest() != 0:
        print("Grader self-test failed; refusing paid model calls.", file=sys.stderr)
        return 2

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot = catalog_snapshot(plan, selected)
    snapshot["captured_at"] = datetime.now(timezone.utc).isoformat()
    (output_dir / "openrouter-catalog-snapshot.json").write_text(
        json.dumps(snapshot, indent=2), encoding="utf-8")
    run_metadata = {
        "study_id": plan.study_id,
        "manifest": str(manifest),
        "temperature": plan.temperature,
        "base_seed": plan.base_seed,
        "repeats": repeats,
        "tasks": tasks,
        "models": all_models,
        "paid_models": list(plan.models),
        "local_models": list(plan.local_models),
        "max_output_tokens": plan.max_output_tokens,
        "max_cost_usd": plan.max_cost_usd,
        "primary_first_attempt_only": True,
        "provider_fallbacks": False,
    }
    (output_dir / "run-config.json").write_text(
        json.dumps(run_metadata, indent=2), encoding="utf-8")

    study_cfg = replace(
        cfg,
        sampling_temperature=plan.temperature,
        sampling_seed=plan.base_seed,
        max_output_tokens=plan.max_output_tokens,
        max_cost_usd=plan.max_cost_usd,
        openrouter_allow_fallbacks=False,
        compile_retries=0,
    )
    run_args = argparse.Namespace(
        tasks=tasks,
        models=all_models,
        output_dir=str(output_dir),
        no_reference=False,
        no_open=args.no_open,
        repeats=repeats,
        resume=True,
        max_new_cells=args.max_new_cells,
    )
    return cmd_run(run_args, study_cfg)


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
    run.add_argument("--resume", action="store_true",
                     help="resume from shader-cells.json and checkpoint each new cell")
    run.add_argument("--max-new-cells", type=int,
                     help="stop cleanly after checkpointing this many new model cells")
    run.set_defaults(function=cmd_run)

    study = sub.add_parser(
        "openrouter-study",
        help="validate or execute the frozen temperature-controlled OpenRouter study")
    study.add_argument("--manifest", default=str(DEFAULT_STUDY))
    study.add_argument("--execute", action="store_true",
                       help="send paid calls; without this flag the command is a dry run")
    study.add_argument("--pilot", action="store_true",
                       help="run one task once per model before the full study")
    study.add_argument("--no-open", action="store_true")
    study.add_argument("--max-new-cells", type=int,
                       help="stop cleanly after checkpointing this many new model cells")
    study.add_argument("--output-dir",
                       default=str(Path.cwd() / "results" / "openrouter-temperature-v0.2"))
    study.set_defaults(function=cmd_openrouter_study)

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
