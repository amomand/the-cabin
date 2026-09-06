"""Command interpretation with deterministic rules and model fallbacks."""

from __future__ import annotations

import os
import sys
from typing import Any, Callable, Dict, Optional

from game.ai import cache, prompt, rules, transport, validation
from game.ai.types import Intent


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
    if ruled and ruled.action == "use":
        log_ai_call(
            user_text,
            context,
            _intent_log_payload(ruled),
            "deterministic fixture use",
        )
        cache.cache_put(cache_key, ruled)
        return ruled

    api_key = os.getenv("OPENAI_API_KEY")
    use_direct_httpx = os.getenv("CABIN_MODEL_TRANSPORT") == "direct-httpx"
    model_transport_available = openai_available is not None or use_direct_httpx
    if not api_key or not model_transport_available:
        debug(
            "No model path: "
            f"api_key={'set' if api_key else 'missing'} "
            f"openai_sdk={'present' if openai_available is not None else 'absent'} "
            f"direct_httpx={'on' if use_direct_httpx else 'off'}; "
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
        from game.config import get_config

        config = get_config()
        model = config.openai_model
        debug(f"Calling {model} via chat.completions")
        reasoning_effort = (
            getattr(config, "openai_reasoning_effort", "none")
            if model.startswith("gpt-5")
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
