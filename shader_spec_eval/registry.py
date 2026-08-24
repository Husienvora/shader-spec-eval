"""Small provider registry for local and hosted model endpoints."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from .config import Config


@dataclass
class ModelSpec:
    provider: str
    model: str
    base_url: str = ""
    label: str = ""

    @property
    def display(self) -> str:
        return self.label or f"{self.provider}:{self.model}"


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    thinking_tokens: int = 0
    seconds: float = 0.0


DEFAULT_BASES = {
    "openrouter": "https://openrouter.ai/api/v1",
    "openai": "https://api.openai.com/v1",
}

ENV_KEYS = {
    "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    "openrouter": ("OPENROUTER_API_KEY",),
    "openai": ("OPENAI_API_KEY",),
}


class TransientError(RuntimeError):
    """Rate limiting or provider overload; not a model-quality failure."""


def parse_spec(text: str) -> ModelSpec:
    raw = text.strip()
    if ":" not in raw:
        return ModelSpec("ollama", raw)
    head, rest = raw.split(":", 1)
    head = head.lower()
    if head not in ("ollama", "gemini", "openrouter", "openai"):
        return ModelSpec("ollama", raw)
    base = ""
    if "@" in rest:
        rest, base = rest.split("@", 1)
    return ModelSpec(head, rest.strip(), base.strip() or DEFAULT_BASES.get(head, ""))


def require_key(spec: ModelSpec) -> str:
    for variable in ENV_KEYS.get(spec.provider, ()):
        if value := os.environ.get(variable):
            return value
    names = " or ".join(ENV_KEYS.get(spec.provider, ("(none)",)))
    raise RuntimeError(f"{spec.provider} requires {names}")


def _post(url: str, payload: dict, headers: dict, timeout: int) -> dict:
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        try:
            error = json.loads(body).get("error", {})
            message = error.get("message", body) if isinstance(error, dict) else str(error)
            code = error.get("code", exc.code) if isinstance(error, dict) else exc.code
        except (json.JSONDecodeError, AttributeError, TypeError):
            message, code = body[:300], exc.code
        raise RuntimeError(f"{code}: {str(message)[:280]}") from None


def call(spec: ModelSpec, prompt: str, system: str, cfg: Config,
         retries: int | None = None) -> tuple[str, Usage]:
    retries = cfg.max_retries if retries is None else retries
    last: Exception | None = None
    for attempt in range(retries):
        try:
            return _call_once(spec, prompt, system, cfg)
        except RuntimeError as exc:
            last = exc
            message = str(exc).lower()
            transient = any(token in message for token in (
                "429", "500", "502", "503", "resource_exhausted", "unavailable",
                "overloaded", "rate limit", "temporarily"))
            if not transient:
                raise
            delay = min(cfg.retry_base_delay * (2 ** attempt), 60.0)
            print(f"      transient provider error; retry in {delay:.0f}s "
                  f"({attempt + 1}/{retries})", flush=True)
            time.sleep(delay)
    raise TransientError(f"provider unavailable after {retries} attempts: {last}")


def _call_once(spec: ModelSpec, prompt: str, system: str,
               cfg: Config) -> tuple[str, Usage]:
    started = time.perf_counter()
    if spec.provider == "ollama":
        data = _post(f"{cfg.ollama_host}/api/generate", {
            "model": spec.model, "prompt": prompt, "system": system, "stream": False,
            "options": {"num_ctx": cfg.local_num_ctx,
                        "temperature": cfg.sampling_temperature,
                        "seed": cfg.sampling_seed},
        }, {}, cfg.request_timeout_s)
        return data.get("response", ""), Usage(
            input_tokens=data.get("prompt_eval_count", 0) or 0,
            output_tokens=data.get("eval_count", 0) or 0,
            seconds=time.perf_counter() - started)

    if spec.provider == "gemini":
        data = _post(
            f"{cfg.gemini_api_base}/models/{spec.model}:generateContent",
            {"contents": [{"parts": [{"text": prompt}]}],
             "systemInstruction": {"parts": [{"text": system}]},
             "generationConfig": {"maxOutputTokens": cfg.max_output_tokens,
                                  "temperature": cfg.sampling_temperature}},
            {"X-goog-api-key": require_key(spec)}, cfg.request_timeout_s)
        candidates = data.get("candidates") or []
        if not candidates:
            raise RuntimeError(f"no candidates returned: {data.get('promptFeedback', {})}")
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "".join(part.get("text", "") for part in parts if "text" in part)
        usage = data.get("usageMetadata", {}) or {}
        thinking = usage.get("thoughtsTokenCount", 0) or 0
        return text, Usage(
            input_tokens=usage.get("promptTokenCount", 0) or 0,
            output_tokens=(usage.get("candidatesTokenCount", 0) or 0) + thinking,
            thinking_tokens=thinking, seconds=time.perf_counter() - started)

    headers = {"Authorization": f"Bearer {require_key(spec)}"}
    if spec.provider == "openrouter":
        headers.update({"HTTP-Referer": "https://github.com/Husienvora/shader-spec-eval",
                        "X-Title": "Shader Spec Eval"})
    data = _post(f"{spec.base_url}/chat/completions", {
        "model": spec.model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": prompt}],
        "max_tokens": cfg.max_output_tokens,
        "temperature": cfg.sampling_temperature,
        "seed": cfg.sampling_seed,
    }, headers, cfg.request_timeout_s)
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError(f"no choices returned: {str(data)[:200]}")
    usage = data.get("usage", {}) or {}
    details = usage.get("completion_tokens_details") or {}
    return (choices[0].get("message") or {}).get("content", ""), Usage(
        input_tokens=usage.get("prompt_tokens", 0) or 0,
        output_tokens=usage.get("completion_tokens", 0) or 0,
        thinking_tokens=details.get("reasoning_tokens", 0) or 0,
        seconds=time.perf_counter() - started)


def describe(spec: ModelSpec) -> str:
    parts = [f"provider={spec.provider}", f"model={spec.model}"]
    if spec.base_url:
        parts.append(f"base={spec.base_url}")
    if spec.provider != "ollama":
        keys = ENV_KEYS.get(spec.provider, ())
        parts.append("key OK" if any(os.environ.get(key) for key in keys)
                     else f"MISSING {' or '.join(keys)}")
    return "  ".join(parts)
