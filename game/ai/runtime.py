"""Interpreter orchestration assembled by the compatibility facade."""

from __future__ import annotations

import os
import sys
from typing import Any, Callable, Dict, Optional

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


def interpret(
    user_text: str,
    context: Dict[str, Any],
    *,
    openai_available: Any,
    get_openai_client: Callable[[str], Any],
    log_ai_call: Callable[..., Any],
    debug: Callable[[str], None],
    make_cache_key: Callable[[str, Dict[str, Any]], str],
    cache_get: Callable[[str], Optional[Intent]],
    cache_put: Callable[[str, Intent], None],
    rule_based: Callable[[str, Optional[Dict[str, Any]]], Optional[Intent]],
    offline_none_reply: Callable[[str, Dict[str, Any]], str],
    build_messages: Callable[[str, Dict[str, Any]], Any],
    request_model_json: Callable[..., Any],
    validate_model_response: Callable[[Any, Dict[str, Any]], Intent],
    openai_version: str,
    httpx_version: str,
) -> Intent:
    """Convert player input into an intent without owning subsystem details."""
    cache_key = make_cache_key(user_text, context)
    cached = cache_get(cache_key)
    if cached:
        return cached

    ruled = rule_based(user_text, context)
    if ruled and ruled.action == "use":
        log_ai_call(
            user_text,
            context,
            _intent_log_payload(ruled),
            "deterministic fixture use",
        )
        cache_put(cache_key, ruled)
        return ruled

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or openai_available is None:
        debug("No OPENAI_API_KEY or OpenAI SDK missing; using rule-based fallback")
        ruled = rule_based(user_text, context)
        if ruled:
            exits = set(context.get("exits", []))
            if ruled.action == "move" and ruled.args.get("direction") not in exits:
                ruled.confidence = min(ruled.confidence, 0.5)
            log_ai_call(
                user_text,
                context,
                _intent_log_payload(ruled),
                "No API key - using rule-based fallback",
            )
            return ruled
        reply = offline_none_reply(user_text, context)
        fallback_intent = Intent(
            "none",
            {},
            0.0,
            reply=reply,
            effects=None,
            rationale="fallback-no-key",
        )
        log_ai_call(
            user_text,
            context,
            _intent_log_payload(fallback_intent),
            "No API key - no rule match",
        )
        return fallback_intent

    debug(f"Using Python: {sys.version.split()[0]} at {sys.executable}")
    debug(f"openai={openai_version} httpx={httpx_version}")
    client = get_openai_client(api_key)
    messages = build_messages(user_text, context)

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
        data = request_model_json(
            client,
            model,
            messages,
            reasoning_effort=reasoning_effort,
            debug=debug,
        )
    except Exception as error:
        debug(f"Model call failed: {error!r}; using rule-based fallback")
        ruled = rule_based(user_text, context)
        if ruled:
            exits = set(context.get("exits", []))
            if ruled.action == "move" and ruled.args.get("direction") not in exits:
                ruled.confidence = min(ruled.confidence, 0.5)
            log_ai_call(
                user_text,
                context,
                _intent_log_payload(ruled),
                f"API call failed: {error}",
            )
            return ruled
        reply = offline_none_reply(user_text, context)
        fallback_intent = Intent(
            "none",
            {},
            0.0,
            reply=reply,
            effects=None,
            rationale="fallback-error",
        )
        log_ai_call(
            user_text,
            context,
            _intent_log_payload(fallback_intent),
            f"API call failed: {error}",
        )
        return fallback_intent

    intent = validate_model_response(data, context)

    try:
        log_ai_call(
            user_text,
            context,
            _intent_log_payload(intent, include_effects=True),
        )
    except Exception as error:
        debug(f"AI call logging failed: {error!r}")

    cache_put(cache_key, intent)
    return intent
