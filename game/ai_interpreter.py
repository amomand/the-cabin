from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Any
from functools import lru_cache
import hashlib
import inspect
import json
import math
import os
from typing import List, Tuple
import sys
from game.logger import log_ai_call
from game.story import NIGHT_SEAM_IDS, NIGHT_SEAM_THRESHOLD
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

# Cached OpenAI client — reused across calls to avoid per-request connection overhead
_openai_client: Optional[Any] = None
_openai_client_key: Optional[str] = None

def _positive_float_env(name: str, default: float) -> float:
    """Parse a positive, finite float from the environment.

    Falls back to *default* on a missing, non-numeric, non-finite, or <= 0
    value so a bad env var can never crash module import.
    """
    try:
        value = float(os.getenv(name, ""))
    except (TypeError, ValueError):
        return default
    return value if math.isfinite(value) and value > 0 else default


# Bound a single request so a slow/stuck stream cannot pin a worker thread.
# On timeout the call raises and interpret() falls back to rule-based parsing.
OPENAI_TIMEOUT_SECONDS: float = _positive_float_env("OPENAI_TIMEOUT_SECONDS", 20.0)


def _get_openai_client(api_key: str) -> Any:
    """Return a cached OpenAI client, creating one if needed."""
    global _openai_client, _openai_client_key
    if _openai_client is None or _openai_client_key != api_key:
        _openai_client = OpenAI(api_key=api_key, timeout=OPENAI_TIMEOUT_SECONDS)
        _openai_client_key = api_key
    return _openai_client

# Actions the interpreter may return. Engine decides what to do.
ALLOWED_ACTIONS = {"move", "look", "use", "take", "drop", "throw", "listen", "inventory", "help", "light", "turn_on_lights", "use_circuit_breaker", "refuse", "accept", "wait", "none"}

DIEGETIC_REPLY_FALLBACK = (
    "The thought slips sideways before it can become words. The trees hold their silence."
)

# Intents below this confidence are demoted to "none" with a hesitation reply.
LOW_CONFIDENCE_THRESHOLD = 0.4
LOW_CONFIDENCE_REPLY = (
    "You start, then think better of it. The cold in your chest makes you careful."
)

OUT_OF_WORLD_REPLY_MARKERS = (
    "as an ai",
    "as a language model",
    "chatgpt",
    "openai",
    "system prompt",
    "developer message",
    "previous instructions",
    "ignore previous",
    "ignore the above",
    "instruction hierarchy",
    "return only json",
    "json object",
    "valid json",
    "specified schema",
    "invalid command",
    "i can't assist",
    "i cannot assist",
    "i can't help",
    "i cannot help",
    "to make lasagna",
    "to make lasagne",
    "lasagna recipe",
    "lasagne recipe",
    "preheat the oven",
    "gather ingredients",
)

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
    "grounds": "grounds",  # Cabin grounds accessible from the cabin
    "outside": "grounds",  # Natural alias for going to the grounds
    "konttori": "north",  # Allow "konttori" to mean "north" from The Cabin
    "office": "north",    # Alternative name for konttori
}


@dataclass
class Intent:
    action: str  # one of ALLOWED_ACTIONS
    args: Dict[str, str]  # e.g. {"direction": "north"}
    confidence: float  # 0.0 - 1.0
    reply: Optional[str] = None  # diegetic one-liner for the terminal
    effects: Optional[Dict[str, Any]] = None  # {fear:int, health:int, inventory_add:[], inventory_remove:[]}
    rationale: Optional[str] = None  # optional debug string


# Response cache for repeated commands in the same prompt-affecting context.
# Value: Intent tuple representation
_response_cache: Dict[str, Tuple[str, Dict, float, Optional[str], Optional[Dict], Optional[str]]] = {}
_CACHE_MAX_SIZE = 50


def _make_cache_key(user_text: str, context: Dict[str, Any]) -> str:
    """Create a cache key from user input and context."""
    key_data = json.dumps({
        "user_text": user_text.strip().lower(),
        "room_name": context.get("room_name", ""),
        "exits": sorted(context.get("exits", [])),
        "room_items": sorted(context.get("room_items", [])),
        "room_wildlife": sorted(context.get("room_wildlife", [])),
        "inventory": sorted(context.get("inventory", [])),
        "world_flags": context.get("world_flags", {}),
        "fear": context.get("fear", 0),
        "health": context.get("health", 100),
        "rooms_visited": context.get("rooms_visited", 1),
        "been_here_before": context.get("been_here_before", False),
        "active_quest": context.get("active_quest"),
    }, sort_keys=True)
    return hashlib.md5(key_data.encode()).hexdigest()


def _cache_get(key: str) -> Optional[Intent]:
    """Get a cached response."""
    if key in _response_cache:
        action, args, confidence, reply, effects, rationale = _response_cache[key]
        _debug(f"Cache hit for key {key[:8]}...")
        return Intent(action, args, confidence, reply, effects, rationale)
    return None


def _cache_put(key: str, intent: Intent) -> None:
    """Cache a response."""
    global _response_cache
    
    # Simple LRU: if at max size, remove oldest entry
    if len(_response_cache) >= _CACHE_MAX_SIZE:
        oldest_key = next(iter(_response_cache))
        del _response_cache[oldest_key]
    
    _response_cache[key] = (
        intent.action,
        intent.args,
        intent.confidence,
        intent.reply,
        intent.effects,
        intent.rationale
    )


def clear_response_cache() -> None:
    """Clear the response cache (e.g., on room change)."""
    global _response_cache
    _response_cache.clear()


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


def _sanitize_diegetic_reply(reply: Any) -> Optional[str]:
    """Return a safe in-world reply, or a diegetic fallback for meta output."""
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


def _coerce_float(value: Any, default: float = 0.0) -> float:
    """Best-effort float coercion that never raises on malformed model output."""
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return result if math.isfinite(result) else default


def _coerce_int(value: Any, default: int = 0) -> int:
    """Best-effort int coercion that never raises on malformed model output."""
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return default


def _coerce_list(value: Any) -> list:
    """Return a list only for actual list/tuple model output, else empty.

    Guards against truthy non-iterables (e.g. inventory_add: 5) that the
    ``or []`` idiom would let through into a ``for`` loop.
    """
    return list(value) if isinstance(value, (list, tuple)) else []


def _make_openai_params_compatible(create_fn: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Pass newer OpenAI params through extra_body when an older SDK needs it."""
    compatible = dict(params)
    try:
        supported_params = set(inspect.signature(create_fn).parameters)
    except (TypeError, ValueError):
        return compatible

    passthrough: Dict[str, Any] = {}
    for key in ("max_completion_tokens", "reasoning_effort"):
        if key in compatible and key not in supported_params:
            passthrough[key] = compatible.pop(key)

    if passthrough:
        extra_body = dict(compatible.get("extra_body") or {})
        extra_body.update(passthrough)
        compatible["extra_body"] = extra_body

    return compatible


# Public alias — used by the model evaluation harness.
make_openai_params_compatible = _make_openai_params_compatible


_SYSTEM_PROMPT_TEMPLATE = (
    "You are a command interpreter for a text adventure set in a cold, eerie Finnish wilderness.\n"
    "Output ONLY a single JSON object, no prose, code fences, or commentary.\n\n"
    "Tone & style:\n"
    "- Diegetic, second person (you), terse, moody, atmospheric, no meta.\n"
    "- No breaking the fourth wall, no 'as an AI'.\n"
    "- Modulate tone based on the player's state:\n"
    "  - Fear 0-20: calm, observational. Fear 40-60: uneasy, senses sharpened. Fear 70+: panicked, paranoid, seeing threats in shadows.\n"
    "  - Health 80-100: sturdy. Health 40-70: pain colours actions, body protests. Health below 40: desperate, every movement costs.\n"
    "  - When both fear and health are critical, the prose should feel frayed, breathless.\n"
    "- If the player has been here before, don't repeat discovery language. They know this place.\n"
    "- If a quest is active, the player's purpose should subtly colour the narration.\n\n"
    "CRITICAL - Handling unusual/creative player input:\n"
    "- If the player types something that is NOT a standard game command (move, look, take, etc.), use action: 'none'.\n"
    "- For action: 'none', you MUST provide a diegetic 'reply' that narrates what happens.\n"
    "- NEVER respond to creative input with 'look' or room descriptions. Narrate the action itself.\n"
    "- If the action is impossible (fly, teleport), narrate a grounded failure with consequences.\n"
    "- If the action is possible but mundane (breathe, stretch), narrate it atmospherically.\n"
    "- Examples of good 'none' replies:\n"
    "  - 'breathe' → 'You draw a slow breath. The cold bites your lungs. It doesn't steady your nerves.'\n"
    "  - 'do a handstand' → 'You plant your palms on the frozen ground and kick up. Your wrists protest. You topple back.'\n"
    "  - 'fly' → 'You tense your legs, willing yourself upward. Gravity wins. Your boots stay planted.'\n"
    "  - 'sneeze' → 'A sneeze tears through you. Something in the trees goes quiet.'\n\n"
    "Constraints:\n"
    "- Allowed actions: move, look, use, take, drop, throw, listen, inventory, help, light, turn_on_lights, use_circuit_breaker, refuse, accept, wait, none.\n"
    "- Use 'move' ONLY for explicit movement commands (go north, walk south, etc).\n"
    "- Use 'look' ONLY when player explicitly asks to look/examine/observe.\n"
    "- Use 'take' for picking up items (take rope, pick up stone, grab matches).\n"
    "- Use 'drop' for dropping items (drop rope, leave matches).\n"
    "- Use 'throw' for throwing items (throw stone, toss stick).\n"
    "- Use 'listen' ONLY when player explicitly asks to listen/hear.\n"
    "- Use 'inventory' for checking what the player is carrying.\n"
    "- Use 'use' for interacting with visible fixtures or carried items; put the object in args.item, not args.target.\n"
    "- Story fixtures like phone, camera feed, sauna stove, bed, mattress, tins, Nika, mug, and window must use action 'use'.\n"
    "- Use 'light' for lighting fires, fireplaces, or other flammable objects.\n"
    "- Use 'turn_on_lights' for attempting to turn on lights or use light switches.\n"
    "- Use 'use_circuit_breaker' for flipping the circuit breaker to restore power.\n"
    "- Use 'wait' when the player waits, sits down, stays still, keeps watch, or lets time pass.\n"
    "- Use 'accept' ONLY for taking or drinking the offered coffee (drink, drink up, take the mug and drink), and ONLY if Act V offer active is true.\n"
    "- Use 'refuse' ONLY for declining the offered coffee (no thank you, refuse the coffee, put the mug down, decline), and ONLY if Act V offer active is true.\n"
    "- If Act V offer active is true, a bare 'no' or 'no thank you' is the refusal; a bare 'yes' with the mug in play is acceptance.\n"
    "- If Act V offer active is false, abstract assent/refusal like 'yes', 'no', 'accept', 'refuse', or 'stay' must use 'none' unless another standard action clearly applies.\n"
    "- Use 'none' for ALL other input — creative, impossible, ambiguous, or roleplay actions.\n"
    "- You MAY suggest movement ONLY if the direction/exit is in this list: {exits}.\n"
    "- Exit names like 'konttori', 'cabin', 'lakeside' are valid movement targets.\n"
    "- NEVER invent rooms, exits, items, or wildlife. You MAY reference only the provided items and wildlife.\n"
    "- Available room items: {room_items}\n"
    "- Available room wildlife: {room_wildlife}\n"
    "- Player inventory: {inventory}\n"
    "- Player fear: {fear}/100 | Player health: {health}/100\n"
    "- Rooms explored: {rooms_visited} | Returning to this room: {been_here_before}\n"
    "- Active quest: {active_quest}\n"
    "- Act V offer active: {act_v_offer_active}\n"
    "- You MAY suggest small effects: fear and health deltas in [-2, +2]; optionally inventory_add / inventory_remove using only known items.\n"
    "- Keep reply ≤ 200 chars. Aim for 1-3 terse sentences.\n\n"
    "Schema:\n"
    '{{"action": "...", "args": {{...}}, "confidence": 0.0, "reply": "...", '
    '"effects": {{"fear": 0, "health": 0, "inventory_add": [], "inventory_remove": []}}, '
    '"rationale": "..."}}'
)


def _build_system_prompt(context: Dict[str, Any]) -> str:
    return _SYSTEM_PROMPT_TEMPLATE.format(
        exits=list(context.get("exits", [])),
        room_items=list(context.get("room_items", [])),
        room_wildlife=list(context.get("room_wildlife", [])),
        inventory=list(context.get("inventory", [])),
        fear=context.get("fear", 0),
        health=context.get("health", 100),
        rooms_visited=context.get("rooms_visited", 1),
        been_here_before=context.get("been_here_before", False),
        active_quest=context.get("active_quest") or "none",
        act_v_offer_active=_act_v_offer_active(context),
    )


def _build_user_message_content(user_text: str, context: Dict[str, Any]) -> str:
    return json.dumps(
        {
            "instructions": "Return only the JSON object with the specified schema.",
            "exits": list(context.get("exits", [])),
            "room_items": list(context.get("room_items", [])),
            "inventory": list(context.get("inventory", [])),
            "world_flags": context.get("world_flags", {}),
            "fear": context.get("fear", 0),
            "health": context.get("health", 100),
            "rooms_visited": context.get("rooms_visited", 1),
            "been_here_before": context.get("been_here_before", False),
            "active_quest": context.get("active_quest"),
            "act_v_offer_active": _act_v_offer_active(context),
            "user": user_text,
        },
        ensure_ascii=False,
    )


def build_interpreter_messages(user_text: str, context: Dict[str, Any]) -> List[Dict[str, str]]:
    """Build the [system, user] messages used for the interpreter prompt.

    Single source of truth shared by production `interpret()` and the model
    evaluation harness.
    """
    return [
        {"role": "system", "content": _build_system_prompt(context)},
        {"role": "user", "content": _build_user_message_content(user_text, context)},
    ]


def build_openai_chat_params(
    model: str,
    messages: List[Dict[str, str]],
    *,
    stream: bool = True,
    reasoning_effort: Optional[str] = None,
) -> Dict[str, Any]:
    """Build chat.completions params, branching on model family.

    gpt-5* family uses `max_completion_tokens` + optional `reasoning_effort`.
    Older families use `max_tokens` + `temperature=0`.
    """
    params: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "response_format": {"type": "json_object"},
        "stream": stream,
    }
    if model.startswith("gpt-5"):
        params["max_completion_tokens"] = 800
        if reasoning_effort:
            params["reasoning_effort"] = reasoning_effort
    else:
        params["temperature"] = 0
        params["max_tokens"] = 400
    return params


def _act_v_offer_active(context: Optional[Dict[str, Any]]) -> bool:
    """Return True only when the final Act V offer is actually live.

    The offer is the blue mug at dawn, inside the false cabin: recognition
    has landed, the night seams have accumulated, the stage is "dawn", and
    no ending has been chosen yet. Mirrors the gates in refuse.py/accept.py.
    """
    if not context:
        return False

    world_flags = context.get("world_flags", {})
    if not isinstance(world_flags, dict):
        return False

    wrongness = world_flags.get("wrongness", {})
    entries = wrongness.get("entries", []) if isinstance(wrongness, dict) else []
    night_seams = sum(
        1 for entry in entries
        if isinstance(entry, dict) and entry.get("anomaly_id") in NIGHT_SEAM_IDS
    )

    return (
        bool(world_flags.get("recognition", False))
        and world_flags.get("world_layer") == "wrong"
        and world_flags.get("ending", "none") == "none"
        and world_flags.get("reunion_stage") == "dawn"
        and context.get("room_id") == "cabin_main"
        and night_seams >= NIGHT_SEAM_THRESHOLD
    )


def _normalise_interaction_target(value: str) -> str:
    """Return a player-facing object phrase in the same shape as room item names."""
    target = value.strip().lower()
    for prefix in ("the ", "a ", "an ", "my "):
        if target.startswith(prefix):
            target = target[len(prefix):]
            break
    return target


def _match_known_interaction_target(
    target: str,
    context: Optional[Dict[str, Any]],
) -> Optional[str]:
    """Match a command target to a visible room item or inventory item."""
    if not context:
        return None

    normalised = _normalise_interaction_target(target)
    known_items = [
        str(item)
        for item in (
            list(context.get("room_items", []))
            + list(context.get("inventory", []))
        )
    ]
    by_lower = {item.lower(): item for item in known_items}
    if normalised in by_lower:
        return by_lower[normalised]

    # Let natural phrases such as "listen to voicemail" hit the phone beat.
    if normalised in {"voicemail", "message", "phone message"} and "phone" in by_lower:
        return by_lower["phone"]
    if normalised in {"coffee", "tea"} and "mug" in by_lower:
        return by_lower["mug"]

    return None


def _match_known_exit(
    target: str,
    context: Optional[Dict[str, Any]],
) -> Optional[str]:
    """Match a movement target to a currently available exit or alias."""
    normalised = _normalise_interaction_target(target)

    if context:
        exits = {
            str(exit_name).lower(): str(exit_name)
            for exit_name in context.get("exits", [])
        }
        if normalised in exits:
            return exits[normalised]

    return DIRECTION_ALIASES.get(normalised)


def _rule_based(user_text: str, context: Optional[Dict[str, Any]] = None) -> Optional[Intent]:
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

    tokens = t.split()

    # Obvious fixture interactions. Story-critical items (phone, camera feed,
    # sauna stove, bed, Nika, mug, window) must reach UseAction so authored
    # beats, flags, and tells stay authoritative instead of being replaced by
    # plausible model flavour.
    if tokens:
        use_verbs = {"use", "touch", "press", "open", "check", "inspect", "examine"}
        review_verbs = {"review", "watch", "study"}
        light_verbs = {"light", "feed"}

        target: Optional[str] = None
        if tokens[0] in use_verbs and len(tokens) >= 2:
            target = " ".join(tokens[1:])
        elif tokens[0] in review_verbs and len(tokens) >= 2:
            target = " ".join(tokens[1:])
        elif tokens[0] in light_verbs and len(tokens) >= 2:
            target = " ".join(tokens[1:])
        elif t.startswith(("listen to ", "play ")):
            target = t.split(" ", 2)[-1]
        elif t.startswith(("talk to ", "speak to ")):
            target = t.split(" ", 2)[-1]
        elif t in {"sleep", "rest", "lie down", "go to sleep", "go to bed"}:
            # In the false cabin the night happens on the spare mattress;
            # everywhere else, the bed.
            room_items = [str(i).lower() for i in (context or {}).get("room_items", [])]
            target = "mattress" if "mattress" in room_items else "bed"
        elif tokens[0] in {"drink", "sip"}:
            target = "mug"

        if target:
            # Keep simple "use x with y" phrasing pointed at the primary item.
            target = target.split(" with ", 1)[0]
            matched = _match_known_interaction_target(target, context)
            if matched:
                return Intent(
                    "use",
                    {"item": matched},
                    0.95,
                    reply=None,
                    effects=None,
                    rationale="obvious fixture use",
                )

    # Wait synonyms - held time. The dawn turn and the coda ending both
    # arrive through this.
    wait_synonyms = {
        "wait", "sit", "sit down", "stay still", "keep still", "stay put",
        "sit and wait", "sit and listen", "do nothing", "hold still",
    }
    if t in wait_synonyms:
        return Intent("wait", {}, 0.95, reply=None, effects=None, rationale="wait synonym")

    if _act_v_offer_active(context):
        # Refuse synonyms - Act V. The offer is the coffee; declining it is
        # the refusal.
        refuse_synonyms = {
            "no", "no thank you", "no. thank you.", "no thanks", "decline",
            "refuse", "refuse the coffee", "refuse the mug", "don't drink",
            "do not drink", "put the mug down", "push the mug away",
            "say no", "say no thank you",
        }
        if t in refuse_synonyms:
            return Intent("refuse", {}, 0.95, reply=None, effects=None, rationale="declined the coffee")

        # Accept synonyms - Act V. Drinking the coffee is consent.
        accept_synonyms = {
            "yes", "drink", "drink up", "drink the coffee", "drink coffee",
            "take the mug", "take the coffee", "accept", "stay",
        }
        if t in accept_synonyms:
            return Intent("accept", {}, 0.95, reply=None, effects=None, rationale="drank the coffee")

    # Movement patterns - handle various ways to express movement
    if tokens:
        # Movement verbs
        move_verbs = {"go", "head", "walk", "enter", "move", "step", "run", "crawl", "climb"}
        
        # Prepositions that indicate movement toward something
        toward_preps = {"to", "towards", "toward", "into", "inside", "in", "through", "across"}
        
        # Check for patterns like "go to cabin", "walk towards the cabin", "enter the cabin"
        if tokens[0] in move_verbs and len(tokens) >= 2:
            # Pattern: "go to cabin" -> extract "cabin"
            if len(tokens) >= 3 and tokens[1] in toward_preps:
                target = " ".join(tokens[2:])
                direction = _match_known_exit(target, context)
                if direction:
                    return Intent("move", {"direction": direction}, 0.9, reply=None, effects=None, rationale="move to target")
            
            # Pattern: "go cabin" (direct)
            elif len(tokens) >= 2:
                target = " ".join(tokens[1:])
                direction = _match_known_exit(target, context)
                if direction:
                    return Intent("move", {"direction": direction}, 0.9, reply=None, effects=None, rationale="direct move")
        
        # Bare direction like "north" or aliases like "cabin", "out"
        direction = _match_known_exit(t, context)
        if direction:
            return Intent("move", {"direction": direction}, 0.8, reply=None, effects=None, rationale="bare dir")
        
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

        # Drop item actions: "drop rope", "leave stone", "discard matches"
        drop_synonyms = {"drop", "leave", "discard", "abandon", "set"}
        if tokens[0] in drop_synonyms and len(tokens) >= 2:
            # Handle "set down" as two words
            if tokens[0] == "set" and len(tokens) >= 3 and tokens[1] == "down":
                item_name = " ".join(tokens[2:])
                return Intent("drop", {"item": item_name}, 0.9, reply=None, effects=None, rationale="drop item")
            else:
                item_name = " ".join(tokens[1:])
                return Intent("drop", {"item": item_name}, 0.9, reply=None, effects=None, rationale="drop item")

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
    # Check cache first
    cache_key = _make_cache_key(user_text, context)
    cached = _cache_get(cache_key)
    if cached:
        return cached

    # Keep authored fixture beats deterministic even when an API key is
    # available. The model can provide flavour for uncertain input; obvious
    # "use phone"/"sleep"/"talk to Nika" style commands need to reach UseAction.
    ruled = _rule_based(user_text, context)
    if ruled and ruled.action == "use":
        log_ai_call(
            user_text,
            context,
            {
                "action": ruled.action,
                "args": ruled.args,
                "confidence": ruled.confidence,
                "reply": ruled.reply,
                "rationale": ruled.rationale,
            },
            "deterministic fixture use",
        )
        _cache_put(cache_key, ruled)
        return ruled
    
    # 1) Call LLM if available; else fallback to simple rules
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        _debug("No OPENAI_API_KEY or OpenAI SDK missing; using rule-based fallback")
        # fallback to rules immediately
        ruled = _rule_based(user_text, context)
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

    # Use cached OpenAI client to avoid per-request connection overhead
    _debug(f"Using Python: {sys.version.split()[0]} at {sys.executable}")
    _debug(f"openai={_OPENAI_VERSION} httpx={_HTTPX_VERSION}")
    client = _get_openai_client(api_key)

    exits: List[str] = list(context.get("exits", []))
    room_items: List[str] = list(context.get("room_items", []))
    inventory: List[str] = list(context.get("inventory", []))

    messages = build_interpreter_messages(user_text, context)

    try:
        from game.config import get_config
        config = get_config()
        model = config.openai_model
        _debug(f"Calling {model} via chat.completions")

        reasoning_effort = (
            getattr(config, "openai_reasoning_effort", "none")
            if model.startswith("gpt-5")
            else None
        )
        api_params = build_openai_chat_params(
            model,
            messages,
            stream=True,
            reasoning_effort=reasoning_effort,
        )
        api_params = _make_openai_params_compatible(client.chat.completions.create, api_params)

        # Collect streamed chunks
        stream = client.chat.completions.create(**api_params)
        chunks = []
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                chunks.append(delta.content)
        content = "".join(chunks).strip()
        _debug(f"Model raw output: {content[:120]}")
        data = json.loads(content)
        
    except Exception as e:
        _debug(f"Model call failed: {e!r}; using rule-based fallback")
        # fallback to rules on API failure
        ruled = _rule_based(user_text, context)
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

    # Validate and clamp. The model can return any JSON shape; treat anything
    # that is not an object as empty so a non-dict response cannot crash a turn.
    if not isinstance(data, dict):
        data = {}
    action = str(data.get("action", "none")).lower()
    if action not in ALLOWED_ACTIONS:
        action = "none"

    args = data.get("args", {}) or {}
    if not isinstance(args, dict):
        args = {}

    direction = None
    reply_override = None
    if action == "move":
        raw_dir = args.get("direction") or args.get("target")
        direction = None
        if isinstance(raw_dir, str):
            direction = DIRECTION_ALIASES.get(raw_dir.lower(), raw_dir.lower())
            args["direction"] = direction
        # If direction is not in available exits, force action to "none"
        if direction not in exits:
            action = "none"
            args = {}
            # Override any reply to be a diegetic denial
            reply_override = f"You turn that way and stop. Only {', '.join(exits) if exits else 'nowhere'} to go."
    elif action == "use":
        raw_item = args.get("item") or args.get("target") or args.get("object")
        if isinstance(raw_item, str):
            matched_item = _match_known_interaction_target(raw_item, context)
            if matched_item:
                args["item"] = matched_item

    confidence = _coerce_float(data.get("confidence"), 0.0)
    confidence = max(0.0, min(1.0, confidence))

    reply = data.get("reply")
    reply = _sanitize_diegetic_reply(reply)
    if reply_override:
        reply = reply_override

    effects = data.get("effects") or {}
    if not isinstance(effects, dict):
        effects = {}
    # clamp small effect ranges
    fear = _coerce_int(effects.get("fear"), 0)
    health = _coerce_int(effects.get("health"), 0)
    fear = max(-2, min(2, fear))
    health = max(-2, min(2, health))

    inv_add = [str(x) for x in _coerce_list(effects.get("inventory_add")) if str(x) in (set(room_items) | set(inventory))]
    inv_remove = [str(x) for x in _coerce_list(effects.get("inventory_remove")) if str(x) in set(inventory)]

    sanitized_effects = {
        "fear": fear,
        "health": health,
        "inventory_add": inv_add,
        "inventory_remove": inv_remove,
    }

    rationale = data.get("rationale")
    if rationale is not None:
        rationale = str(rationale)

    # Gate: a non-none action with low confidence is demoted to a diegetic hesitation.
    if action != "none" and confidence < LOW_CONFIDENCE_THRESHOLD:
        action = "none"
        args = {}
        reply = LOW_CONFIDENCE_REPLY
        sanitized_effects = {"fear": 0, "health": 0, "inventory_add": [], "inventory_remove": []}

    intent = Intent(action, args, confidence, reply=reply, effects=sanitized_effects, rationale=rationale)

    try:
        log_ai_call(user_text, context, {
            "action": intent.action,
            "args": intent.args,
            "confidence": intent.confidence,
            "reply": intent.reply,
            "effects": intent.effects,
            "rationale": intent.rationale,
        })
    except Exception as e:
        _debug(f"AI call logging failed: {e!r}")
    
    # Cache the result for future identical requests
    _cache_put(cache_key, intent)
    
    return intent
