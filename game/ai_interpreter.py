from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Any
import json
import os
from typing import List
import sys
try:
    from dotenv import load_dotenv, find_dotenv  # type: ignore
    load_dotenv(find_dotenv())
except Exception:
    # dotenv is optional at runtime; if missing, rely on env
    pass

# Optional: capture library versions for debug
try:
    import httpx as _httpx  # type: ignore
    _HTTPX_VERSION = getattr(_httpx, "__version__", "unknown")
except Exception:  # pragma: no cover
    _httpx = None
    _HTTPX_VERSION = "unavailable"
try:
    import openai as _openai_mod  # type: ignore
    _OPENAI_VERSION = getattr(_openai_mod, "__version__", "unknown")
except Exception:
    _openai_mod = None
    _OPENAI_VERSION = "unavailable"

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover - optional dependency during dev
    OpenAI = None  # type: ignore

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
    reply: Optional[str] = None  # diegetic one-liner for the terminal
    effects: Optional[Dict[str, Any]] = None  # {fear:int, health:int, inventory_add:[], inventory_remove:[]}
    rationale: Optional[str] = None  # optional debug string


def _debug(msg: str) -> None:
    if os.getenv("CABIN_DEBUG") == "1":
        print(f"[AI DEBUG] {msg}", file=sys.stderr)


def _rule_based(user_text: str) -> Optional[Intent]:
    t = user_text.strip().lower()
    if not t:
        return Intent("none", {}, 0.0, "empty")

    # a few forgiving rules
    if t in {"inv", "inventory", "bag"}:
        return Intent("inventory", {}, 0.95, reply=None, effects=None, rationale="synonym")

    if t in {"look", "l", "examine"}:
        return Intent("look", {}, 0.9, reply=None, effects=None, rationale="synonym")

    if t in {"help", "?"}:
        return Intent("help", {}, 0.9, reply=None, effects=None, rationale="synonym")

    # simple verb-noun movement
    tokens = t.split()
    if tokens:
        # canonicalise direction
        if tokens[0] in {"go", "head", "walk", "enter"} and len(tokens) >= 2:
            d = DIRECTION_ALIASES.get(tokens[1])
            if d:
                return Intent("move", {"direction": d}, 0.9, reply=None, effects=None, rationale="rule move")
        # bare direction like “north” or aliases like “cabin”, “out”
        if tokens[0] in DIRECTION_ALIASES:
            return Intent("move", {"direction": DIRECTION_ALIASES[tokens[0]]}, 0.8, reply=None, effects=None, rationale="bare dir")

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
    # 1) Call LLM if available; else fallback to simple rules
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        _debug("No OPENAI_API_KEY or OpenAI SDK missing; using rule-based fallback")
        # fallback to rules immediately
        ruled = _rule_based(user_text)
        if ruled:
            exits = set(context.get("exits", []))
            if ruled.action == "move" and ruled.args.get("direction") not in exits:
                ruled.confidence = min(ruled.confidence, 0.5)
            return ruled
        return Intent("none", {}, 0.0, reply=None, effects=None, rationale="fallback-no-key")

    # Use modern OpenAI client; pass key explicitly to avoid env/proxy issues in some setups
    _debug(f"Using Python: {sys.version.split()[0]} at {sys.executable}")
    _debug(f"openai={_OPENAI_VERSION} httpx={_HTTPX_VERSION}")
    client = OpenAI(api_key=api_key)

    exits: List[str] = list(context.get("exits", []))
    room_items: List[str] = list(context.get("room_items", []))
    inventory: List[str] = list(context.get("inventory", []))

    system_prompt = (
        "You are a command interpreter for a text adventure set in a cold, eerie Finnish wilderness.\n"
        "Output ONLY a single JSON object, no prose, code fences, or commentary.\n\n"
        "Tone & style:\n"
        "- Diegetic, second person (you), terse, moody, atmospheric, no meta.\n"
        "- No breaking the fourth wall, no 'as an AI'.\n\n"
        "Constraints:\n"
        "- Allowed actions: move, look, use, take, drop, inventory, help, none.\n"
        "- You MAY suggest movement ONLY if the direction is in this list.\n"
        "- NEVER invent rooms, exits, or items. You MAY reference only the provided items.\n"
        "- You MAY suggest small effects: fear and health deltas in [-2, +2]; optionally inventory_add / inventory_remove using only known items.\n"
        "- Keep reply ≤ 140 chars.\n\n"
        "Schema:\n"
        '{"action": "...", "args": {...}, "confidence": 0.0, "reply": "...", '
        '"effects": {"fear": 0, "health": 0, "inventory_add": [], "inventory_remove": []}, '
        '"rationale": "..."}'
    )

    user_payload = {
        "room_name": context.get("room_name", ""),
        "exits": exits,
        "room_items": room_items,
        "inventory": inventory,
        "world_flags": context.get("world_flags", {}),
        "input": user_text,
    }

    try:
        _debug("Calling gpt-4o-mini via chat.completions")
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "instructions": "Return only the JSON object with the specified schema.",
                            "exits": exits,
                            "room_items": room_items,
                            "inventory": inventory,
                            "world_flags": user_payload["world_flags"],
                            "user": user_text,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        )
        content = (resp.choices[0].message.content or "").strip()
        # Some models may wrap in fences; try to extract JSON
        if content.startswith("```"):
            lines = content.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()
        _debug(f"Model raw output: {content[:120]}")
        data = json.loads(content)
    except Exception as e:
        _debug(f"Model call failed: {e!r}; using rule-based fallback")
        # fallback to rules on API failure
        ruled = _rule_based(user_text)
        if ruled:
            exits = set(context.get("exits", []))
            if ruled.action == "move" and ruled.args.get("direction") not in exits:
                ruled.confidence = min(ruled.confidence, 0.5)
            return ruled
        return Intent("none", {}, 0.0, reply=None, effects=None, rationale="fallback-error")

    # Validate and clamp
    action = str(data.get("action", "none")).lower()
    if action not in ALLOWED_ACTIONS:
        action = "none"

    args = data.get("args", {}) or {}
    if not isinstance(args, dict):
        args = {}

    direction = None
    if action == "move":
        raw_dir = args.get("direction")
        direction = None
        if isinstance(raw_dir, str):
            direction = DIRECTION_ALIASES.get(raw_dir.lower(), raw_dir.lower())
            args["direction"] = direction
        if direction not in exits:
            action = "none"
            args = {}

    confidence = float(data.get("confidence", 0.0))
    confidence = max(0.0, min(1.0, confidence))

    reply = data.get("reply")
    if reply is not None:
        reply = str(reply)[:140]

    effects = data.get("effects") or {}
    if not isinstance(effects, dict):
        effects = {}
    # clamp small effect ranges
    fear = int(effects.get("fear", 0))
    health = int(effects.get("health", 0))
    fear = max(-2, min(2, fear))
    health = max(-2, min(2, health))

    inv_add = [str(x) for x in effects.get("inventory_add", []) if str(x) in (set(room_items) | set(inventory))]
    inv_remove = [str(x) for x in effects.get("inventory_remove", []) if str(x) in set(inventory)]

    sanitized_effects = {
        "fear": fear,
        "health": health,
        "inventory_add": inv_add,
        "inventory_remove": inv_remove,
    }

    rationale = data.get("rationale")
    if rationale is not None:
        rationale = str(rationale)

    return Intent(action, args, confidence, reply=reply, effects=sanitized_effects, rationale=rationale)


