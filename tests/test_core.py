from pathlib import Path

from shader_spec_eval.config import Config
from shader_spec_eval.registry import parse_spec
from shader_spec_eval.shader.analysis import analyse, base_name, spearman
from shader_spec_eval.shader.bench import Cell, load_cells, load_task, save_cells


def test_model_spec_parsing() -> None:
    assert parse_spec("qwen2.5-coder:14b").provider == "ollama"
    remote = parse_spec("openai:model@http://127.0.0.1:1234/v1")
    assert remote.provider == "openai"
    assert remote.base_url == "http://127.0.0.1:1234/v1"


def test_default_sampling_is_explicit_and_nonzero() -> None:
    config = Config()
    assert config.sampling_temperature == 0.7
    assert config.sampling_seed == 7


def test_all_tasks_load() -> None:
    for task in ("shader-gradient", "shader-pulse", "shader-tile",
                 "shader-sdf", "shader-polar"):
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
                    sampling_temperature=0.7, sampling_seed=9)
    save_cells([original], path)
    loaded = load_cells(path)[0]
    assert loaded.sampling_temperature == 0.7
    assert loaded.sampling_seed == 9
