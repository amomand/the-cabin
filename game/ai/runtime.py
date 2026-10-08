"""Command interpretation with deterministic rules and model fallbacks."""

from __future__ import annotations

import os
import sys
from typing import Any, Callable, Dict, Optional

from game.ai import cache, prompt, rules, transport, validation
from game.ai.types import Intent
from game.config import get_config

SUPPORTED_PROVIDERS = ("anthropic", "openai")


def _intent_log_payload(intent: Intent, *, include_effects: bool = False) -> Dict[str, Any]:
    payload = {
        "action": intent.action,
        "args": intent.args,
        "confidence": intent.confidence,
        "reply": intent.reply,
    }
    if include_effects:
        payload["effects"] = intent.effects
    payload["rationale"] = intent.rationale
    return payload


def _fallback(
    user_text: str,
    context: Dict[str, Any],
    ruled: Optional[Intent],
    *,
    rationale: str,
    error: str,
    log_ai_call: Callable[..., Any],
) -> Intent:
    if ruled:
        if (
            ruled.action == "move"
            and ruled.args.get("direction") not in context.get("exits", [])
        ):
            ruled.confidence = min(ruled.confidence, 0.5)
        intent = ruled
    else:
        intent = Intent(
            "none", {}, 0.0,
            reply=rules.offline_none_reply(user_text, context),
            effects=None,
            rationale=rationale,
        )
    log_ai_call(user_text, context, _intent_log_payload(intent), error)
    return intent


def rule_answers_without_model(ruled: Optional[Intent]) -> bool:
    """Whether a rule match is final in play, or only the offline fallback.

    Deterministic fixture use skips the model; every other rule match is
    kept as the fallback and the model still sees the input. The evaluation
    harness reuses this so it never scores models on inputs they never get.
    """
    return ruled is not None and ruled.action == "use"


def interpret(
    user_text: str,
    context: Dict[str, Any],
    *,
    openai_available: Any,
    get_openai_client: Callable[[str], Any],
    log_ai_call: Callable[..., Any],
    debug: Callable[[str], None],
) -> Intent:
    """Convert player input into an intent without owning subsystem details."""
    cache_key = cache.make_cache_key(user_text, context)
    cached = cache.cache_get(cache_key, debug=debug)
    if cached:
        return cached

    ruled = rules.rule_based(user_text, context)
    if rule_answers_without_model(ruled):
        log_ai_call(
            user_text,
            context,
            _intent_log_payload(ruled),
            "deterministic fixture use",
        )
        cache.cache_put(cache_key, ruled)
        return ruled

    config = get_config()
    # Provider and keys are read from the environment per call, not from the
    # cached config, so an offline harness that pops them really is offline.
    from game.config import normalise_provider

    provider = normalise_provider(os.getenv("CABIN_MODEL_PROVIDER") or config.model_provider)
    use_direct_httpx = os.getenv("CABIN_MODEL_TRANSPORT") == "direct-httpx"
    if provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        model_transport_available = transport._httpx is not None
        transport_state = f"httpx={'present' if model_transport_available else 'absent'}"
    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        model_transport_available = openai_available is not None or use_direct_httpx
        transport_state = (
            f"openai_sdk={'present' if openai_available is not None else 'absent'} "
            f"direct_httpx={'on' if use_direct_httpx else 'off'}"
        )
    else:
        api_key = None
        model_transport_available = False
        transport_state = f"unknown provider {provider!r} (expected one of {SUPPORTED_PROVIDERS})"
    if not api_key or not model_transport_available:
        debug(
            f"No model path ({provider}): "
            f"api_key={'set' if api_key else 'missing'} {transport_state}; "
            "using rule-based fallback"
        )
        return _fallback(
            user_text, context, ruled,
            rationale="fallback-no-model",
            error=(
                "No model path - using rule-based fallback"
                if ruled else "No model path - no rule match"
            ),
            log_ai_call=log_ai_call,
        )

    debug(f"Using Python: {sys.version.split()[0]} at {sys.executable}")
    debug(f"openai={transport.OPENAI_VERSION} httpx={transport.HTTPX_VERSION}")
    messages = prompt.build_interpreter_messages(user_text, context)

    try:
        if provider == "anthropic":
            model = config.anthropic_model
            debug(f"Calling {model} via anthropic messages (httpx), thinking={config.anthropic_thinking}")
            data = transport.request_anthropic_json_httpx(
                api_key,
                model,
                messages,
                thinking=config.anthropic_thinking,
                debug=debug,
            )
        else:
            model = config.openai_model
            debug(f"Calling {model} via chat.completions")
            reasoning_effort = (
                getattr(config, "openai_reasoning_effort", "none")
                if transport.is_reasoning_model(model)
                else None
            )
            if use_direct_httpx:
                debug(f"Calling {model} via direct httpx chat.completions")
                data = transport.request_model_json_httpx(
                    api_key,
                    model,
                    messages,
                    reasoning_effort=reasoning_effort,
                    debug=debug,
                )
            else:
                client = get_openai_client(api_key)
                data = transport.request_model_json(
                    client,
                    model,
                    messages,
                    reasoning_effort=reasoning_effort,
                    debug=debug,
                )
    except Exception as error:
        debug(f"Model call failed: {error!r}; using rule-based fallback")
        return _fallback(
            user_text, context, ruled,
            rationale="fallback-error",
            error=f"API call failed: {error}",
            log_ai_call=log_ai_call,
        )

    intent = validation.validate_model_response(data, context)

    try:
        log_ai_call(
            user_text,
            context,
            _intent_log_payload(intent, include_effects=True),
        )
    except Exception as error:
        debug(f"AI call logging failed: {error!r}")

    cache.cache_put(cache_key, intent)
    return intent
