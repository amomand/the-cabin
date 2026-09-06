"""Interpreter prompt and context construction."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from game.ai.rules import act_v_offer_active


SYSTEM_PROMPT_TEMPLATE = (
    "You are a command interpreter for a text adventure set in a cold, eerie Finnish wilderness.\n"
    "Output ONLY a single JSON object, no prose, code fences, or commentary.\n\n"
    "Reply guidance:\n"
    "- Keep replies in-world, with no parser or AI explanations.\n"
    "- Use second person and present tense. Answer the attempted action in Elli's current situation.\n"
    "- Elli is practical and observant; ordinary comfort and an occasional dry note belong here too.\n"
    "- Keep a mundane reply plain when the action needs no more. Do not add menace to fill silence.\n"
    "- Use only supplied scene facts. Fear and health are limits, not permission to invent injuries, threats or perceptions.\n"
    "- Do not invent events, sound sources, dialogue or another character's reactions.\n"
    "- Do not narrate discoveries, advance care or consent, consume coffee, change posture established by a story beat, or move the player. Authored actions own those outcomes.\n"
    "- On a revisit, do not repeat a discovery or arrival act.\n"
    "- World flags are author-side constraints, not facts to disclose. Never explain the entity or the rules of the place.\n"
    "{wrong_layer_rules}\n"
    "Handling unusual/creative player input:\n"
    "- If no standard action applies, use action: 'none' and a brief diegetic 'reply'.\n"
    "- Reply to the attempt itself, not with a room description. Leave consequential outcomes to authored actions.\n"
    "- Examples, subject to the current scene:\n"
    "  - 'breathe' → 'You take a slow breath and let it out.'\n"
    "  - 'fly' → 'You try to rise into the air. You stay exactly where you are.'\n"
    "  - 'sneeze' → 'You sneeze into your sleeve.'\n\n"
    "Constraints:\n"
    "- Allowed actions: move, look, use, take, drop, throw, listen, inventory, help, light, turn_on_lights, use_circuit_breaker, refuse, accept, wait, none.\n"
    "- Use 'move' ONLY for explicit movement commands (go north, walk south, etc).\n"
    "- Retreating without a named exit or direction (back away, step back, retreat) is NOT movement; use 'none' and narrate the retreat in place.\n"
    "- Use 'look' ONLY when player explicitly asks to look/examine/observe. Put a particular subject in args.target; leave args empty for general attention. Authored observation supplies the reply.\n"
    "- Use 'take' for picking up items (take rope, pick up stone, grab matches).\n"
    "- Use 'drop' for dropping items (drop rope, leave matches).\n"
    "- Use 'throw' for throwing items (throw stone, toss stick).\n"
    "- Use 'listen' ONLY when player explicitly asks to listen/hear. Put a sound or subject in args.target; listening does not operate or consume it. Authored observation supplies the reply.\n"
    "- Use 'inventory' for checking what the player is carrying.\n"
    "- Use 'use' for interacting with visible fixtures or carried items; put the object in args.item, not args.target.\n"
    "- Operating story fixtures, playing the phone message, reviewing saved camera images, talking to Nika, drinking coffee or using bedding require 'use'. Merely looking at, studying, watching or listening to a fixture uses 'look' or 'listen', never 'use'.\n"
    "- Use 'light' for lighting fires, fireplaces, or other flammable objects.\n"
    "- Use 'turn_on_lights' for attempting to turn on lights or use light switches.\n"
    "- Use 'use_circuit_breaker' for flipping the circuit breaker to restore power.\n"
    "- Use 'wait' when the player waits, sits down, stays still, keeps watch, or lets time pass.\n"
    "- Use 'accept' ONLY for accepting the offered coffee, whether by taking/drinking it or by explicit assent (yes, accept, stay), and ONLY if Act V offer active is true.\n"
    "- Use 'refuse' ONLY for declining the offered coffee (no thank you, refuse the coffee, put the mug down, decline), and ONLY if Act V offer active is true.\n"
    "- If Act V offer active is true, a bare 'no' or 'no thank you' is the refusal; a bare 'yes' with the mug in play is acceptance.\n"
    "- If Act V offer active is false, abstract assent/refusal like 'yes', 'no', 'accept', 'refuse', or 'stay' must use 'none' unless another standard action clearly applies.\n"
    "- If Act V offer active is false, 'accept' and 'refuse' are never valid — even a decline aimed at the mug or coffee is 'none', narrated in the scene.\n"
    "- Use 'none' for ALL other input — creative, impossible, ambiguous, or roleplay actions.\n"
    "- You MAY suggest movement ONLY if the direction/exit is in this list: {exits}.\n"
    "- Exit names like 'konttori', 'cabin', 'lakeside' are valid movement targets.\n"
    "- NEVER invent rooms, exits, or items. You MAY reference only the provided items.\n"
    "- Available room items: {room_items}\n"
    "- Player inventory: {inventory}\n"
    "- Carried story equipment (available to use, never take or drop): {equipment}\n"
    "- Player fear: {fear}/100 | Player health: {health}/100\n"
    "- Rooms explored: {rooms_visited} | Returning to this room: {been_here_before}\n"
    "- Active quest: {active_quest}\n"
    "- Act V offer active: {act_v_offer_active}\n"
    "- You MAY suggest small effects: fear and health deltas in [-2, +2]; optionally inventory_add / inventory_remove using only known items.\n"
    "- Keep reply ≤ 200 chars. Use only as much as the attempt needs.\n\n"
    "Schema:\n"
    '{{"action": "...", "args": {{...}}, "confidence": 0.0, "reply": "...", '
    '"effects": {{"fear": 0, "health": 0, "inventory_add": [], "inventory_remove": []}}, '
    '"rationale": "..."}}'
)


def wrong_layer_rules(context: Optional[Dict[str, Any]]) -> str:
    """Return false-cabin constraints for model flavour."""
    if not context:
        return ""
    world_flags = context.get("world_flags", {})
    if not isinstance(world_flags, dict) or world_flags.get("world_layer") != "wrong":
        return ""

    if world_flags.get("ending") == "escaped":
        return (
            "\nThe false cabin (pretence stopped):\n"
            "- The thing that looked like Nika has stopped pretending. It does not "
            "engage, answer, or react. Nothing in this place is interested in the "
            "player any more.\n"
            "- Replies about it are flat and minimal. Never describe what is under "
            "the face. Never name or explain it.\n"
        )

    identity = (
        "- Recognition has been narrated. Elli knows this is the thing wearing Nika; do not restore the pretence for her.\n"
        if world_flags.get("recognition")
        else "- Refer to the companion as Nika. Do not reveal what she is or anticipate recognition.\n"
    )
    return (
        "\nWrong layer:\n"
        "- Use the current room: the companion is in the cabin, not beside Elli in the clearing or woods.\n"
        + identity
        + "- Care, dialogue, coffee, the night and the dawn offer belong to authored actions. Do not perform them in flavour.\n"
        "- Do not volunteer seams such as frost, knuckles, breathing, the mug or boards; authored observations own disclosure.\n"
    )


def build_system_prompt(context: Dict[str, Any]) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        exits=list(context.get("exits", [])),
        room_items=list(context.get("room_items", [])),
        inventory=list(context.get("inventory", [])),
        equipment=list(context.get("equipment", [])),
        fear=context.get("fear", 0),
        health=context.get("health", 100),
        rooms_visited=context.get("rooms_visited", 1),
        been_here_before=context.get("been_here_before", False),
        active_quest=context.get("active_quest") or "none",
        act_v_offer_active=act_v_offer_active(context),
        wrong_layer_rules=wrong_layer_rules(context),
    )


def build_user_message_content(user_text: str, context: Dict[str, Any]) -> str:
    return json.dumps(
        {
            "instructions": "Return only the JSON object with the specified schema.",
            "room_name": context.get("room_name", ""),
            "room_id": context.get("room_id", ""),
            "is_indoors": context.get("is_indoors"),
            "exits": list(context.get("exits", [])),
            "room_items": list(context.get("room_items", [])),
            "inventory": list(context.get("inventory", [])),
            "equipment": list(context.get("equipment", [])),
            "world_flags": context.get("world_flags", {}),
            "fear": context.get("fear", 0),
            "health": context.get("health", 100),
            "rooms_visited": context.get("rooms_visited", 1),
            "been_here_before": context.get("been_here_before", False),
            "active_quest": context.get("active_quest"),
            "act_v_offer_active": act_v_offer_active(context),
            "user": user_text,
        },
        ensure_ascii=False,
    )


def build_interpreter_messages(
    user_text: str,
    context: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Build the exact system and user messages used by production and evals."""
    return [
        {"role": "system", "content": build_system_prompt(context)},
        {"role": "user", "content": build_user_message_content(user_text, context)},
    ]
