from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Any
import json
import os
from typing import List
import sys
from game.logger import log_ai_call
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
ALLOWED_ACTIONS = {"move", "look", "use", "take", "drop", "throw", "listen", "inventory", "help", "light", "turn_on_lights", "use_circuit_breaker", "none"}

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
    # Also log to file for debugging purposes
    try:
        from game.logger import get_logger
        logger = get_logger()
        logger.debug(f"AI DEBUG: {msg}")
    except:
        pass  # Don't break if logger isn't available


def _rule_based(user_text: str) -> Optional[Intent]:
    t = user_text.strip().lower()
    if not t:
        return Intent("none", {}, 0.0, "empty")

    # Inventory synonyms
    inventory_synonyms = {
        "inv", "inventory", "bag", "what am i carrying", "what things have i got",
        "what do i have", "check inventory", "show inventory", "what's in my bag",
        "what am i holding", "what do i own", "my stuff", "my things"
    }
    if t in inventory_synonyms:
        return Intent("inventory", {}, 0.95, reply=None, effects=None, rationale="inventory synonym")

    # Look synonyms
    look_synonyms = {"look", "l", "examine", "inspect", "check", "see", "observe"}
    if t in look_synonyms:
        return Intent("look", {}, 0.9, reply=None, effects=None, rationale="look synonym")

    # Listen synonyms
    listen_synonyms = {"listen", "hear", "sound", "noise", "quiet"}
    if t in listen_synonyms:
        return Intent("listen", {}, 0.9, reply=None, effects=None, rationale="listen synonym")

    # Help synonyms
    help_synonyms = {"help", "?", "what can i do", "commands", "hint"}
    if t in help_synonyms:
        return Intent("help", {}, 0.9, reply=None, effects=None, rationale="help synonym")

    # Movement patterns - handle various ways to express movement
    tokens = t.split()
    if tokens:
        # Movement verbs
        move_verbs = {"go", "head", "walk", "enter", "move", "step", "run", "crawl", "climb"}
        
        # Prepositions that indicate movement toward something
        toward_preps = {"to", "towards", "toward", "into", "inside", "in", "through", "across"}
        
        # Check for patterns like "go to cabin", "walk towards the cabin", "enter the cabin"
        if tokens[0] in move_verbs and len(tokens) >= 2:
            # Pattern: "go to cabin" -> extract "cabin"
            if len(tokens) >= 3 and tokens[1] in toward_preps:
                target = tokens[2]
                # Handle articles: "go to the cabin" -> extract "cabin"
                if target in {"the", "a", "an"} and len(tokens) >= 4:
                    target = tokens[3]
                # Check if target is a known exit
                if target in DIRECTION_ALIASES:
                    return Intent("move", {"direction": DIRECTION_ALIASES[target]}, 0.9, reply=None, effects=None, rationale="move to target")
            
            # Pattern: "go cabin" (direct)
            elif len(tokens) >= 2:
                target = tokens[1]
                if target in DIRECTION_ALIASES:
                    return Intent("move", {"direction": DIRECTION_ALIASES[target]}, 0.9, reply=None, effects=None, rationale="direct move")
        
        # Bare direction like "north" or aliases like "cabin", "out"
        if tokens[0] in DIRECTION_ALIASES:
            return Intent("move", {"direction": DIRECTION_ALIASES[tokens[0]]}, 0.8, reply=None, effects=None, rationale="bare dir")
        
        # Take item actions: "take rope", "pick up stone", "grab matches"
        take_synonyms = {"take", "pick", "grab", "snatch", "get", "collect", "acquire"}
        if tokens[0] in take_synonyms and len(tokens) >= 2:
            # Handle "pick up" as two words
            if tokens[0] == "pick" and len(tokens) >= 3 and tokens[1] == "up":
                item_name = " ".join(tokens[2:])
                return Intent("take", {"item": item_name}, 0.9, reply=None, effects=None, rationale="take item")
            else:
                item_name = " ".join(tokens[1:])
                return Intent("take", {"item": item_name}, 0.9, reply=None, effects=None, rationale="take item")
        
        # Throw item actions: "throw stone", "toss stick", "hurl rock"
        throw_synonyms = {"throw", "toss", "hurl", "chuck", "fling", "pitch"}
        if tokens[0] in throw_synonyms and len(tokens) >= 2:
            # Check if throwing at something specific: "throw stone at wolf"
            remaining_words = tokens[1:]
            if len(remaining_words) >= 3 and remaining_words[1] == "at":
                item_name = remaining_words[0]
                target_name = " ".join(remaining_words[2:])
                return Intent("throw", {"item": item_name, "target": target_name}, 0.9, reply=None, effects=None, rationale="throw at target")
            else:
                item_name = " ".join(remaining_words)
                return Intent("throw", {"item": item_name}, 0.9, reply=None, effects=None, rationale="throw item")

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
            # Log the fallback response
            response_data = {
                "action": ruled.action,
                "args": ruled.args,
                "confidence": ruled.confidence,
                "reply": ruled.reply,
                "rationale": ruled.rationale
            }
            log_ai_call(user_text, context, response_data, "No API key - using rule-based fallback")
            return ruled
        fallback_intent = Intent("none", {}, 0.0, reply=None, effects=None, rationale="fallback-no-key")
        log_ai_call(user_text, context, {"action": "none", "args": {}, "confidence": 0.0, "reply": None, "rationale": "fallback-no-key"}, "No API key - no rule match")
        return fallback_intent

    # Use modern OpenAI client; pass key explicitly to avoid env/proxy issues in some setups
    _debug(f"Using Python: {sys.version.split()[0]} at {sys.executable}")
    _debug(f"openai={_OPENAI_VERSION} httpx={_HTTPX_VERSION}")
    client = OpenAI(api_key=api_key)

    exits: List[str] = list(context.get("exits", []))
    room_items: List[str] = list(context.get("room_items", []))
    inventory: List[str] = list(context.get("inventory", []))
    room_wildlife: List[str] = list(context.get("room_wildlife", []))

    system_prompt = (
        "You are a command interpreter for a text adventure set in a cold, eerie Finnish wilderness.\n"
        "Output ONLY a single JSON object, no prose, code fences, or commentary.\n\n"
        "Tone & style:\n"
        "- Diegetic, second person (you), terse, moody, atmospheric, no meta.\n"
        "- No breaking the fourth wall, no 'as an AI'.\n\n"
        "Constraints:\n"
        "- Allowed actions: move, look, use, take, drop, throw, inventory, help, light, turn_on_lights, use_circuit_breaker, none.\n"
        "- Use 'move' ONLY for explicit movement commands (go north, walk south, etc).\n"
        "- Use 'take' for picking up items (take rope, pick up stone, grab matches).\n"
        "- Use 'throw' for throwing items (throw stone, toss stick).\n"
        "- Use 'listen' for hearing wildlife sounds.\n"
        "- Use 'inventory' for checking what the player is carrying.\n"
        "- Use 'light' for lighting fires, fireplaces, or other flammable objects.\n"
        "- Use 'turn_on_lights' for attempting to turn on lights or use light switches.\n"
        "- Use 'use_circuit_breaker' for flipping the circuit breaker to restore power.\n"
        "- Use 'none' for ambiguous, impossible, or non-movement actions.\n"
        "- You MAY suggest movement ONLY if the direction/exit is in this list: {exits}.\n"
        "- Exit names like 'konttori', 'cabin', 'lakeside' are valid movement targets.\n"
        "- NEVER invent rooms, exits, items, or wildlife. You MAY reference only the provided items and wildlife.\n"
        "- Available room items: {room_items}\n"
        "- Available room wildlife: {room_wildlife}\n"
        "- Player inventory: {inventory}\n"
        "- When player uses 'look', include room items and visible wildlife in your reply naturally.\n"
        "- When player uses 'listen', describe wildlife sounds present in the room.\n"
        "- You MAY suggest small effects: fear and health deltas in [-2, +2]; optionally inventory_add / inventory_remove using only known items.\n"
        "- Keep reply ≤ 140 chars.\n\n"
        "Schema:\n"
        '{{"action": "...", "args": {{...}}, "confidence": 0.0, "reply": "...", '
        '"effects": {{"fear": 0, "health": 0, "inventory_add": [], "inventory_remove": []}}, '
        '"rationale": "..."}}'
    )

    # Inject available exits, items, and wildlife into the prompt
    system_prompt = system_prompt.format(
        exits=exits,
        room_items=room_items,
        room_wildlife=room_wildlife,
        inventory=inventory
    )

    user_payload = {
        "room_name": context.get("room_name", ""),
        "exits": exits,
        "room_items": room_items,
        "room_wildlife": room_wildlife,
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
        
        # Log successful AI call
        log_ai_call(user_text, context, data)
        
    except Exception as e:
        _debug(f"Model call failed: {e!r}; using rule-based fallback")
        # fallback to rules on API failure
        ruled = _rule_based(user_text)
        if ruled:
            exits = set(context.get("exits", []))
            if ruled.action == "move" and ruled.args.get("direction") not in exits:
                ruled.confidence = min(ruled.confidence, 0.5)
            # Log the fallback response
            response_data = {
                "action": ruled.action,
                "args": ruled.args,
                "confidence": ruled.confidence,
                "reply": ruled.reply,
                "rationale": ruled.rationale
            }
            log_ai_call(user_text, context, response_data, f"API call failed: {e}")
            return ruled
        fallback_intent = Intent("none", {}, 0.0, reply=None, effects=None, rationale="fallback-error")
        log_ai_call(user_text, context, {"action": "none", "args": {}, "confidence": 0.0, "reply": None, "rationale": "fallback-error"}, f"API call failed: {e}")
        return fallback_intent

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
        # If direction is not in available exits, force action to "none"
        if direction not in exits:
            action = "none"
            args = {}
            # Override any reply to be a diegetic denial
            reply = f"You turn that way and stop. Only {', '.join(exits) if exits else 'nowhere'} to go."

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


