from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

# Actions the interpreter may return. Engine decides what to do.
ALLOWED_ACTIONS = {"move", "look", "use", "take", "drop", "inventory", "help", "none"}

# Direction and exit aliasing. Add domain-specific aliases here (e.g., "out", "cabin").
DIRECTION_ALIASES = {
    "n": "north",
    "s": "south",
    "e": "east",
    "w": "west",
    "north": "north",
    "south": "south",
    "east": "east",
    "west": "west",
    "cabin": "cabin",
    "out": "out",
}


@dataclass
class Intent:
    action: str  # one of ALLOWED_ACTIONS
    args: Dict[str, str]  # e.g. {"direction": "north"}
    confidence: float  # 0.0 - 1.0
    rationale: Optional[str] = None  # optional debug string


def _rule_based(user_text: str) -> Optional[Intent]:
    t = user_text.strip().lower()
    if not t:
        return Intent("none", {}, 0.0, "empty")

    # a few forgiving rules
    if t in {"inv", "inventory", "bag"}:
        return Intent("inventory", {}, 0.95, "synonym")

    if t in {"look", "l", "examine"}:
        return Intent("look", {}, 0.9, "synonym")

    if t in {"help", "?"}:
        return Intent("help", {}, 0.9, "synonym")

    # simple verb-noun movement
    tokens = t.split()
    if tokens:
        # canonicalise direction
        if tokens[0] in {"go", "head", "walk", "enter"} and len(tokens) >= 2:
            d = DIRECTION_ALIASES.get(tokens[1])
            if d:
                return Intent("move", {"direction": d}, 0.9, "rule move")
        # bare direction like “north” or aliases like “cabin”, “out”
        if tokens[0] in DIRECTION_ALIASES:
            return Intent("move", {"direction": DIRECTION_ALIASES[tokens[0]]}, 0.8, "bare dir")

    return None


def interpret(user_text: str, context: Dict) -> Intent:
    """
    Convert a player's input into an Intent.

    context may include:
      {
        "room_name": str,
        "exits": ["north","south",...],
        "inventory": [...],
        "world_flags": {...},
        "allowed_actions": list[str]
      }
    """
    # 1) try simple rules first
    ruled = _rule_based(user_text)
    if ruled:
        # if rule says move, but direction not in exits, lower confidence so engine can reject gracefully
        if ruled.action == "move":
            exits = set(context.get("exits", []))
            if ruled.args.get("direction") not in exits:
                ruled.confidence = min(ruled.confidence, 0.5)
        return ruled

    # 2) (optional) call LLM here to classify → Intent  (stub below)
    #    If you haven’t wired an API yet, just return a neutral fallback.
    return Intent("none", {}, 0.0, "fallback")


