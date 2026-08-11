"""Public interpreter types and shared protocol constants."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


ALLOWED_ACTIONS = {
    "move",
    "look",
    "use",
    "take",
    "drop",
    "throw",
    "listen",
    "inventory",
    "help",
    "light",
    "turn_on_lights",
    "use_circuit_breaker",
    "refuse",
    "accept",
    "wait",
    "none",
}

DIEGETIC_REPLY_FALLBACK = (
    "The thought goes nowhere. You put your hands back to the work in front of you."
)
LOW_CONFIDENCE_THRESHOLD = 0.4
LOW_CONFIDENCE_REPLY = (
    "You begin, stop, and listen. Nothing nearby has changed."
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


@dataclass
class Intent:
    action: str
    args: Dict[str, str]
    confidence: float
    reply: Optional[str] = None
    effects: Optional[Dict[str, Any]] = None
    rationale: Optional[str] = None
