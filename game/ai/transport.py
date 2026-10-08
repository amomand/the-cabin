"""Model transports: OpenAI (SDK or direct httpx) and Anthropic (direct httpx)."""

from __future__ import annotations

import inspect
import json
import math
import os
import threading
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

# OpenAI reasoning families take reasoning_effort and max_completion_tokens
# in place of temperature and max_tokens. The game and the evaluation harness
# both route through these helpers; keep this the one definition.
_REASONING_FAMILY_PREFIXES = ("gpt-5", "gpt-6")
# Reasoning models that reject reasoning_effort="none" and "minimal": the
# GPT-6 flagship and the GPT-6.1 line take "low" as their floor.
_NO_NONE_EFFORT_PREFIXES = ("gpt-6-astra", "gpt-6.1")
REASONING_EFFORT_FLOOR = "low"


def is_reasoning_model(model: str) -> bool:
    """Whether the model takes reasoning_effort rather than temperature."""
    return model.startswith(_REASONING_FAMILY_PREFIXES)


def supports_no_reasoning(model: str) -> bool:
    """Whether the model accepts reasoning_effort="none"."""
    return is_reasoning_model(model) and not model.startswith(_NO_NONE_EFFORT_PREFIXES)


def effective_reasoning_effort(model: str, requested: Optional[str]) -> Optional[str]:
    """Clamp a requested reasoning effort to what the model accepts.

    Non-reasoning models get None. A "none" request on a model that rejects
    it becomes the floor, so a config written for the incumbent does not
    turn into a 400 at play time when the live model changes.
    """
    if not is_reasoning_model(model):
        return None
    if requested in ("none", "minimal") and not supports_no_reasoning(model):
        return REASONING_EFFORT_FLOOR
    return requested


# --- Anthropic -------------------------------------------------------------
#
# Anthropic is reached over plain httpx on every surface, the iOS bundle
# included, so there is one request shape and no SDK to ship. The evaluation
# harness builds its requests with the same functions, so the bench measures
# the production request.

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
# The thinking setting that turns thinking off. Anything else is an adaptive
# effort level ("low", "medium", "high"). Config normalises a blank value to
# "off"; only the bench can send None to keep a model's own default.
ANTHROPIC_THINKING_OFF = "off"
# Models whose thinking is switched off with "between_tools" rather than
# "disabled". With no tools in the request the two are equivalent in effect.
_ANTHROPIC_BETWEEN_TOOLS_MODELS = ("claude-sonnet-5-5",)
# A reply is a short JSON object; this is the budget with thinking off.
ANTHROPIC_REPLY_MAX_TOKENS = 1024
# Thinking tokens count against max_tokens; a thinking-on request needs room
# for them before the reply, or the response ends on max_tokens with no text.
ANTHROPIC_THINKING_HEADROOM = 3000


def strip_code_fences(text: str) -> str:
    """Remove a ``` fence around a JSON payload, including a leading newline."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
    return text


def split_system_for_cache(system_text: str) -> List[Dict[str, Any]]:
    """Split the system prompt into a static prefix and a dynamic tail.

    Everything before the Constraints block is identical across turns, so
    the prefix is tagged with Anthropic's `cache_control` (type `ephemeral`
    is the API's name for its prompt cache, not a signal that the block is
    disposable). Whether the cache engages is reported in usage, not assumed.
    """
    marker = "Constraints:"
    index = system_text.find(marker)
    if index <= 0:
        return [{"type": "text", "text": system_text}]
    return [
        {
            "type": "text",
            "text": system_text[:index],
            "cache_control": {"type": "ephemeral"},
        },
        {"type": "text", "text": system_text[index:]},
    ]


def anthropic_thinking_options(
    model: str,
    thinking: Optional[str],
    *,
    max_tokens: int = ANTHROPIC_REPLY_MAX_TOKENS,
) -> Dict[str, Any]:
    """Thinking, effort and max_tokens parameters for an Anthropic request."""
    if thinking == ANTHROPIC_THINKING_OFF:
        kind = "between_tools" if model.startswith(_ANTHROPIC_BETWEEN_TOOLS_MODELS) else "disabled"
        return {"thinking": {"type": kind}, "max_tokens": max_tokens}
    options: Dict[str, Any] = {"max_tokens": max_tokens + ANTHROPIC_THINKING_HEADROOM}
    if thinking:
        options["output_config"] = {"effort": thinking}
    return options


def build_anthropic_params(
    model: str,
    messages: List[Dict[str, str]],
    *,
    thinking: Optional[str],
) -> Dict[str, Any]:
    """Build the Messages API body for the interpreter prompt.

    No sampling parameters: current Claude models reject a non-default
    temperature. JSON comes from the prompt, as it did on the bench.
    """
    system = next(m["content"] for m in messages if m["role"] == "system")
    user = next(m["content"] for m in messages if m["role"] == "user")
    params: Dict[str, Any] = {
        "model": model,
        "system": split_system_for_cache(system),
        "messages": [{"role": "user", "content": user}],
    }
    params.update(anthropic_thinking_options(model, thinking))
    return params


def anthropic_response_text(body: Dict[str, Any]) -> str:
    """Join the text blocks of a Messages API response, skipping thinking.

    A refusal is raised, not parsed: there is no reply to validate, and the
    runtime's fallback is the right answer to a declined turn.
    """
    if body.get("stop_reason") == "refusal":
        raise RuntimeError("model declined the turn (stop_reason=refusal)")
    blocks = body.get("content") or []
    return "".join(
        str(block.get("text", ""))
        for block in blocks
        if isinstance(block, dict) and block.get("type") == "text"
    ).strip()


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
    if is_reasoning_model(model):
        params["max_completion_tokens"] = 800
        effort = effective_reasoning_effort(model, reasoning_effort)
        if effort:
            params["reasoning_effort"] = effort
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
            # Fences are stripped on every path so terminal, web and the
            # direct-httpx bundle accept the same output.
            content = strip_code_fences("".join(chunks))
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


def request_model_json_httpx(
    api_key: str,
    model: str,
    messages: List[Dict[str, str]],
    *,
    reasoning_effort: Optional[str],
    debug: Callable[[str], None],
) -> Any:
    """Use the pure-Python HTTP stack shipped by the embedded iOS runtime.

    This is deliberately opt-in at the orchestration layer.  Desktop and
    server entry points continue to use the OpenAI SDK; the mobile bundle can
    omit it (and its compiled pydantic-core dependency) without forking prompt,
    validation, retry, or fallback behaviour.
    """
    params = build_openai_chat_params(
        model,
        messages,
        stream=False,
        reasoning_effort=reasoning_effort,
    )

    def extract(body: Any) -> str:
        content = body["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise ValueError("model response content is not text")
        return content

    return _post_json_with_retry(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        body=params,
        extract=extract,
        debug=debug,
    )


def request_anthropic_json_httpx(
    api_key: str,
    model: str,
    messages: List[Dict[str, str]],
    *,
    thinking: Optional[str],
    debug: Callable[[str], None],
) -> Any:
    """Call the Anthropic Messages API over httpx and decode the JSON reply.

    Same deadline and single-retry contract as the OpenAI paths, read from
    OPENAI_TIMEOUT_SECONDS, which is the production model-call budget for
    every provider.
    """
    params = build_anthropic_params(model, messages, thinking=thinking)
    return _post_json_with_retry(
        ANTHROPIC_MESSAGES_URL,
        headers={
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        },
        body=params,
        extract=anthropic_response_text,
        debug=debug,
    )


_http_client: Any = None
_http_client_lock = threading.Lock()


# Idle keep-alive long enough to span a player's think time between turns;
# httpx's default of 5 s would reopen the connection on most turns. A
# connection the server has closed cleanly is noticed before reuse and
# simply reopened. The risk is a middlebox that drops an idle connection
# silently: that turn waits out the whole budget and falls back, so the
# mobile bundle, which sits behind carrier NAT, keeps a shorter expiry.
HTTP_KEEPALIVE_SECONDS = 120.0
MOBILE_HTTP_KEEPALIVE_SECONDS = 30.0


def _keepalive_seconds() -> float:
    if os.getenv("CABIN_MODEL_TRANSPORT") == "direct-httpx":
        return MOBILE_HTTP_KEEPALIVE_SECONDS
    return HTTP_KEEPALIVE_SECONDS


def http_post(url: str, *, headers: Dict[str, str], json: Dict[str, Any], timeout: float) -> Any:
    """POST through one shared client so turns reuse the TLS connection.

    A fresh handshake per turn is latency the bench never measured: the
    harness pools per thread, and the OpenAI SDK path reuses its client.
    Harnesses that must stay offline patch this function.
    """
    global _http_client
    if _httpx is None:
        raise RuntimeError("httpx transport is unavailable")
    if _http_client is None:
        with _http_client_lock:
            if _http_client is None:
                _http_client = _httpx.Client(
                    limits=_httpx.Limits(keepalive_expiry=_keepalive_seconds())
                )
    return _http_client.post(url, headers=headers, json=json, timeout=timeout)


def _post_json_with_retry(
    url: str,
    *,
    headers: Dict[str, str],
    body: Dict[str, Any],
    extract: Callable[[Any], str],
    debug: Callable[[str], None],
) -> Any:
    """POST once, retry a transient failure once, decode the model's JSON."""
    if _httpx is None:
        raise RuntimeError("httpx transport is unavailable")

    deadline = monotonic() + OPENAI_TIMEOUT_SECONDS
    retry_error: Optional[Exception] = None

    for attempt in range(1, MODEL_MAX_ATTEMPTS + 1):
        remaining = deadline - monotonic()
        if remaining <= 0:
            if retry_error is not None:
                raise retry_error
            raise TimeoutError("model-call deadline exhausted before request")
        try:
            response = http_post(url, headers=headers, json=body, timeout=remaining)
            response.raise_for_status()
            content = strip_code_fences(extract(response.json()))
            debug(f"Model raw output: {content[:120]}")
            return json.loads(content)
        except Exception as error:
            if attempt == MODEL_MAX_ATTEMPTS or not _is_retryable_model_error(error):
                raise
            remaining = deadline - monotonic()
            if remaining <= MODEL_RETRY_DELAY_SECONDS:
                raise
            retry_error = error
            debug(f"Transient model failure: {type(error).__name__}; retrying once")
            sleep(MODEL_RETRY_DELAY_SECONDS)
