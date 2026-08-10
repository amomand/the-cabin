"""Validation and diegetic sanitization for untrusted model output."""

from __future__ import annotations

import math
from typing import Any, Dict, Optional

from game.ai.rules import DIRECTION_ALIASES, match_known_interaction_target
from game.ai.types import (
    ALLOWED_ACTIONS,
    DIEGETIC_REPLY_FALLBACK,
    Intent,
    LOW_CONFIDENCE_REPLY,
    LOW_CONFIDENCE_THRESHOLD,
    OUT_OF_WORLD_REPLY_MARKERS,
)


def sanitize_diegetic_reply(reply: Any) -> Optional[str]:
    """Return safe in-world text, or the fallback for meta output."""
    if reply is None:
        return None

    text = str(reply).strip()
    if not text:
        return None

    text = text[:140]
    lowered = text.lower()
    if any(marker in lowered for marker in OUT_OF_WORLD_REPLY_MARKERS):
        return DIEGETIC_REPLY_FALLBACK

    return text


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
    invalid_inventory_target = False
    if action == "move":
        raw_direction = args.get("direction") or args.get("target")
        direction = None
        if isinstance(raw_direction, str):
            direction = DIRECTION_ALIASES.get(
                raw_direction.lower(),
                raw_direction.lower(),
            )
            args["direction"] = direction
        if direction not in exits:
            action = "none"
            args = {}
            reply_override = "You turn that way and stop. Nothing opens there."
    elif action == "use":
        raw_item = args.get("item") or args.get("target") or args.get("object")
        if isinstance(raw_item, str):
            matched_item = match_known_interaction_target(raw_item, context)
            if matched_item:
                args["item"] = matched_item
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
            invalid_inventory_target = True

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
    if invalid_inventory_target:
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
