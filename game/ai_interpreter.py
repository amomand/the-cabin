"""Compatibility facade for command interpretation.

Implementation lives in ``game.ai`` modules. This module intentionally keeps
the established imports and runtime monkeypatch seams used by the game, tests,
and deterministic evaluation harnesses. Internal helpers are tested in their
owning modules.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, Optional

from game.ai.cache import clear_response_cache
from game.ai.prompt import build_interpreter_messages
from game.ai.rules import DIRECTION_ALIASES
from game.ai import runtime as _runtime
from game.ai import transport as _transport
from game.ai.transport import build_openai_chat_params, make_openai_params_compatible
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
_openai_client: Optional[Any] = None
_openai_client_key: Optional[str] = None


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


def interpret(user_text: str, context: Dict[str, Any]) -> Intent:
    """Convert player input into an intent through the shared runtime."""
    return _runtime.interpret(
        user_text,
        context,
        openai_available=OpenAI,
        get_openai_client=_get_openai_client,
        log_ai_call=log_ai_call,
        debug=_debug,
    )
