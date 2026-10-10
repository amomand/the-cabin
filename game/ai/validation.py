"""Validation and diegetic sanitization for untrusted model output."""

from __future__ import annotations

import math
import re
from typing import Any, Dict, Optional

from game.ai.rules import DIRECTION_ALIASES, match_known_interaction_target
from game.ai.types import (
    ALLOWED_ACTIONS,
    DIEGETIC_REPLY_FALLBACK,
    Intent,
    LOW_CONFIDENCE_REPLY,
    LOW_CONFIDENCE_THRESHOLD,
    OUT_OF_WORLD_REPLY_MARKERS,
    REPLY_CHAR_LIMIT,
)


# A marker must start a word: a provider name must not censor "lycanthropic"
# or "Claudia", plausible vocabulary in a story about something wearing a
# dog's shape. Only the leading edge is bounded, so plural, possessive and
# underscore forms ("system prompts", "OpenAI's", "ANTHROPIC_API_KEY") still
# count as leaks.
_OUT_OF_WORLD_PATTERNS = tuple(
    re.compile(r"\b" + re.escape(marker)) for marker in OUT_OF_WORLD_REPLY_MARKERS
)


def _is_out_of_world(lowered: str) -> bool:
    return any(pattern.search(lowered) for pattern in _OUT_OF_WORLD_PATTERNS)


# A sentence ends at terminal punctuation, optionally closed by a quote or
# bracket, followed by whitespace or the end of the text. The full stop after
# a title or an initial ("Mr. Koskinen", "A. Koskinen") is not an ending.
_SENTENCE_END = re.compile(
    r"(?<!\bMr)(?<!\bMrs)(?<!\bMs)(?<!\bDr)(?<!\bSt)(?<!\b[A-Z])"
    r"[.!?\u2026][\"'\u2019\u201d)]*(?=\s|$)"
)


def _open_quote_closer(text: str) -> str:
    """Return the mark that would close dialogue left open in ``text``."""
    if text.count("\u201c") > text.count("\u201d"):
        return "\u201d"
    if text.count('"') % 2:
        return '"'
    return ""


def _trim_to_limit(text: str) -> str:
    """Shorten an over-long reply without leaving it cut mid-word.

    Keep every whole sentence that fits, never stopping inside open dialogue.
    A first sentence too long to fit trails off at a word boundary instead,
    which reads as the narration falling quiet rather than as a seam.
    """
    if len(text) <= REPLY_CHAR_LIMIT:
        return text

    # Match against the full text so the limit itself never passes for the end
    # of a sentence, and a closing quote just past it isn't left behind.
    sentence_ends = [
        match.end()
        for match in _SENTENCE_END.finditer(text)
        if match.end() <= REPLY_CHAR_LIMIT
        and not _open_quote_closer(text[: match.end()])
    ]
    if sentence_ends:
        return text[: sentence_ends[-1]]

    closer = _open_quote_closer(text[:REPLY_CHAR_LIMIT])
    budget = REPLY_CHAR_LIMIT - 1 - len(closer)
    head = text[:budget]
    if not text[budget].isspace() and len(head.split()) > 1:
        head = head.rsplit(None, 1)[0]
    head = head.rstrip(" \t\n,;:-\u2013\u2014")
    if not head:
        return DIEGETIC_REPLY_FALLBACK
    return head + "\u2026" + _open_quote_closer(head)


def sanitize_diegetic_reply(reply: Any) -> Optional[str]:
    """Return safe in-world text, a meta fallback, or ``None`` for no text."""
    if reply is None:
        return None

    text = str(reply).strip()
    if not text:
        return None

    # Screen the whole reply, not just the part that survives trimming: a
    # model that leaks after its first sentence is off the rails anyway.
    if _is_out_of_world(text.lower()):
        return DIEGETIC_REPLY_FALLBACK

    return _trim_to_limit(text)


def coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return result if math.isfinite(result) else default


def coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return default


def coerce_list(value: Any) -> list:
    """Return a list only for actual list or tuple model output."""
    return list(value) if isinstance(value, (list, tuple)) else []


def validate_model_response(data: Any, context: Dict[str, Any]) -> Intent:
    """Convert arbitrary decoded model output into a bounded ``Intent``."""
    exits = list(context.get("exits", []))
    room_items = list(context.get("room_items", []))
    inventory = list(context.get("inventory", []))

    if not isinstance(data, dict):
        data = {}
    action = str(data.get("action", "none")).lower()
    if action not in ALLOWED_ACTIONS:
        action = "none"

    args = data.get("args", {}) or {}
    if not isinstance(args, dict):
        args = {}

    reply_override = None
    invalid_action_target = False
    if action == "move":
        raw_direction = args.get("direction") or args.get("target")
        direction = None
        if isinstance(raw_direction, str):
            direction = DIRECTION_ALIASES.get(
                raw_direction.lower(),
                raw_direction.lower(),
            )
            args = {"direction": direction}
        if direction not in exits:
            action = "none"
            args = {}
            reply_override = "You turn that way and stop. Nothing opens there."
            invalid_action_target = True
    elif action == "use":
        raw_item = args.get("item") or args.get("target") or args.get("object")
        if isinstance(raw_item, str) and raw_item.strip():
            matched_item = match_known_interaction_target(raw_item, context)
            args = {"item": matched_item or raw_item.strip()}
        else:
            action = "none"
            args = {}
            reply_override = LOW_CONFIDENCE_REPLY
            invalid_action_target = True
    elif action in {"look", "listen"}:
        raw_target = args.get("target", args.get("item"))
        if raw_target is None or isinstance(raw_target, str):
            target = raw_target.strip() if raw_target else ""
            args = {"target": target} if target else {}
        else:
            action = "none"
            args = {}
            reply_override = LOW_CONFIDENCE_REPLY
            invalid_action_target = True
    elif action == "light":
        raw_target = args.get("target")
        if isinstance(raw_target, str) and raw_target.strip():
            args = {"target": raw_target.strip()}
        else:
            action = "none"
            args = {}
            reply_override = LOW_CONFIDENCE_REPLY
            invalid_action_target = True
    elif action in {"take", "drop", "throw"}:
        raw_item = args.get("item") or args.get("target") or args.get("object")
        sources = (
            ("carryable_room_items",)
            if action == "take"
            else ("inventory",)
        )
        matched_item = (
            match_known_interaction_target(raw_item, context, sources=sources)
            if isinstance(raw_item, str)
            else None
        )
        if matched_item:
            args["item"] = matched_item
        else:
            action = "none"
            args = {}
            reply_override = LOW_CONFIDENCE_REPLY
            invalid_action_target = True

    confidence = coerce_float(data.get("confidence"), 0.0)
    confidence = max(0.0, min(1.0, confidence))

    reply = sanitize_diegetic_reply(data.get("reply"))
    if reply_override:
        reply = reply_override

    effects = data.get("effects") or {}
    if not isinstance(effects, dict):
        effects = {}
    fear = max(-2, min(2, coerce_int(effects.get("fear"), 0)))
    health = max(-2, min(2, coerce_int(effects.get("health"), 0)))

    inv_add = [
        str(item)
        for item in coerce_list(effects.get("inventory_add"))
        if str(item) in (set(room_items) | set(inventory))
    ]
    inv_remove = [
        str(item)
        for item in coerce_list(effects.get("inventory_remove"))
        if str(item) in set(inventory)
    ]

    sanitized_effects = {
        "fear": fear,
        "health": health,
        "inventory_add": inv_add,
        "inventory_remove": inv_remove,
    }
    if invalid_action_target:
        sanitized_effects = {
            "fear": 0,
            "health": 0,
            "inventory_add": [],
            "inventory_remove": [],
        }

    rationale = data.get("rationale")
    if rationale is not None:
        rationale = str(rationale)

    if action != "none" and confidence < LOW_CONFIDENCE_THRESHOLD:
        action = "none"
        args = {}
        reply = LOW_CONFIDENCE_REPLY
        sanitized_effects = {
            "fear": 0,
            "health": 0,
            "inventory_add": [],
            "inventory_remove": [],
        }

    return Intent(
        action,
        args,
        confidence,
        reply=reply,
        effects=sanitized_effects,
        rationale=rationale,
    )
