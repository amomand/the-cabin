"""OpenAI request compatibility and streamed transport."""

from __future__ import annotations

import inspect
import json
import math
import os
from time import monotonic, sleep
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


def positive_float_env(name: str, default: float) -> float:
    """Parse a positive finite float without making import fragile."""
    try:
        value = float(os.getenv(name, ""))
    except (TypeError, ValueError):
        return default
    return value if math.isfinite(value) and value > 0 else default


OPENAI_TIMEOUT_SECONDS = positive_float_env("OPENAI_TIMEOUT_SECONDS", 20.0)
MODEL_RETRY_DELAY_SECONDS = 0.25
MODEL_MAX_ATTEMPTS = 2


def _exception_status_code(error: Exception) -> Optional[int]:
    """Return an HTTP status exposed directly or through an SDK response."""
    status_code = getattr(error, "status_code", None)
    if not isinstance(status_code, int):
        status_code = getattr(getattr(error, "response", None), "status_code", None)
    return status_code if isinstance(status_code, int) else None


def _is_model_timeout(error: Exception) -> bool:
    """Recognise timeout failures before broader connection-error classes."""
    if isinstance(error, TimeoutError):
        return True
    if _openai_mod is not None:
        timeout_error = getattr(_openai_mod, "APITimeoutError", None)
        if timeout_error is not None and isinstance(error, timeout_error):
            return True
    if _httpx is not None:
        timeout_error = getattr(_httpx, "TimeoutException", None)
        if timeout_error is not None and isinstance(error, timeout_error):
            return True
    return False


def _is_retryable_model_error(error: Exception) -> bool:
    """Classify failures that can plausibly clear within one short retry."""
    if isinstance(error, json.JSONDecodeError):
        return True
    if _is_model_timeout(error):
        return False

    status_code = _exception_status_code(error)
    if status_code is not None:
        return status_code == 429 or status_code >= 500

    if isinstance(error, ConnectionError):
        return True
    if _openai_mod is not None:
        connection_error = getattr(_openai_mod, "APIConnectionError", None)
        if connection_error is not None and isinstance(error, connection_error):
            return True
    if _httpx is not None:
        transport_error = getattr(_httpx, "TransportError", None)
        if transport_error is not None and isinstance(error, transport_error):
            return True
    return False


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
    """Decode a streamed response, retrying one transient production failure.

    The evaluation harness intentionally differs: malformed output is a model
    quality signal there, while in play it is a lost turn and gets one retry.
    """
    deadline = monotonic() + OPENAI_TIMEOUT_SECONDS
    retry_error: Optional[Exception] = None
    params = build_openai_chat_params(
        model,
        messages,
        stream=True,
        reasoning_effort=reasoning_effort,
    )
    params = make_openai_params_compatible(client.chat.completions.create, params)

    for attempt in range(1, MODEL_MAX_ATTEMPTS + 1):
        remaining = deadline - monotonic()
        if remaining <= 0:
            if retry_error is not None:
                raise retry_error
            raise TimeoutError("model-call deadline exhausted before request")

        try:
            stream = client.chat.completions.create(
                **params,
                timeout=remaining,
            )
            chunks = []
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    chunks.append(delta.content)
            content = "".join(chunks).strip()
            debug(f"Model raw output: {content[:120]}")
            return json.loads(content)
        except Exception as error:
            if attempt == MODEL_MAX_ATTEMPTS or not _is_retryable_model_error(error):
                raise

            remaining = deadline - monotonic()
            if remaining <= MODEL_RETRY_DELAY_SECONDS:
                raise
            retry_error = error
            debug(f"Transient model failure: {error!r}; retrying once")
            sleep(MODEL_RETRY_DELAY_SECONDS)
