"""Compatibility facade for command interpretation.

Implementation lives in ``game.ai`` modules. This module intentionally keeps
the established imports and runtime monkeypatch seams used by the game, tests,
and deterministic evaluation harnesses.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, Optional

from game.ai import cache as _cache
from game.ai import prompt as _prompt
from game.ai import rules as _rules
from game.ai import runtime as _runtime
from game.ai import transport as _transport
from game.ai import validation as _validation
from game.ai.types import (
    ALLOWED_ACTIONS,
    DIEGETIC_REPLY_FALLBACK,
    Intent,
    LOW_CONFIDENCE_REPLY,
    LOW_CONFIDENCE_THRESHOLD,
    OUT_OF_WORLD_REPLY_MARKERS,
)
from game.logger import log_ai_call


# Importing this facade must not load .env. Entry points own that boundary.
OpenAI = _transport.OpenAI
OPENAI_TIMEOUT_SECONDS = _transport.OPENAI_TIMEOUT_SECONDS
_OPENAI_VERSION = _transport.OPENAI_VERSION
_HTTPX_VERSION = _transport.HTTPX_VERSION
_httpx = _transport._httpx
_openai_mod = _transport._openai_mod

_openai_client: Optional[Any] = None
_openai_client_key: Optional[str] = None

# These aliases preserve the evaluation and test harness surface.
_SYSTEM_PROMPT_TEMPLATE = _prompt.SYSTEM_PROMPT_TEMPLATE
DIRECTION_ALIASES = _rules.DIRECTION_ALIASES
_response_cache = _cache.response_cache
_DEFAULT_RESPONSE_CACHE_SIZE = _cache.DEFAULT_RESPONSE_CACHE_SIZE

_positive_float_env = _transport.positive_float_env
_offline_none_reply = _rules.offline_none_reply
_make_cache_key = _cache.make_cache_key
_response_cache_capacity = _cache.response_cache_capacity
_sanitize_diegetic_reply = _validation.sanitize_diegetic_reply
_coerce_float = _validation.coerce_float
_coerce_int = _validation.coerce_int
_coerce_list = _validation.coerce_list
_make_openai_params_compatible = _transport.make_openai_params_compatible
make_openai_params_compatible = _make_openai_params_compatible
_wrong_layer_rules = _prompt.wrong_layer_rules
_build_system_prompt = _prompt.build_system_prompt
_build_user_message_content = _prompt.build_user_message_content
build_interpreter_messages = _prompt.build_interpreter_messages
build_openai_chat_params = _transport.build_openai_chat_params
_act_v_offer_active = _rules.act_v_offer_active
_normalise_interaction_target = _rules.normalise_interaction_target
_is_single_edit_apart = _rules.is_single_edit_apart
_unique_single_edit_match = _rules.unique_single_edit_match
_match_known_interaction_target = _rules.match_known_interaction_target
_match_known_exit = _rules.match_known_exit
_rule_based = _rules.rule_based

# Keep historical type identity for introspection and pickle compatibility.
Intent.__module__ = __name__


def _get_openai_client(api_key: str) -> Any:
    """Preserve the facade-level client factory seam."""
    global _openai_client, _openai_client_key
    if _openai_client is None or _openai_client_key != api_key:
        _openai_client = OpenAI(
            api_key=api_key,
            timeout=OPENAI_TIMEOUT_SECONDS,
            max_retries=0,
        )
        _openai_client_key = api_key
    return _openai_client


def _debug(message: str) -> None:
    if os.getenv("CABIN_DEBUG") == "1":
        print(f"[AI DEBUG] {message}", file=sys.stderr)
    try:
        from game.logger import get_logger

        get_logger().debug(f"AI DEBUG: {message}")
    except Exception:
        pass


def _cache_get(key: str) -> Optional[Intent]:
    return _cache.cache_get(key, debug=_debug)


def _cache_put(key: str, intent: Intent) -> None:
    _cache.cache_put(key, intent)


def clear_response_cache() -> None:
    _cache.clear_response_cache()


def interpret(user_text: str, context: Dict[str, Any]) -> Intent:
    """Convert player input into an intent through the shared runtime."""
    return _runtime.interpret(
        user_text,
        context,
        openai_available=OpenAI,
        get_openai_client=_get_openai_client,
        log_ai_call=log_ai_call,
        debug=_debug,
        make_cache_key=_make_cache_key,
        cache_get=_cache_get,
        cache_put=_cache_put,
        rule_based=_rule_based,
        offline_none_reply=_offline_none_reply,
        build_messages=build_interpreter_messages,
        request_model_json=_transport.request_model_json,
        validate_model_response=_validation.validate_model_response,
        openai_version=_OPENAI_VERSION,
        httpx_version=_HTTPX_VERSION,
    )
