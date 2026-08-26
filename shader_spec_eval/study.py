"""Frozen study manifests and OpenRouter catalog validation."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"


@dataclass(frozen=True)
class StudyPlan:
    study_id: str
    temperature: float
    base_seed: int
    repeats: int
    max_output_tokens: int
    max_cost_usd: float
    require_parameters: tuple[str, ...]
    models: tuple[str, ...]
    local_models: tuple[str, ...]


def load_study(path: Path) -> StudyPlan:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return StudyPlan(
        study_id=str(raw["study_id"]),
        temperature=float(raw["temperature"]),
        base_seed=int(raw["base_seed"]),
        repeats=int(raw["repeats"]),
        max_output_tokens=int(raw["max_output_tokens"]),
        max_cost_usd=float(raw["max_cost_usd"]),
        require_parameters=tuple(raw.get("require_parameters", ())),
        models=tuple(raw["models"]),
        local_models=tuple(raw.get("local_models", ())),
    )


def fetch_openrouter_catalog(timeout: int = 30) -> dict:
    request = urllib.request.Request(
        OPENROUTER_MODELS_URL,
        headers={"User-Agent": "shader-spec-eval/0.1"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


def model_id(model_spec: str) -> str:
    prefix = "openrouter:"
    if not model_spec.startswith(prefix):
        raise ValueError(f"study model is not an OpenRouter route: {model_spec}")
    return model_spec[len(prefix):]


def validate_catalog(plan: StudyPlan, catalog: dict) -> list[dict]:
    by_id = {item.get("id"): item for item in catalog.get("data", [])}
    selected: list[dict] = []
    problems: list[str] = []
    for spec in plan.models:
        route = model_id(spec)
        item = by_id.get(route)
        if not item:
            problems.append(f"missing route: {route}")
            continue
        supported = set(item.get("supported_parameters") or [])
        missing = sorted(set(plan.require_parameters) - supported)
        if missing:
            problems.append(f"{route} lacks required parameters: {', '.join(missing)}")
            continue
        selected.append(item)
    if problems:
        raise ValueError("OpenRouter preflight failed:\n- " + "\n- ".join(problems))
    return selected


def pricing_per_million(item: dict) -> tuple[float, float, float]:
    pricing = item.get("pricing") or {}
    return (
        float(pricing.get("prompt", 0) or 0) * 1_000_000,
        float(pricing.get("completion", 0) or 0) * 1_000_000,
        float(pricing.get("internal_reasoning", 0) or 0) * 1_000_000,
    )


def catalog_snapshot(plan: StudyPlan, selected: list[dict]) -> dict:
    keep = []
    for item in selected:
        input_rate, output_rate, reasoning_rate = pricing_per_million(item)
        keep.append({
            "id": item.get("id"),
            "name": item.get("name"),
            "created": item.get("created"),
            "context_length": item.get("context_length"),
            "supported_parameters": item.get("supported_parameters") or [],
            "reasoning": item.get("reasoning"),
            "pricing_per_million_usd": {
                "input": input_rate,
                "output": output_rate,
                "internal_reasoning": reasoning_rate,
            },
        })
    return {
        "study_id": plan.study_id,
        "required_parameters": list(plan.require_parameters),
        "models": keep,
    }
