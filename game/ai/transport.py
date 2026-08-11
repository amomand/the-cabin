"""OpenAI client lifecycle, request compatibility, and streamed transport."""

from __future__ import annotations

import inspect
import json
import math
import os
from typing import Any, Callable, Dict, List, Optional


try:
    import httpx as _httpx  # type: ignore

    HTTPX_VERSION = getattr(_httpx, "__version__", "unknown")
except Exception:  # pragma: no cover
    _httpx = None
    HTTPX_VERSION = "unavailable"

try:
    import openai as _openai_mod  # type: ignore

    OPENAI_VERSION = getattr(_openai_mod, "__version__", "unknown")
except Exception:
    _openai_mod = None
    OPENAI_VERSION = "unavailable"

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover - optional dependency during dev
    OpenAI = None  # type: ignore


_openai_client: Optional[Any] = None
_openai_client_key: Optional[str] = None


def positive_float_env(name: str, default: float) -> float:
    """Parse a positive finite float without making import fragile."""
    try:
        value = float(os.getenv(name, ""))
    except (TypeError, ValueError):
        return default
    return value if math.isfinite(value) and value > 0 else default


OPENAI_TIMEOUT_SECONDS = positive_float_env("OPENAI_TIMEOUT_SECONDS", 20.0)


def get_openai_client(
    api_key: str,
    *,
    openai_factory: Any = OpenAI,
    timeout: float = OPENAI_TIMEOUT_SECONDS,
) -> Any:
    """Return a cached client, rebuilding it when the credential changes."""
    global _openai_client, _openai_client_key
    if _openai_client is None or _openai_client_key != api_key:
        _openai_client = openai_factory(api_key=api_key, timeout=timeout)
        _openai_client_key = api_key
    return _openai_client


def make_openai_params_compatible(
    create_fn: Any,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """Pass newer OpenAI params through extra_body for older SDKs."""
    compatible = dict(params)
    try:
        supported_params = set(inspect.signature(create_fn).parameters)
    except (TypeError, ValueError):
        return compatible

    passthrough: Dict[str, Any] = {}
    for key in ("max_completion_tokens", "reasoning_effort"):
        if key in compatible and key not in supported_params:
            passthrough[key] = compatible.pop(key)

    if passthrough:
        extra_body = dict(compatible.get("extra_body") or {})
        extra_body.update(passthrough)
        compatible["extra_body"] = extra_body

    return compatible


def build_openai_chat_params(
    model: str,
    messages: List[Dict[str, str]],
    *,
    stream: bool = True,
    reasoning_effort: Optional[str] = None,
) -> Dict[str, Any]:
    """Build chat.completions params for the configured model family."""
    params: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "response_format": {"type": "json_object"},
        "stream": stream,
    }
    if model.startswith("gpt-5"):
        params["max_completion_tokens"] = 800
        if reasoning_effort:
            params["reasoning_effort"] = reasoning_effort
    else:
        params["temperature"] = 0
        params["max_tokens"] = 400
    return params


def request_model_json(
    client: Any,
    model: str,
    messages: List[Dict[str, str]],
    *,
    reasoning_effort: Optional[str],
    debug: Callable[[str], None],
) -> Any:
    """Execute the streamed request and decode its JSON response."""
    params = build_openai_chat_params(
        model,
        messages,
        stream=True,
        reasoning_effort=reasoning_effort,
    )
    params = make_openai_params_compatible(client.chat.completions.create, params)

    stream = client.chat.completions.create(**params)
    chunks = []
    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            chunks.append(delta.content)
    content = "".join(chunks).strip()
    debug(f"Model raw output: {content[:120]}")
    return json.loads(content)
