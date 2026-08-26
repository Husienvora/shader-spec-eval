"""Shader benchmark — run N models across the difficulty ladder.

Produces, for every (model, task) pair: the shader source, the rendered frame as
a PNG, and a per-property pass/fail record. Everything is objective; nothing is
judged by another model.

The point of the exercise: text coding benchmarks primarily measure symbolic
program behavior. Shader tasks let us probe whether models can translate explicit
spatial and temporal requirements into visual programs. Whether that is a distinct
ability is an empirical question, not an assumption built into the score.
"""

from __future__ import annotations

import base64
import io as _io
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from ..config import Config
from ..registry import ModelSpec, TransientError, call, parse_spec
from .assertions import Check, evaluate
from .render import render

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_TASKS = PACKAGE_ROOT.parent / "tasks"
TASKS = REPOSITORY_TASKS if REPOSITORY_TASKS.is_dir() else PACKAGE_ROOT / "tasks"

SYSTEM = (
    "You write GLSL ES 3.0 fragment shaders. Return ONLY the shader source code. "
    "No markdown fences, no explanation, no commentary."
)


@dataclass
class Cell:
    model: str
    task: str
    source: str = ""
    compiled: bool = False
    transient: bool = False        # rate-limited etc. — excluded, never scored 0
    attempts: int = 1
    compile_log: str = ""
    checks: list[Check] = field(default_factory=list)
    png_b64: str = ""
    seconds: float = 0.0
    error: str = ""
    sampling_temperature: float | None = None
    sampling_seed: int | None = None
    responses: list[str] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    thinking_tokens: int = 0
    cost_usd: float = 0.0
    resolved_model: str = ""
    provider_name: str = ""

    @property
    def passed(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def total(self) -> int:
        return len(self.checks)

    @property
    def score(self) -> float:
        """Fraction of properties satisfied. A compile failure genuinely scores 0.

        A TRANSIENT failure (rate limit, 5xx) is not a model failure and must be
        excluded from aggregates rather than scored 0 — conflating the two was
        the single largest source of fake variance in early runs.
        """
        return self.passed / self.total if self.total else 0.0

    @property
    def scorable(self) -> bool:
        # Provider/harness failures are missing observations, not zero-quality shaders.
        # Compiler failures have no infrastructure error and remain genuine zero scores.
        return not self.transient and not self.error

    @property
    def perfect(self) -> bool:
        return self.total > 0 and self.passed == self.total


def _strip_fences(text: str | None) -> str:
    # A reasoning route can return JSON null after spending its output budget
    # without emitting final content. Preserve that as an empty first attempt
    # so it is checkpointed and scored instead of crashing or being regenerated.
    t = (text or "").strip()
    if t.startswith("```"):
        lines = t.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines)
    return t.strip()


def load_task(task_id: str) -> tuple[str, dict]:
    spec = json.loads((TASKS / task_id / "task.json").read_text(encoding="utf-8"))
    shader_spec = json.loads(
        (TASKS / task_id / "seed" / "shader_spec.json").read_text(encoding="utf-8"))
    return spec["prompt"], shader_spec


def _png_b64(frame) -> str:
    try:
        from PIL import Image
    except ImportError:
        return ""
    img = Image.frombytes("RGBA", (frame.size, frame.size), frame.pixels)
    img = img.transpose(Image.FLIP_TOP_BOTTOM).convert("RGB")
    buf = _io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


def run_cell(spec: ModelSpec | str, task_id: str, cfg: Config,
             is_local: bool = False) -> Cell:
    if isinstance(spec, str):
        spec = parse_spec(spec)
    prompt, shader_spec = load_task(task_id)
    cell = Cell(model=spec.display, task=task_id)
    cell.sampling_temperature = cfg.sampling_temperature
    cell.sampling_seed = cfg.sampling_seed
    t0 = time.perf_counter()
    convo = prompt

    for attempt in range(cfg.compile_retries + 1):
        cell.attempts = attempt + 1
        try:
            text, usage = call(spec, convo, SYSTEM, cfg)
        except TransientError as exc:
            cell.transient = True
            cell.error = f"rate-limited: {exc}"
            cell.seconds = time.perf_counter() - t0
            return cell
        except Exception as exc:                          # noqa: BLE001
            cell.error = f"{type(exc).__name__}: {exc}"
            cell.seconds = time.perf_counter() - t0
            return cell

        cell.responses.append(text)
        cell.input_tokens += usage.input_tokens
        cell.output_tokens += usage.output_tokens
        cell.thinking_tokens += usage.thinking_tokens
        cell.cost_usd += usage.cost_usd
        cell.resolved_model = usage.resolved_model or cell.resolved_model
        cell.provider_name = usage.provider_name or cell.provider_name
        cell.source = _strip_fences(text)
        result = render(cell.source,
                        times=shader_spec.get("times", [0.0]),
                        size=shader_spec.get("size", 256))
        if result.error:                                   # harness fault, not model
            cell.transient = True
            cell.error = result.error
            cell.seconds = time.perf_counter() - t0
            return cell

        if result.ok:
            cell.compiled = True
            cell.checks = evaluate(result, shader_spec.get("properties", []))
            cell.png_b64 = _png_b64(result.first)
            break

        bad = next(f for f in result.frames if not f.ok)
        cell.compile_log = f"[{bad.stage}] {bad.log}"
        if attempt < cfg.compile_retries:
            # Hand the compiler error back, exactly as a developer would. This is
            # not best-of-N: it only fires on a hard compile failure, never to
            # improve a low score.
            convo = "\n".join([
                prompt,
                "",
                "# Your previous shader failed to compile",
                bad.log[:600],
                "",
                "# Previous shader source",
                cell.source,
                "",
                "Return a corrected shader. Source only.",
            ])

    cell.seconds = time.perf_counter() - t0
    return cell


def save_cells(cells: list[Cell], path: Path) -> None:
    """Persist raw results so the dashboard can be re-rendered without re-running."""
    path.write_text(json.dumps([{
        "model": c.model, "task": c.task, "source": c.source,
        "compiled": c.compiled, "compile_log": c.compile_log,
        "checks": [{"name": k.name, "passed": k.passed, "detail": k.detail} for k in c.checks],
        "png_b64": c.png_b64, "seconds": c.seconds, "error": c.error,
        "transient": c.transient, "attempts": c.attempts,
        "sampling_temperature": c.sampling_temperature,
        "sampling_seed": c.sampling_seed,
        "responses": c.responses,
        "input_tokens": c.input_tokens,
        "output_tokens": c.output_tokens,
        "thinking_tokens": c.thinking_tokens,
        "cost_usd": c.cost_usd,
        "resolved_model": c.resolved_model,
        "provider_name": c.provider_name,
    } for c in cells], indent=1), encoding="utf-8")


def load_cells(path: Path) -> list[Cell]:
    out = []
    for d in json.loads(path.read_text(encoding="utf-8")):
        c = Cell(model=d["model"], task=d["task"], source=d["source"],
                 compiled=d["compiled"], compile_log=d["compile_log"],
                 png_b64=d["png_b64"], seconds=d["seconds"],
                 error=d["error"], transient=d.get("transient", False),
                 attempts=d.get("attempts", 1),
                 sampling_temperature=d.get("sampling_temperature"),
                 sampling_seed=d.get("sampling_seed"),
                 responses=d.get("responses", []),
                 input_tokens=d.get("input_tokens", 0),
                 output_tokens=d.get("output_tokens", 0),
                 thinking_tokens=d.get("thinking_tokens", 0),
                 cost_usd=d.get("cost_usd", 0.0),
                 resolved_model=d.get("resolved_model", ""),
                 provider_name=d.get("provider_name", ""))
        c.checks = [Check(k["name"], k["passed"], k["detail"]) for k in d["checks"]]
        out.append(c)
    return out


def reference_cell(task_id: str, ref_file: str) -> Cell:
    """Render the known-good answer so the grid has a control row."""
    _, shader_spec = load_task(task_id)
    src = (Path(__file__).parent / "reference" / ref_file).read_text(encoding="utf-8")
    cell = Cell(model="reference (human)", task=task_id, source=src)
    result = render(src, times=shader_spec.get("times", [0.0]),
                    size=shader_spec.get("size", 256))
    if result.ok:
        cell.compiled = True
        cell.checks = evaluate(result, shader_spec.get("properties", []))
        cell.png_b64 = _png_b64(result.first)
    return cell
