from pathlib import Path

from shader_spec_eval.config import Config
from shader_spec_eval.registry import parse_spec
from shader_spec_eval.shader.analysis import analyse, base_name, spearman
from shader_spec_eval.shader.bench import Cell, _strip_fences, load_cells, load_task, save_cells
from shader_spec_eval.study import load_study, pricing_per_million, validate_catalog


def test_model_spec_parsing() -> None:
    assert parse_spec("qwen2.5-coder:14b").provider == "ollama"
    remote = parse_spec("openai:model@http://127.0.0.1:1234/v1")
    assert remote.provider == "openai"
    assert remote.base_url == "http://127.0.0.1:1234/v1"


def test_default_sampling_is_explicit_and_nonzero() -> None:
    config = Config()
    assert config.sampling_temperature == 0.7
    assert config.sampling_seed == 7


def test_null_model_content_becomes_an_empty_first_attempt() -> None:
    assert _strip_fences(None) == ""


def test_all_tasks_load() -> None:
    from shader_spec_eval.cli import DEFAULT_TASKS
    assert len(DEFAULT_TASKS) == 15
    for task in DEFAULT_TASKS:
        prompt, spec = load_task(task)
        assert "GLSL" in prompt
        assert spec["properties"]


def test_one_model_does_not_claim_signal_to_noise() -> None:
    cells = [Cell(model=f"local:model #{repeat}", task="shader-gradient")
             for repeat in range(1, 4)]
    verdict = analyse(cells, ["shader-gradient"])
    assert verdict.reliable is False
    assert "signal_to_noise" not in verdict.stats
    assert any("DISCRIMINATION UNTESTED" in reason for reason in verdict.reasons)


def test_statistics_and_repeat_labels() -> None:
    assert base_name("ollama:qwen #3") == "ollama:qwen"
    assert spearman([1, 2, 3], [10, 20, 30]) > 0.999


def test_cell_cache_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "cells.json"
    original = Cell(model="ollama:test", task="shader-gradient",
                    sampling_temperature=0.7, sampling_seed=9,
                    responses=["raw"], input_tokens=12, output_tokens=34,
                    thinking_tokens=5, cost_usd=0.0123,
                    resolved_model="resolved", provider_name="provider")
    save_cells([original], path)
    loaded = load_cells(path)[0]
    assert loaded.sampling_temperature == 0.7
    assert loaded.sampling_seed == 9
    assert loaded.responses == ["raw"]
    assert loaded.cost_usd == 0.0123
    assert loaded.resolved_model == "resolved"


def test_infrastructure_error_is_not_a_zero_score() -> None:
    failed = Cell(model="hosted:test", task="shader-gradient",
                  error="provider unavailable")
    compile_failure = Cell(model="hosted:test", task="shader-gradient",
                           compiled=False, compile_log="syntax error")
    assert failed.scorable is False
    assert compile_failure.scorable is True


def test_study_manifest_requires_temperature_and_seed() -> None:
    manifest = Path(__file__).parents[1] / "research" / "openrouter-temperature-study.json"
    plan = load_study(manifest)
    assert plan.temperature == 0.7
    assert set(plan.require_parameters) == {"temperature", "seed"}
    assert plan.local_models == ("qwen2.5-coder:14b",)
    catalog = {"data": [{
        "id": model.split(":", 1)[1],
        "supported_parameters": ["temperature", "seed", "max_tokens"],
        "pricing": {"prompt": "0.000001", "completion": "0.000002"},
    } for model in plan.models]}
    selected = validate_catalog(plan, catalog)
    assert len(selected) == len(plan.models)
    assert pricing_per_million(selected[0])[:2] == (1.0, 2.0)


def test_study_preflight_rejects_unsupported_temperature() -> None:
    manifest = Path(__file__).parents[1] / "research" / "openrouter-temperature-study.json"
    plan = load_study(manifest)
    route = plan.models[0].split(":", 1)[1]
    catalog = {"data": [{"id": route, "supported_parameters": ["seed"]}]}
    try:
        validate_catalog(plan, catalog)
    except ValueError as exc:
        assert "lacks required parameters: temperature" in str(exc)
    else:
        raise AssertionError("unsupported model should fail preflight")
