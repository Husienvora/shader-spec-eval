"""Runtime configuration for Shader Spec Eval."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Config:
    ollama_host: str = "http://127.0.0.1:11434"
    gemini_api_base: str = "https://generativelanguage.googleapis.com/v1beta"
    max_output_tokens: int = 16000
    local_num_ctx: int = 16384
    max_retries: int = 6
    retry_base_delay: float = 4.0
    sampling_temperature: float = 0.7
    sampling_seed: int = 7
    compile_retries: int = 1
    request_timeout_s: int = 900
