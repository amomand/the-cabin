"""Deterministic interpreter rules and context-bound target matching."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

from game.ai.types import Intent


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
    "grounds": "grounds",
    "outside": "grounds",
    "konttori": "north",
    "office": "north",
}


def offline_none_reply(user_text: str, context: Dict[str, Any]) -> str:
    """Give common free-form attempts a grounded offline consequence."""
    text = user_text.strip().lower()
    tokens = re.findall(r"[a-z]+(?:'[a-z]+)?", text)
    words = set(tokens)
    negated = bool(words & {"not", "never", "don't", "dont"})

    def begins(*phrases: Tuple[str, ...]) -> bool:
        return any(tuple(tokens[: len(phrase)]) == phrase for phrase in phrases)

    room_id = str(context.get("room_id", ""))
    flags = context.get("world_flags", {}) or {}
    wrong_cabin = room_id == "cabin_main" and flags.get("world_layer") == "wrong"

    if wrong_cabin and not negated:
        if begins(("sing",), ("hum",), ("whistle",)):
            return "You get as far as Nika's name. She waits. You let the tune die."
        if "coffee" in words and words & {"snow", "ice"}:
            return "Coffee steams between you. Snow has nothing to do with it."
        if begins(("dance",), ("spin",), ("waltz",)):
            return "You shift your weight. Your ribs stop you before the second step."
        if begins(("ask", "nika"), ("tell", "nika"), ("question", "nika")):
            return "You look at Nika across the mug. She raises one eyebrow, and the question stays in your mouth."
        if begins(("take", "nika"), ("grab", "nika"), ("pick", "up", "nika")):
            return "You put one hand on the table. Nika watches until you leave it there."
        if begins(("leave", "nika"), ("abandon", "nika")):
            return "You keep that behind your teeth with the mug between you."
        if begins(("leave",), ("abandon",)):
            return "You look past Nika to the door. She follows your eyes, and you stay in the chair."
        if begins(("get", "out")):
            return "Your palm presses the chair arm. Your ribs answer. You stay seated."

    if not negated and begins(("sing",), ("hum",), ("whistle",)):
        return "You sing one line. It comes back thin between the trunks."
    if not negated and begins(("fly",), ("float",), ("levitate",)):
        return "You look up. Branches cross above the track, too close for sky."
    if not negated and "coffee" in words and words & {"snow", "ice"}:
        return "You scoop up snow. It wets the glove, tastes of bark, and falls when you open your hand."

    if room_id in {"cabin_main", "konttori", "bedroom", "sauna"}:
        return "You try it. Nothing in the room changes."
    return "You try it. The trees stand where they stood."


def act_v_offer_active(context: Optional[Dict[str, Any]]) -> bool:
    """Read the runtime-computed dawn-offer truth from interpreter context."""
    return context is not None and context.get("is_dawn_offer_active") is True


def normalise_interaction_target(value: str) -> str:
    """Return a player-facing object phrase in the shape of room item names."""
    target = value.strip().lower()
    for prefix in ("the ", "a ", "an ", "my "):
        if target.startswith(prefix):
            target = target[len(prefix) :]
            break
    return target


def is_single_edit_apart(left: str, right: str) -> bool:
    """Return whether two explicit targets differ by one character edit."""
    if left == right or max(len(left), len(right)) < 4:
        return False
    if abs(len(left) - len(right)) > 1:
        return False
    if len(left) == len(right):
        return sum(a != b for a, b in zip(left, right)) == 1

    shorter, longer = (left, right) if len(left) < len(right) else (right, left)
    for index, (short_char, long_char) in enumerate(zip(shorter, longer)):
        if short_char != long_char:
            return shorter[index:] == longer[index + 1 :]
    return True


def unique_single_edit_match(
    target: str,
    candidates: Dict[str, str],
) -> Optional[str]:
    """Return the sole known candidate one edit from a normalized target."""
    matches = [
        canonical
        for lowered, canonical in candidates.items()
        if is_single_edit_apart(target, lowered)
    ]
    return matches[0] if len(matches) == 1 else None


def match_known_interaction_target(
    target: str,
    context: Optional[Dict[str, Any]],
    sources: Tuple[str, ...] = ("room_items", "inventory", "equipment"),
) -> Optional[str]:
    """Match a command target to an item in the given context sources."""
    if not context:
        return None

    normalised = normalise_interaction_target(target)
    known_items = [
        str(item)
        for source in sources
        for item in context.get(source, [])
    ]
    by_lower = {item.lower(): item for item in known_items}
    if normalised in by_lower:
        return by_lower[normalised]

    if normalised in {"camera", "battery", "camera battery", "casing", "live feed", "images", "pictures", "frames"} and "northern camera" in by_lower:
        return by_lower["northern camera"]
    if normalised in {"voicemail", "message", "phone message"} and "phone" in by_lower:
        return by_lower["phone"]
    if normalised in {"frames", "pictures", "saved frames"} and "camera feed" in by_lower:
        return by_lower["camera feed"]
    if normalised in {"coffee", "tea"} and "mug" in by_lower:
        return by_lower["mug"]

    return unique_single_edit_match(normalised, by_lower)


def match_known_exit(
    target: str,
    context: Optional[Dict[str, Any]],
) -> Optional[str]:
    """Match a movement target to a currently available exit or alias."""
    normalised = normalise_interaction_target(target)

    if context:
        exits = {
            str(exit_name).lower(): str(exit_name)
            for exit_name in context.get("exits", [])
        }
        if normalised in exits:
            return exits[normalised]
        typo_match = unique_single_edit_match(normalised, exits)
        if typo_match:
            return typo_match

    return DIRECTION_ALIASES.get(normalised)


def rule_based(
    user_text: str,
    context: Optional[Dict[str, Any]] = None,
) -> Optional[Intent]:
    """Interpret only commands deterministic enough to bypass model judgement."""
    t = user_text.strip().lower()
    if not t:
        return Intent("none", {}, 0.0, "empty")

    inventory_synonyms = {
        "inv",
        "inventory",
        "bag",
        "what am i carrying",
        "what things have i got",
        "what do i have",
        "check inventory",
        "show inventory",
        "what's in my bag",
        "what am i holding",
        "what do i own",
        "my stuff",
        "my things",
    }
    if t in inventory_synonyms:
        return Intent(
            "inventory",
            {},
            0.95,
            reply=None,
            effects=None,
            rationale="inventory synonym",
        )

    look_synonyms = {"look", "l", "examine", "inspect", "check", "see", "observe"}
    if t in look_synonyms:
        return Intent("look", {}, 0.9, reply=None, effects=None, rationale="look synonym")

    listen_synonyms = {"listen", "hear", "sound", "noise", "quiet"}
    if t in listen_synonyms:
        return Intent("listen", {}, 0.9, reply=None, effects=None, rationale="listen synonym")

    help_synonyms = {"help", "?", "what can i do", "commands", "hint"}
    if t in help_synonyms:
        return Intent("help", {}, 0.9, reply=None, effects=None, rationale="help synonym")

    tokens = t.split()

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
            room_items = [
                str(item).lower()
                for item in (context or {}).get("room_items", [])
            ]
            target = "mattress" if "mattress" in room_items else "bed"
        elif tokens[0] in {"drink", "sip"}:
            target = "mug"

        if tokens[0] in {"test", "repair", "fix", "replace", "compare"} and len(tokens) >= 2:
            camera_target = match_known_interaction_target(" ".join(tokens[1:]), context)
            if camera_target == "northern camera":
                target = camera_target
        if target:
            target = target.split(" with ", 1)[0]
            matched = match_known_interaction_target(target, context)
            if matched:
                return Intent(
                    "use",
                    {"item": matched},
                    0.95,
                    reply=None,
                    effects=None,
                    rationale="obvious fixture use",
                )

    wait_synonyms = {
        "wait",
        "sit",
        "sit down",
        "stay still",
        "keep still",
        "stay put",
        "sit and wait",
        "sit and listen",
        "do nothing",
        "hold still",
    }
    if t in wait_synonyms:
        return Intent("wait", {}, 0.95, reply=None, effects=None, rationale="wait synonym")

    if act_v_offer_active(context):
        t_dawn = " ".join(
            t.replace(",", " ").replace(".", " ").replace("!", " ").split()
        )
        refuse_synonyms = {
            "no",
            "no thank you",
            "no thanks",
            "decline",
            "refuse",
            "refuse the coffee",
            "refuse the mug",
            "don't drink",
            "do not drink",
            "put the mug down",
            "put mug down",
            "push the mug away",
            "push mug away",
            "say no",
            "say no thank you",
        }
        if t_dawn in refuse_synonyms:
            return Intent(
                "refuse",
                {},
                0.95,
                reply=None,
                effects=None,
                rationale="declined the coffee",
            )

        accept_synonyms = {
            "yes",
            "drink",
            "drink up",
            "drink the coffee",
            "drink coffee",
            "take the mug",
            "take mug",
            "take the coffee",
            "grab the mug",
            "pick up the mug",
            "accept",
            "stay",
        }
        if t_dawn in accept_synonyms:
            return Intent(
                "accept",
                {},
                0.95,
                reply=None,
                effects=None,
                rationale="drank the coffee",
            )

    if tokens:
        move_verbs = {
            "go",
            "head",
            "walk",
            "enter",
            "move",
            "step",
            "run",
            "crawl",
            "climb",
        }
        toward_preps = {
            "to",
            "towards",
            "toward",
            "into",
            "inside",
            "in",
            "through",
            "across",
        }

        if tokens[0] in move_verbs and len(tokens) >= 2:
            if len(tokens) >= 3 and tokens[1] in toward_preps:
                target = " ".join(tokens[2:])
                direction = match_known_exit(target, context)
                if direction:
                    return Intent(
                        "move",
                        {"direction": direction},
                        0.9,
                        reply=None,
                        effects=None,
                        rationale="move to target",
                    )
            elif len(tokens) >= 2:
                target = " ".join(tokens[1:])
                direction = match_known_exit(target, context)
                if direction:
                    return Intent(
                        "move",
                        {"direction": direction},
                        0.9,
                        reply=None,
                        effects=None,
                        rationale="direct move",
                    )

        direction = match_known_exit(t, context)
        if direction:
            return Intent(
                "move",
                {"direction": direction},
                0.8,
                reply=None,
                effects=None,
                rationale="bare dir",
            )

        take_synonyms = {
            "take",
            "pick",
            "grab",
            "snatch",
            "get",
            "collect",
            "acquire",
        }
        if tokens[0] in take_synonyms and len(tokens) >= 2:
            if tokens[0] == "pick" and len(tokens) >= 3 and tokens[1] == "up":
                item_name = " ".join(tokens[2:])
            else:
                item_name = " ".join(tokens[1:])
            if "carryable_room_items" not in (context or {}):
                return None
            matched = match_known_interaction_target(
                item_name,
                context,
                sources=("carryable_room_items",),
            )
            if matched:
                return Intent(
                    "take",
                    {"item": matched},
                    0.9,
                    reply=None,
                    effects=None,
                    rationale="take item",
                )
            return None

        throw_synonyms = {"throw", "toss", "hurl", "chuck", "fling", "pitch"}
        if tokens[0] in throw_synonyms and len(tokens) >= 2:
            remaining_words = tokens[1:]
            if "at" in remaining_words[1:]:
                index = remaining_words.index("at", 1)
                if index < len(remaining_words) - 1:
                    item_name = " ".join(remaining_words[:index])
                    target_name = " ".join(remaining_words[index + 1 :])
                    matched = match_known_interaction_target(
                        item_name,
                        context,
                        sources=("inventory",),
                    )
                    if matched:
                        return Intent(
                            "throw",
                            {"item": matched, "target": target_name},
                            0.9,
                            reply=None,
                            effects=None,
                            rationale="throw at target",
                        )
                    return None
            item_name = " ".join(remaining_words)
            matched = match_known_interaction_target(
                item_name,
                context,
                sources=("inventory",),
            )
            if matched:
                return Intent(
                    "throw",
                    {"item": matched},
                    0.9,
                    reply=None,
                    effects=None,
                    rationale="throw item",
                )
            return None

        drop_synonyms = {"drop", "leave", "discard", "abandon", "set"}
        if tokens[0] in drop_synonyms and len(tokens) >= 2:
            if tokens[0] == "set" and len(tokens) >= 3 and tokens[1] == "down":
                item_name = " ".join(tokens[2:])
            else:
                item_name = " ".join(tokens[1:])
            matched = match_known_interaction_target(
                item_name,
                context,
                sources=("inventory",),
            )
            if matched:
                return Intent(
                    "drop",
                    {"item": matched},
                    0.9,
                    reply=None,
                    effects=None,
                    rationale="drop item",
                )
            return None

    return None
