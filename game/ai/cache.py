"""Runtime-sized LRU storage for interpreted commands."""

from __future__ import annotations

from collections import OrderedDict
import hashlib
import json
from typing import Any, Callable, Dict, Optional, Tuple

from game.ai.types import Intent


ResponseTuple = Tuple[
    str,
    Dict,
    float,
    Optional[str],
    Optional[Dict],
    Optional[str],
]

response_cache: OrderedDict[str, ResponseTuple] = OrderedDict()
DEFAULT_RESPONSE_CACHE_SIZE = 50


def make_cache_key(user_text: str, context: Dict[str, Any]) -> str:
    """Create a cache key from every prompt-affecting runtime input."""
    key_data = json.dumps(
        {
            "user_text": user_text.strip().lower(),
            "room_name": context.get("room_name", ""),
            "exits": sorted(context.get("exits", [])),
            "room_items": sorted(context.get("room_items", [])),
            "inventory": sorted(context.get("inventory", [])),
            "world_flags": context.get("world_flags", {}),
            "fear": context.get("fear", 0),
            "health": context.get("health", 100),
            "rooms_visited": context.get("rooms_visited", 1),
            "been_here_before": context.get("been_here_before", False),
            "active_quest": context.get("active_quest"),
            "can_advance_to_dawn": context.get("can_advance_to_dawn", False),
            "is_dawn_offer_active": context.get("is_dawn_offer_active", False),
        },
        sort_keys=True,
    )
    return hashlib.md5(key_data.encode()).hexdigest()


def response_cache_capacity() -> int:
    """Return the configured cache capacity, with zero disabling the cache."""
    from game.config import get_config

    raw_capacity = getattr(
        get_config(),
        "response_cache_size",
        DEFAULT_RESPONSE_CACHE_SIZE,
    )
    try:
        return max(0, int(raw_capacity))
    except (TypeError, ValueError):
        return DEFAULT_RESPONSE_CACHE_SIZE


def cache_get(
    key: str,
    *,
    debug: Callable[[str], None] | None = None,
) -> Optional[Intent]:
    """Read a cached intent while enforcing live configuration changes."""
    capacity = response_cache_capacity()
    if capacity == 0:
        response_cache.clear()
        return None

    while len(response_cache) > capacity:
        response_cache.popitem(last=False)

    if key in response_cache:
        response_cache.move_to_end(key)
        action, args, confidence, reply, effects, rationale = response_cache[key]
        if debug is not None:
            debug(f"Cache hit for key {key[:8]}...")
        return Intent(action, args, confidence, reply, effects, rationale)
    return None


def cache_put(key: str, intent: Intent) -> None:
    """Store an intent, evicting the least recently used entry if needed."""
    capacity = response_cache_capacity()
    if capacity == 0:
        response_cache.clear()
        return

    response_cache.pop(key, None)
    while len(response_cache) >= capacity:
        response_cache.popitem(last=False)

    response_cache[key] = (
        intent.action,
        intent.args,
        intent.confidence,
        intent.reply,
        intent.effects,
        intent.rationale,
    )


def clear_response_cache() -> None:
    response_cache.clear()
