"""Round 4 model evaluation harness.

Evaluates candidate interpreter models against the production prompt path
(`build_interpreter_messages` / `build_openai_chat_params`) on scenarios whose
contexts are derived from the dev save seeds, so they cannot drift from real
game state.

Two scoring tiers:

- Mechanical (deterministic, local): JSON validity, action routing, effects,
  guardrails (meta words, Lyer-naming, length, exclamations).
- Quality (pairwise LLM judge): challenger reply vs incumbent reply on the
  same scenario/run, positions swapped, judged by one OpenAI and one
  Anthropic model. Reported as win-rate vs the incumbent.

Legacy keyword tone/interest scores are kept as reference columns so Round 4
numbers can be read against Round 3, but decisions weigh mechanical scores,
judge win-rates, and latency (TTFT + total, avg and P95).

Usage:
    python -m game.devtools.model_eval --all --runs 5          # decision run
    python -m game.devtools.model_eval --runs 1 --no-judge     # smoke test
    python -m game.devtools.model_eval --all --dry-run         # plan only
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from game.ai_context import build_ai_context
from game.ai_interpreter import (
    build_interpreter_messages,
    build_openai_chat_params,
    make_openai_params_compatible,
)


@dataclass(frozen=True)
class ModelSpec:
    provider: str
    model: str
    reasoning_effort: Optional[str] = None
    label: Optional[str] = None

    @property
    def display_name(self) -> str:
        if self.label:
            return self.label
        if self.reasoning_effort:
            return f"{self.model}:{self.reasoning_effort}"
        return self.model


@dataclass(frozen=True)
class EvalScenario:
    scenario_id: str
    user_input: str
    context: Dict[str, Any]
    expected_action: str
    expect_reply: bool = True
    expect_effect: bool = False
    forbid_words: Tuple[str, ...] = ()
    notes: str = ""

    @property
    def judge_eligible(self) -> bool:
        """Prose quality is judged only where the model's reply is the product."""
        return self.expected_action == "none" and self.expect_reply


@dataclass
class EvalResult:
    model: str
    provider: str
    reasoning_effort: Optional[str]
    scenario_id: str
    run_index: int
    user_input: str
    latency_ms: float
    ttft_ms: Optional[float]
    ok: bool
    raw_output: str
    parsed: Optional[Dict[str, Any]]
    scores: Dict[str, float]
    usage: Dict[str, int] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    attempts: int = 1

    @property
    def display_name(self) -> str:
        if self.reasoning_effort:
            return f"{self.model}:{self.reasoning_effort}"
        return self.model

    @property
    def reply_text(self) -> str:
        if not self.parsed:
            return ""
        return str(self.parsed.get("reply") or "").strip()


@dataclass
class JudgeVerdict:
    judge: str
    scenario_id: str
    run_index: int
    challenger: str
    incumbent: str
    challenger_position: str  # "A" or "B"
    winner: str  # "challenger" | "incumbent" | "tie" | "error"
    reason: str


INCUMBENT_LABEL = "gpt-5.4-mini:none"

DEFAULT_MODEL_SPECS = [
    ModelSpec(provider="openai", model="gpt-5.4-mini", reasoning_effort="none"),
    ModelSpec(provider="openai", model="gpt-5.6-terra", reasoning_effort="none"),
]


# Round 4 slate used by `--all`. gpt-5.4-nano dropped (dominated by mini in
# Round 3); gpt-5.5 kept as the prior challenger reference point.
ALL_MODEL_SPECS = [
    # OpenAI
    ModelSpec(provider="openai", model="gpt-5.4-mini", reasoning_effort="none"),
    ModelSpec(provider="openai", model="gpt-5.5", reasoning_effort="none"),
    ModelSpec(provider="openai", model="gpt-5.6-luna", reasoning_effort="none"),
    ModelSpec(provider="openai", model="gpt-5.6-luna", reasoning_effort="low"),
    ModelSpec(provider="openai", model="gpt-5.6-terra", reasoning_effort="none"),
    ModelSpec(provider="openai", model="gpt-5.6-terra", reasoning_effort="low"),
    ModelSpec(provider="openai", model="gpt-5.6-sol", reasoning_effort="none"),
    # Anthropic
    ModelSpec(provider="anthropic", model="claude-haiku-4-5-20251001"),
    ModelSpec(provider="anthropic", model="claude-sonnet-5"),
    ModelSpec(provider="anthropic", model="claude-opus-4-8"),
    ModelSpec(provider="anthropic", model="claude-fable-5"),
]


DEFAULT_JUDGE_SPECS = [
    ModelSpec(provider="openai", model="gpt-5.5", reasoning_effort="none", label="judge:gpt-5.5"),
    ModelSpec(provider="anthropic", model="claude-sonnet-5", label="judge:claude-sonnet-5"),
]


def _base_context(**overrides: Any) -> Dict[str, Any]:
    """Hand-authored context used by the legacy Round 3 scenarios."""
    context = {
        "room_name": "Wilderness",
        "exits": ["north"],
        "room_items": ["stick", "stone"],
        "room_wildlife": ["snowy owl"],
        "inventory": [],
        "world_flags": {"has_power": False, "fire_lit": False},
        "allowed_actions": [
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
            "none",
        ],
        "fear": 18,
        "health": 96,
        "rooms_visited": 1,
        "been_here_before": False,
        "active_quest": None,
    }
    context.update(overrides)
    return context


def _seed_context(
    seed_name: str,
    *,
    room_id: Optional[str] = None,
    fear: Optional[int] = None,
    health: Optional[int] = None,
) -> Dict[str, Any]:
    """Build an interpreter context from a dev save seed — real game state."""
    from game.devtools import seed_saves

    state = seed_saves.SEEDS[seed_name]()
    if room_id is not None:
        # Switch first, then record the visit — a typo'd room_id must fail
        # loudly, not silently build a context for the seed's default room
        # while inflating rooms_visited.
        if not state.map._set_current_room_by_id(room_id, been_here_before=True):
            raise ValueError(f"Unknown room_id {room_id!r} for seed {seed_name!r}")
        state.map.visited_rooms.add(room_id)
    if fear is not None:
        state.player.fear = fear
    if health is not None:
        state.player.health = health
    return build_ai_context(state.player, state.map, state.quest_manager)


# Round 3 scenarios, unchanged, for cross-round comparability.
LEGACY_SCENARIOS = [
    EvalScenario(
        scenario_id="impossible_backflip",
        user_input="do a backflip into the dark",
        context=_base_context(fear=55, health=82),
        expected_action="none",
        expect_effect=True,
        notes="Impossible creative action should fail in-world, not become look/move.",
    ),
    EvalScenario(
        scenario_id="quiet_defiance",
        user_input="I tell the trees I am not afraid",
        context=_base_context(fear=72, health=88, room_wildlife=[]),
        expected_action="none",
        expect_effect=True,
        notes="Roleplay input should stay diegetic and Lyer-adjacent without exposition.",
    ),
    EvalScenario(
        scenario_id="look_at_sky",
        user_input="look at the sky",
        context=_base_context(room_name="The Clearing", exits=["south", "cabin"], rooms_visited=2),
        expected_action="look",
        notes="Explicit examine command should classify as look and ideally provide usable prose.",
    ),
    EvalScenario(
        scenario_id="invalid_exit",
        user_input="go east",
        context=_base_context(exits=["north"], room_items=[]),
        expected_action="none",
        notes="Model should not invent an unavailable direction.",
    ),
    EvalScenario(
        scenario_id="take_visible_stone",
        user_input="pick up the stone",
        context=_base_context(room_items=["stick", "stone"], inventory=[]),
        expected_action="take",
        expect_reply=False,
        notes="Simple grounded action should classify cleanly.",
    ),
    EvalScenario(
        scenario_id="eat_key",
        user_input="eat the key",
        context=_base_context(
            room_name="The Cabin",
            exits=["out", "north", "grounds"],
            room_items=["matches", "key", "light switch", "fireplace"],
            inventory=["key"],
            room_wildlife=[],
            fear=38,
        ),
        expected_action="none",
        expect_effect=True,
        notes="Absurd but physical input should get a grounded denial with consequences.",
    ),
    EvalScenario(
        scenario_id="listen_wolf",
        user_input="listen",
        context=_base_context(room_wildlife=["wolf"], fear=64, rooms_visited=4),
        expected_action="listen",
        notes="Standard command should use present wildlife and keep tension.",
    ),
    EvalScenario(
        scenario_id="light_fireplace_no_fuel",
        user_input="light the fireplace",
        context=_base_context(
            room_name="The Cabin",
            exits=["out", "north", "grounds"],
            room_items=["matches", "light switch", "fireplace"],
            inventory=["matches"],
            room_wildlife=[],
            active_quest="Find fuel and restore warmth to the cabin",
        ),
        expected_action="light",
        notes="Quest context should subtly shape output without inventing firewood.",
    ),
    EvalScenario(
        scenario_id="returning_room_memory",
        user_input="touch the wall and remember",
        context=_base_context(
            room_name="The Cabin",
            exits=["out", "north", "grounds"],
            room_items=["matches", "key", "light switch", "fireplace"],
            room_wildlife=[],
            inventory=["matches"],
            fear=47,
            rooms_visited=6,
            been_here_before=True,
        ),
        expected_action="none",
        notes="Returning-room context should avoid first-discovery language.",
    ),
    EvalScenario(
        scenario_id="panic_low_health",
        user_input="crawl under the table and hold my breath",
        context=_base_context(
            room_name="Konttori",
            exits=["south", "north"],
            room_items=["circuit breaker"],
            room_wildlife=[],
            fear=88,
            health=31,
            rooms_visited=7,
            been_here_before=True,
        ),
        expected_action="none",
        expect_effect=True,
        notes="Critical player state should make prose frayed without bloating.",
    ),
]


def _build_story_scenarios() -> List[EvalScenario]:
    """Act III–V scenarios with contexts derived from dev save seeds."""
    act5_live = _seed_context("act4_recognition", room_id="cabin_clearing", fear=74)
    return [
        # Act V threshold routing — the newest interpreter rules.
        EvalScenario(
            scenario_id="act5_accept_door",
            user_input="close the door",
            context=act5_live,
            expected_action="accept",
            expect_reply=False,
            notes="Physical threshold action while the Act V offer is live must route to accept.",
        ),
        EvalScenario(
            scenario_id="act5_refuse_turn",
            user_input="turn away from the door and walk",
            context=act5_live,
            expected_action="refuse",
            expect_reply=False,
            notes="Turning away while the Act V offer is live must route to refuse.",
        ),
        EvalScenario(
            scenario_id="act5_abstract_assent",
            user_input="yes, I want to stay",
            context=act5_live,
            expected_action="none",
            notes="Abstract assent must stay 'none' even with the offer live; only physical threshold acts route.",
        ),
        EvalScenario(
            scenario_id="act5_threshold_inactive",
            user_input="close the door",
            context=_seed_context("act3_seated", fear=42),
            expected_action="none",
            notes="Threshold input with the offer inactive must not route to accept/refuse.",
        ),
        # Wrong-layer prose quality.
        EvalScenario(
            scenario_id="wrong_layer_heartbeats",
            user_input="stand very still and count my heartbeats",
            context=_seed_context("act3_seated", fear=48),
            expected_action="none",
            notes="Wrong-layer stillness should read as wrongness held at arm's length, not cosy reunion.",
        ),
        EvalScenario(
            scenario_id="wrong_layer_phantom_dog",
            user_input="call out to the dog",
            context=_seed_context("act3_seated", fear=44),
            expected_action="none",
            notes="No dog exists; nothing lives in the wrong layer. Reply must not confirm one.",
        ),
        # Canon-safety baiting.
        EvalScenario(
            scenario_id="lyer_bait_shout",
            user_input="shout 'I know what you are' at the trees",
            context=_seed_context("act4_recognition", fear=66),
            expected_action="none",
            expect_effect=True,
            forbid_words=("lyer",),
            notes="Defiance at the entity: reply must imply presence without naming or explaining it.",
        ),
        EvalScenario(
            scenario_id="meta_bait_hint",
            user_input="I'm stuck. give me a hint, what am I supposed to do next?",
            context=_seed_context("act2_mid", fear=30),
            expected_action="none",
            notes="Meta plea must get a diegetic answer — no mechanics, no objectives, no 4th wall.",
        ),
        # Frayed-state prose.
        EvalScenario(
            scenario_id="near_death_retreat",
            user_input="back slowly away from the table",
            context=_seed_context("near_death_fear"),
            expected_action="none",
            notes="Fear 98 in the wrong layer: prose should fray without tipping into melodrama.",
        ),
    ]


STORY_SCENARIOS = _build_story_scenarios()
DEFAULT_SCENARIOS = LEGACY_SCENARIOS + STORY_SCENARIOS


DARK_WORDS = {
    "cold",
    "dark",
    "quiet",
    "silence",
    "snow",
    "shadow",
    "trees",
    "breath",
    "still",
    "wrong",
    "watching",
    "bites",
    "near",
}
SENSORY_WORDS = {
    "cold",
    "snow",
    "breath",
    "teeth",
    "skin",
    "wood",
    "smoke",
    "sound",
    "quiet",
    "dark",
    "light",
    "air",
}
CONSEQUENCE_WORDS = {
    "pain",
    "cost",
    "fear",
    "stop",
    "stops",
    "cannot",
    "can't",
    "won't",
    "nothing",
    "falls",
    "protest",
    "bites",
    "tightens",
}
META_WORDS = {"ai", "model", "json", "command", "player", "game", "invalid", "cannot do that"}
GENERIC_PHRASES = {
    "you start, then think better of it",
    "you can't do that",
    "nothing happens",
    "invalid command",
    "as an ai",
}


SUPPORTED_PROVIDERS = ("openai", "anthropic")


def _default_reasoning_effort(provider: str, model: str, given: Optional[str]) -> Optional[str]:
    """Default OpenAI gpt-5* specs to reasoning_effort="none" when omitted.

    Keeps CLI shorthand consistent with the incumbent and the production
    default: `--models gpt-5.4-mini` becomes `gpt-5.4-mini:none`, so its
    display_name matches `--incumbent` (else judging silently skips it) and
    OpenAI isn't left to pick a non-"none" reasoning mode.
    """
    if given is not None:
        return given
    if provider == "openai" and model.startswith("gpt-5"):
        return "none"
    return None


def parse_model_spec(raw: str) -> ModelSpec:
    """Parse provider/model specs like openai:gpt-5.6-terra:low or gpt-5.4-mini."""
    parts = [part.strip() for part in raw.split(":") if part.strip()]
    if len(parts) == 1:
        return ModelSpec(
            provider="openai",
            model=parts[0],
            reasoning_effort=_default_reasoning_effort("openai", parts[0], None),
        )
    if len(parts) == 2:
        if parts[0] in SUPPORTED_PROVIDERS:
            return ModelSpec(
                provider=parts[0],
                model=parts[1],
                reasoning_effort=_default_reasoning_effort(parts[0], parts[1], None),
            )
        return ModelSpec(provider="openai", model=parts[0], reasoning_effort=parts[1])
    if len(parts) == 3:
        provider = parts[0]
        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unsupported provider {provider!r} in spec {raw!r}; "
                f"supported: {', '.join(SUPPORTED_PROVIDERS)}"
            )
        return ModelSpec(provider=provider, model=parts[1], reasoning_effort=parts[2])
    raise ValueError(f"Invalid model spec: {raw}")


def parse_model_specs(values: Optional[Sequence[str]]) -> List[ModelSpec]:
    if not values:
        return list(DEFAULT_MODEL_SPECS)

    specs: List[ModelSpec] = []
    for value in values:
        for raw in value.split(","):
            raw = raw.strip()
            if raw:
                specs.append(parse_model_spec(raw))
    return specs


_WORD_RE = re.compile(r"[a-z0-9']+")


def _word_tokens(text_lower: str) -> set:
    """Whole-word tokens of an already-lowercased string."""
    return set(_WORD_RE.findall(text_lower))


def _contains_meta(reply_words: set, reply_lower: str) -> bool:
    """True if the reply breaks the fourth wall.

    Single tokens (ai, model, game...) match whole words; multi-word markers
    (cannot do that) match as substrings, since they can't false-positive.
    """
    for marker in META_WORDS:
        if " " in marker:
            if marker in reply_lower:
                return True
        elif marker in reply_words:
            return True
    return False


def _forbidden(word: str, reply_words: set, reply_lower: str) -> bool:
    marker = word.lower()
    return marker in reply_lower if " " in marker else marker in reply_words


def score_response(parsed: Optional[Dict[str, Any]], raw_output: str, scenario: EvalScenario) -> Dict[str, float]:
    if parsed is None:
        return {
            "json_valid": 0.0,
            "action_match": 0.0,
            "reply_present": 0.0,
            "effects_present": 0.0,
            "guardrail": 0.0,
            "mech": 0.0,
            "tone": 0.0,
            "interesting": 0.0,
            "overall": 0.0,
        }

    reply = parsed.get("reply")
    reply_text = str(reply or "").strip()
    reply_lower = reply_text.lower()
    effects = parsed.get("effects") if isinstance(parsed.get("effects"), dict) else {}
    try:
        fear_effect = int(effects.get("fear", 0) or 0)
        health_effect = int(effects.get("health", 0) or 0)
    except (TypeError, ValueError):
        fear_effect = 0
        health_effect = 0

    json_valid = 1.0
    action_match = 1.0 if parsed.get("action") == scenario.expected_action else 0.0
    reply_present = 1.0 if (not scenario.expect_reply or reply_text) else 0.0
    effects_present = 1.0
    if scenario.expect_effect:
        effects_present = 1.0 if fear_effect != 0 or health_effect != 0 else 0.0

    reply_words = _word_tokens(reply_lower)

    second_person = 1.0 if "you" in reply_words else 0.0
    dark_signal = min(1.0, sum(1 for word in DARK_WORDS if word in reply_words) / 2)
    # Penalty checks match whole words: substring matching would trip "ai" on
    # "afraid"/"pain"/"air" and unfairly zero the score on ordinary prose.
    no_meta = 0.0 if _contains_meta(reply_words, reply_lower) else 1.0
    terse = 1.0 if len(reply_text) <= 200 else max(0.0, 1 - ((len(reply_text) - 200) / 200))
    no_exclaim = 0.0 if "!" in reply_text else 1.0
    no_generic = 0.0 if any(phrase in reply_lower for phrase in GENERIC_PHRASES) else 1.0
    tone = statistics.mean([second_person, dark_signal, no_meta, terse, no_exclaim, no_generic])

    sensory = min(1.0, sum(1 for word in SENSORY_WORDS if word in reply_words) / 2)
    consequence = min(1.0, sum(1 for word in CONSEQUENCE_WORDS if word in reply_words) / 1)
    specificity = min(1.0, len(reply_words) / 18)
    interesting = statistics.mean([sensory, consequence, specificity, no_generic])

    # Hard guardrails. Lyer-naming is a canon breach on any player-facing
    # surface, so it is checked on every scenario, not just the baits.
    # Whole-word match so "flyer" doesn't read as the proper noun "Lyer".
    lyer_ok = 0.0 if "lyer" in reply_words else 1.0
    forbid_ok = 0.0 if any(_forbidden(word, reply_words, reply_lower) for word in scenario.forbid_words) else 1.0
    effects_bounded = 1.0 if (-2 <= fear_effect <= 2 and -2 <= health_effect <= 2) else 0.0
    guardrail = statistics.mean([no_meta, no_generic, no_exclaim, terse, lyer_ok, forbid_ok, effects_bounded])

    # Deterministic mechanical score. Prose quality lives with the judges.
    mech = statistics.mean([json_valid, action_match, reply_present, effects_present, guardrail])

    # Legacy Round 3 composite, unchanged for cross-round comparability.
    overall = (
        (json_valid * 0.15)
        + (action_match * 0.20)
        + (reply_present * 0.10)
        + (effects_present * 0.10)
        + (tone * 0.25)
        + (interesting * 0.20)
    )

    return {
        "json_valid": round(json_valid, 4),
        "action_match": round(action_match, 4),
        "reply_present": round(reply_present, 4),
        "effects_present": round(effects_present, 4),
        "guardrail": round(guardrail, 4),
        "mech": round(mech, 4),
        "tone": round(tone, 4),
        "interesting": round(interesting, 4),
        "overall": round(overall, 4),
    }


def _strip_code_fences(text: str) -> str:
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    return text


# Clients are cached per thread. Each model runs its calls serially on one
# thread (see _run_spec), so a per-thread client keeps HTTP connections alive
# across that model's requests — measured latency then reflects the API, not a
# fresh TLS handshake per call — without sharing a pool across model threads.
_thread_clients = threading.local()


def _openai_client():
    client = getattr(_thread_clients, "openai", None)
    if client is None:
        from openai import OpenAI  # type: ignore

        client = OpenAI()
        _thread_clients.openai = client
    return client


def _anthropic_client():
    client = getattr(_thread_clients, "anthropic", None)
    if client is None:
        from anthropic import Anthropic  # type: ignore

        client = Anthropic()
        _thread_clients.anthropic = client
    return client


def split_system_for_cache(system_text: str) -> List[Dict[str, Any]]:
    """Split the system prompt into a static prefix + dynamic tail.

    Everything before the Constraints block is identical across scenarios and
    turns, so the prefix is tagged with Anthropic's `cache_control` (type
    `ephemeral` is the API's name for its ~5-minute prompt cache, not a signal
    that the block is disposable). Whether the cache actually engages (minimum
    token thresholds apply) is reported via usage cache_read_input_tokens, not
    assumed.
    """
    marker = "Constraints:"
    index = system_text.find(marker)
    if index <= 0:
        return [{"type": "text", "text": system_text}]
    return [
        {
            "type": "text",
            "text": system_text[:index],
            "cache_control": {"type": "ephemeral"},
        },
        {"type": "text", "text": system_text[index:]},
    ]


def call_openai(spec: ModelSpec, messages: List[Dict[str, str]], timeout: float) -> Dict[str, Any]:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required to run model evaluations")

    client = _openai_client()
    reasoning_effort = spec.reasoning_effort if spec.reasoning_effort != "none" else None
    params = build_openai_chat_params(
        spec.model,
        messages,
        stream=True,
        reasoning_effort=reasoning_effort,
    )
    if spec.reasoning_effort == "none" and spec.model.startswith("gpt-5"):
        params["reasoning_effort"] = "none"
    if reasoning_effort and spec.model.startswith("gpt-5"):
        # Reasoning tokens count against the completion budget; production's
        # 800 would risk truncated JSON at any real effort setting. Gated on
        # gpt-5*: non-gpt-5 specs use max_tokens, and adding
        # max_completion_tokens alongside it is an OpenAI validation error.
        params["max_completion_tokens"] = 2000
    params["timeout"] = timeout
    params["stream_options"] = {"include_usage": True}
    params = make_openai_params_compatible(client.chat.completions.create, params)

    started = time.perf_counter()
    stream = client.chat.completions.create(**params)
    chunks: List[str] = []
    ttft_ms: Optional[float] = None
    usage: Dict[str, int] = {}
    for chunk in stream:
        if getattr(chunk, "usage", None):
            usage = {
                "input_tokens": chunk.usage.prompt_tokens,
                "output_tokens": chunk.usage.completion_tokens,
            }
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta.content:
            if ttft_ms is None:
                ttft_ms = (time.perf_counter() - started) * 1000
            chunks.append(delta.content)
    return {
        "text": "".join(chunks).strip(),
        "ttft_ms": ttft_ms,
        "usage": usage,
    }


def call_anthropic(spec: ModelSpec, messages: List[Dict[str, str]], timeout: float) -> Dict[str, Any]:
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is required for Anthropic specs")

    client = _anthropic_client()
    system = next(m["content"] for m in messages if m["role"] == "system")
    user = next(m["content"] for m in messages if m["role"] == "user")

    started = time.perf_counter()
    chunks: List[str] = []
    ttft_ms: Optional[float] = None
    with client.messages.stream(
        model=spec.model,
        max_tokens=1024,
        system=split_system_for_cache(system),
        messages=[{"role": "user", "content": user}],
        timeout=timeout,
    ) as stream:
        for text in stream.text_stream:
            if ttft_ms is None and text:
                ttft_ms = (time.perf_counter() - started) * 1000
            chunks.append(text)
        final = stream.get_final_message()

    usage = {
        "input_tokens": final.usage.input_tokens,
        "output_tokens": final.usage.output_tokens,
        "cache_read_input_tokens": getattr(final.usage, "cache_read_input_tokens", 0) or 0,
        "cache_creation_input_tokens": getattr(final.usage, "cache_creation_input_tokens", 0) or 0,
    }
    return {
        "text": _strip_code_fences("".join(chunks).strip()),
        "ttft_ms": ttft_ms,
        "usage": usage,
    }


def call_model(spec: ModelSpec, messages: List[Dict[str, str]], timeout: float) -> Dict[str, Any]:
    if spec.provider == "openai":
        return call_openai(spec, messages, timeout)
    if spec.provider == "anthropic":
        return call_anthropic(spec, messages, timeout)
    raise NotImplementedError(f"Provider is not implemented: {spec.provider}")


def _provider_skip_reason(spec: ModelSpec) -> Optional[str]:
    """Return a reason to skip this spec, or None if it can run."""
    if spec.provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        return "OPENAI_API_KEY not set"
    if spec.provider == "anthropic":
        if not os.getenv("ANTHROPIC_API_KEY"):
            return "ANTHROPIC_API_KEY not set"
        try:
            import anthropic  # type: ignore  # noqa: F401
        except ImportError:
            return "anthropic SDK not installed (pip install anthropic)"
    return None


MAX_TRANSPORT_ATTEMPTS = 4


def run_one(spec: ModelSpec, scenario: EvalScenario, run_index: int, timeout: float) -> EvalResult:
    """One scored call. Transport failures retry with backoff (the gpt-5.6
    family intermittently 401s); malformed model output does not — that is a
    quality signal, not transport noise. Latency is per successful attempt.
    """
    messages = build_interpreter_messages(scenario.user_input, scenario.context)
    raw_output = ""
    ttft_ms: Optional[float] = None
    usage: Dict[str, int] = {}
    parsed: Optional[Dict[str, Any]] = None
    errors: List[str] = []
    latency_ms = 0.0
    attempts = 0

    for attempt in range(1, MAX_TRANSPORT_ATTEMPTS + 1):
        attempts = attempt
        started = time.perf_counter()
        try:
            outcome = call_model(spec, messages, timeout)
        except Exception as exc:
            latency_ms = (time.perf_counter() - started) * 1000
            errors.append(repr(exc))
            if attempt < MAX_TRANSPORT_ATTEMPTS:
                time.sleep(min(2.0, 0.5 * (2 ** (attempt - 1))))
            continue
        latency_ms = (time.perf_counter() - started) * 1000
        errors = []
        raw_output = outcome["text"]
        ttft_ms = outcome["ttft_ms"]
        usage = outcome["usage"]
        try:
            parsed = json.loads(raw_output)
        except Exception as exc:
            errors.append(repr(exc))
        break

    scores = score_response(parsed, raw_output, scenario)

    return EvalResult(
        model=spec.model,
        provider=spec.provider,
        reasoning_effort=spec.reasoning_effort,
        scenario_id=scenario.scenario_id,
        run_index=run_index,
        user_input=scenario.user_input,
        latency_ms=round(latency_ms, 2),
        ttft_ms=round(ttft_ms, 2) if ttft_ms is not None else None,
        ok=not errors and parsed is not None,
        raw_output=raw_output,
        parsed=parsed,
        scores=scores,
        usage=usage,
        errors=errors,
        attempts=attempts,
    )


# ---------------------------------------------------------------------------
# Pairwise judging


_JUDGE_SYSTEM_PROMPT = (
    "You judge candidate narrations for a survival-horror text adventure set in a "
    "cold Finnish wilderness. The player typed something; each candidate is the "
    "game's in-world response.\n\n"
    "Rubric — the better reply:\n"
    "- Second person, present tense. Terse: 1-3 short sentences that land.\n"
    "- Sensory and specific. Cold, sound, breath, texture — not abstract mood words.\n"
    "- Sustains creeping dread. Understatement over melodrama. No exclamation marks.\n"
    "- Stays in-world. Never meta, never explains mechanics, never names or explains "
    "the presence in the woods. Implication only.\n"
    "- Impossible actions get grounded physical failure with a felt cost.\n"
    "- Matches the player's fear/health state: calm when low, frayed when critical.\n"
    "- Fresh phrasing. Stock horror lines ('a chill runs down your spine') lose.\n"
    "- Never confirms things that are not in the world (items, animals, exits).\n\n"
    "Compare reply_A and reply_B for the given situation. Small differences matter; "
    "prefer a genuine winner, use 'tie' only when truly equivalent.\n"
    'Output ONLY JSON: {"winner": "A" | "B" | "tie", "reason": "<one short sentence>"}'
)


def build_judge_messages(
    scenario: EvalScenario,
    reply_a: str,
    reply_b: str,
) -> List[Dict[str, str]]:
    context = scenario.context
    world_flags = context.get("world_flags", {})
    payload = {
        "player_input": scenario.user_input,
        "situation": {
            "room": context.get("room_name"),
            "world_layer": world_flags.get("world_layer", "real"),
            "fear": context.get("fear"),
            "health": context.get("health"),
            "scenario_intent": scenario.notes,
        },
        "reply_A": reply_a,
        "reply_B": reply_b,
    }
    return [
        {"role": "system", "content": _JUDGE_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]


def _judge_call(judge: ModelSpec, messages: List[Dict[str, str]], timeout: float) -> Dict[str, Any]:
    if judge.provider == "openai":
        client = _openai_client()
        params: Dict[str, Any] = {
            "model": judge.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "timeout": timeout,
        }
        if judge.model.startswith("gpt-5"):
            params["max_completion_tokens"] = 400
            if judge.reasoning_effort:
                params["reasoning_effort"] = judge.reasoning_effort
        else:
            params["temperature"] = 0
            params["max_tokens"] = 400
        params = make_openai_params_compatible(client.chat.completions.create, params)
        response = client.chat.completions.create(**params)
        text = (response.choices[0].message.content or "").strip()
    elif judge.provider == "anthropic":
        client = _anthropic_client()
        system = next(m["content"] for m in messages if m["role"] == "system")
        user = next(m["content"] for m in messages if m["role"] == "user")
        response = client.messages.create(
            model=judge.model,
            max_tokens=400,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
            timeout=timeout,
        )
        text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        ).strip()
    else:
        raise NotImplementedError(f"Judge provider not implemented: {judge.provider}")

    return json.loads(_strip_code_fences(text))


def hash_stable(text: str) -> int:
    """Stable across processes (unlike built-in hash with PYTHONHASHSEED)."""
    value = 0
    for char in text:
        value = (value * 31 + ord(char)) % 1_000_003
    return value


def challenger_position(scenario_id: str, run_index: int) -> str:
    """Deterministic position swap so neither side always sits in slot A."""
    return "A" if (hash_stable(scenario_id) + run_index) % 2 == 0 else "B"


def judge_pair(
    judge: ModelSpec,
    scenario: EvalScenario,
    challenger_result: EvalResult,
    incumbent_result: EvalResult,
    timeout: float,
) -> JudgeVerdict:
    position = challenger_position(scenario.scenario_id, challenger_result.run_index)
    if position == "A":
        reply_a, reply_b = challenger_result.reply_text, incumbent_result.reply_text
    else:
        reply_a, reply_b = incumbent_result.reply_text, challenger_result.reply_text

    winner = "error"
    reason = ""
    try:
        verdict = _judge_call(judge, build_judge_messages(scenario, reply_a, reply_b), timeout)
        raw_winner = str(verdict.get("winner", "")).strip().upper()
        reason = str(verdict.get("reason", "")).strip()
        if raw_winner == "TIE":
            winner = "tie"
        elif raw_winner in {"A", "B"}:
            winner = "challenger" if raw_winner == position else "incumbent"
    except Exception as exc:
        reason = repr(exc)

    return JudgeVerdict(
        judge=judge.display_name,
        scenario_id=scenario.scenario_id,
        run_index=challenger_result.run_index,
        challenger=challenger_result.display_name,
        incumbent=incumbent_result.display_name,
        challenger_position=position,
        winner=winner,
        reason=reason,
    )


def run_judging(
    results: Sequence[EvalResult],
    scenarios: Sequence[EvalScenario],
    judges: Sequence[ModelSpec],
    *,
    incumbent_label: str,
    judge_runs: int,
    timeout: float,
    concurrency: int = 8,
) -> List[JudgeVerdict]:
    scenario_lookup = {scenario.scenario_id: scenario for scenario in scenarios}
    incumbent_results = {
        (r.scenario_id, r.run_index): r
        for r in results
        if r.display_name == incumbent_label and r.ok and r.reply_text
    }
    if not incumbent_results:
        print(f"[model-eval] judging skipped — no usable incumbent results for {incumbent_label}", flush=True)
        return []

    active_judges = []
    for judge in judges:
        skip = _provider_skip_reason(judge)
        if skip:
            print(f"[model-eval] judge SKIP {judge.display_name} — {skip}", flush=True)
        else:
            active_judges.append(judge)

    pairs: List[Tuple[ModelSpec, EvalScenario, EvalResult, EvalResult]] = []
    for result in results:
        if result.display_name == incumbent_label or not result.ok or not result.reply_text:
            continue
        if result.run_index > judge_runs:
            continue
        scenario = scenario_lookup.get(result.scenario_id)
        if scenario is None or not scenario.judge_eligible:
            continue
        incumbent_result = incumbent_results.get((result.scenario_id, result.run_index))
        if incumbent_result is None:
            continue
        for judge in active_judges:
            pairs.append((judge, scenario, result, incumbent_result))

    if not pairs:
        return []

    print(f"[model-eval] judging {len(pairs)} pairs with {len(active_judges)} judge(s)", flush=True)
    verdicts: List[JudgeVerdict] = []
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [
            pool.submit(judge_pair, judge, scenario, challenger, incumbent, timeout)
            for judge, scenario, challenger, incumbent in pairs
        ]
        for future in futures:
            verdicts.append(future.result())
    return verdicts


def summarize_judging(verdicts: Sequence[JudgeVerdict]) -> Dict[str, Dict[str, Any]]:
    """Per-challenger judge win-rates vs the incumbent, per judge and combined."""
    by_challenger: Dict[str, Dict[str, Any]] = {}
    for verdict in verdicts:
        if verdict.winner == "error":
            continue
        row = by_challenger.setdefault(
            verdict.challenger,
            {"judges": {}, "wins": 0, "ties": 0, "losses": 0},
        )
        judge_row = row["judges"].setdefault(verdict.judge, {"wins": 0, "ties": 0, "losses": 0})
        key = {"challenger": "wins", "tie": "ties", "incumbent": "losses"}[verdict.winner]
        row[key] += 1
        judge_row[key] += 1

    for row in by_challenger.values():
        total = row["wins"] + row["ties"] + row["losses"]
        row["win_rate"] = round((row["wins"] + 0.5 * row["ties"]) / total, 4) if total else None
        for judge_row in row["judges"].values():
            judge_total = judge_row["wins"] + judge_row["ties"] + judge_row["losses"]
            judge_row["win_rate"] = (
                round((judge_row["wins"] + 0.5 * judge_row["ties"]) / judge_total, 4)
                if judge_total
                else None
            )
    return by_challenger


def judge_agreement(verdicts: Sequence[JudgeVerdict]) -> Optional[float]:
    """Fraction of (scenario, run, challenger) pairs where both judges agree."""
    by_pair: Dict[Tuple[str, int, str], Dict[str, str]] = {}
    for verdict in verdicts:
        if verdict.winner == "error":
            continue
        by_pair.setdefault(
            (verdict.scenario_id, verdict.run_index, verdict.challenger), {}
        )[verdict.judge] = verdict.winner

    comparable = [outcomes for outcomes in by_pair.values() if len(outcomes) >= 2]
    if not comparable:
        return None
    agreements = sum(1 for outcomes in comparable if len(set(outcomes.values())) == 1)
    return round(agreements / len(comparable), 4)


# ---------------------------------------------------------------------------
# Aggregation and output


def summarize(results: Sequence[EvalResult]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[EvalResult]] = {}
    for result in results:
        grouped.setdefault(result.display_name, []).append(result)

    rows: List[Dict[str, Any]] = []
    for label, items in grouped.items():
        latencies = [item.latency_ms for item in items if item.ok]
        ttfts = [item.ttft_ms for item in items if item.ok and item.ttft_ms is not None]
        overalls = [item.scores.get("overall", 0.0) for item in items]
        input_tokens = [item.usage.get("input_tokens") for item in items if item.usage.get("input_tokens")]
        output_tokens = [item.usage.get("output_tokens") for item in items if item.usage.get("output_tokens")]
        cache_reads = [item.usage.get("cache_read_input_tokens", 0) for item in items]
        rows.append(
            {
                "model": label,
                "provider": items[0].provider,
                "runs": len(items),
                "ok_rate": round(sum(1 for item in items if item.ok) / len(items), 4),
                "avg_ttft_ms": round(statistics.mean(ttfts), 2) if ttfts else None,
                "avg_latency_ms": round(statistics.mean(latencies), 2) if latencies else None,
                "p95_latency_ms": round(_percentile(latencies, 95), 2) if latencies else None,
                "avg_mech": _avg_score(items, "mech"),
                "avg_guardrail": _avg_score(items, "guardrail"),
                "avg_overall": _avg_score(items, "overall"),
                "stdev_overall": round(statistics.stdev(overalls), 4) if len(overalls) > 1 else 0.0,
                "avg_tone": _avg_score(items, "tone"),
                "avg_interesting": _avg_score(items, "interesting"),
                "action_match_rate": _avg_score(items, "action_match"),
                "effects_present_rate": _avg_score(items, "effects_present"),
                "retry_rate": round(sum(1 for item in items if item.attempts > 1) / len(items), 4),
                "avg_input_tokens": round(statistics.mean(input_tokens)) if input_tokens else None,
                "avg_output_tokens": round(statistics.mean(output_tokens)) if output_tokens else None,
                "cache_hit_rate": (
                    round(sum(1 for c in cache_reads if c) / len(cache_reads), 4) if cache_reads else 0.0
                ),
            }
        )
    return sorted(rows, key=lambda row: (-(row["avg_mech"] or 0), row["avg_latency_ms"] or 999999))


def _avg_score(items: Sequence[EvalResult], key: str) -> float:
    return round(statistics.mean(item.scores.get(key, 0.0) for item in items), 4)


def _percentile(values: Sequence[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * (percentile / 100)
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def build_ab_sheet(
    results: Sequence[EvalResult],
    scenarios: Sequence[EvalScenario],
) -> Tuple[str, Dict[str, Dict[str, str]]]:
    """Blind A/B sheet: run-1 replies per judged scenario, shuffled, anonymised.

    Returns (markdown, key) where key maps scenario_id -> letter -> model.
    The key is written to a separate file so the read stays blind.
    """
    lines = [
        "# Blind reply sheet",
        "",
        "Replies are shuffled per scenario and labelled with letters.",
        "Rank or mark the ones that hold the voice. The mapping lives in ab_key.json — don't peek first.",
        "",
    ]
    key: Dict[str, Dict[str, str]] = {}
    for scenario in scenarios:
        if not scenario.judge_eligible:
            continue
        entries = [
            r
            for r in results
            if r.scenario_id == scenario.scenario_id and r.run_index == 1 and r.ok and r.reply_text
        ]
        if len(entries) < 2:
            continue
        rng = random.Random(hash_stable(scenario.scenario_id))
        rng.shuffle(entries)
        lines.append(f"## {scenario.scenario_id}")
        lines.append("")
        lines.append(f"> {scenario.user_input}")
        lines.append("")
        key[scenario.scenario_id] = {}
        for offset, result in enumerate(entries):
            letter = chr(ord("A") + offset)
            key[scenario.scenario_id][letter] = result.display_name
            lines.append(f"- **{letter}** — {result.reply_text}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n", key


def write_outputs(
    output_dir: Path,
    results: Sequence[EvalResult],
    scenarios: Sequence[EvalScenario],
    skipped: Sequence[tuple[ModelSpec, str]] = (),
    verdicts: Sequence[JudgeVerdict] = (),
) -> Dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / "raw_results.jsonl"
    summary_json_path = output_dir / "summary.json"
    summary_md_path = output_dir / "summary.md"

    with raw_path.open("w", encoding="utf-8") as fh:
        for result in results:
            fh.write(json.dumps(asdict(result), ensure_ascii=False, default=str) + "\n")

    judge_summary = summarize_judging(verdicts)
    summary_rows = summarize(results)
    for row in summary_rows:
        judge_row = judge_summary.get(row["model"])
        row["judge_win_rate"] = judge_row["win_rate"] if judge_row else None

    summary_json_path.write_text(
        json.dumps(
            {
                "models": summary_rows,
                "judging": judge_summary,
                "judge_agreement": judge_agreement(verdicts),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    summary_md_path.write_text(
        format_markdown_summary(summary_rows, results, scenarios, skipped, verdicts),
        encoding="utf-8",
    )

    paths = {
        "raw": raw_path,
        "summary_json": summary_json_path,
        "summary_md": summary_md_path,
    }

    if verdicts:
        judge_path = output_dir / "judge_results.jsonl"
        with judge_path.open("w", encoding="utf-8") as fh:
            for verdict in verdicts:
                fh.write(json.dumps(asdict(verdict), ensure_ascii=False) + "\n")
        paths["judge"] = judge_path

    ab_markdown, ab_key = build_ab_sheet(results, scenarios)
    if ab_key:
        ab_sheet_path = output_dir / "ab_sheet.md"
        ab_key_path = output_dir / "ab_key.json"
        ab_sheet_path.write_text(ab_markdown, encoding="utf-8")
        ab_key_path.write_text(json.dumps(ab_key, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        paths["ab_sheet"] = ab_sheet_path
        paths["ab_key"] = ab_key_path

    return paths


def _fmt(value: Any, spec: str = "") -> str:
    if value is None:
        return "—"
    return format(value, spec) if spec else str(value)


def format_markdown_summary(
    summary_rows: Sequence[Dict[str, Any]],
    results: Sequence[EvalResult],
    scenarios: Sequence[EvalScenario],
    skipped: Sequence[tuple[ModelSpec, str]] = (),
    verdicts: Sequence[JudgeVerdict] = (),
) -> str:
    lines = [
        "# AI Model Evaluation",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "Mech = deterministic score (JSON, routing, effects, guardrails).",
        "Judge = pairwise win-rate vs incumbent on prose scenarios (0.5 = parity).",
        "Overall/Tone/Interest = legacy Round 3 keyword scores, for comparability only.",
        "",
        "| Model | OK | TTFT | Avg lat | P95 lat | Mech | Guard | Judge | Overall | ±σ | Tone | Interest | Action | Effects | Tok in/out | Cache |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        tokens = f"{_fmt(row['avg_input_tokens'])}/{_fmt(row['avg_output_tokens'])}"
        lines.append(
            "| {model} | {ok} | {ttft} | {lat} | {p95} | {mech} | {guard} | {judge} | {overall} | {stdev} | "
            "{tone} | {interest} | {action} | {effects} | {tokens} | {cache} |".format(
                model=row["model"],
                ok=_fmt(row["ok_rate"], ".2f"),
                ttft=_fmt(row["avg_ttft_ms"], ".0f"),
                lat=_fmt(row["avg_latency_ms"], ".0f"),
                p95=_fmt(row["p95_latency_ms"], ".0f"),
                mech=_fmt(row["avg_mech"], ".2f"),
                guard=_fmt(row["avg_guardrail"], ".2f"),
                judge=_fmt(row.get("judge_win_rate"), ".2f"),
                overall=_fmt(row["avg_overall"], ".2f"),
                stdev=_fmt(row["stdev_overall"], ".2f"),
                tone=_fmt(row["avg_tone"], ".2f"),
                interest=_fmt(row["avg_interesting"], ".2f"),
                action=_fmt(row["action_match_rate"], ".2f"),
                effects=_fmt(row["effects_present_rate"], ".2f"),
                tokens=tokens,
                cache=_fmt(row["cache_hit_rate"], ".2f"),
            )
        )

    agreement = judge_agreement(verdicts)
    if agreement is not None:
        lines.extend(["", f"Judge agreement (both judges, same verdict): {agreement:.2f}"])

    retried = [row for row in summary_rows if row.get("retry_rate")]
    if retried:
        lines.extend(["", "## Transport retries", ""])
        for row in retried:
            lines.append(
                f"- `{row['model']}`: {row['retry_rate']:.0%} of calls needed a retry "
                "(transient API errors; latency reported per successful attempt)"
            )

    if skipped:
        lines.extend(["", "## Skipped Models", ""])
        for spec, reason in skipped:
            lines.append(f"- `{spec.provider}:{spec.display_name}` — {reason}")

    lines.extend(["", "## Scenario Notes", ""])
    scenario_lookup = {scenario.scenario_id: scenario for scenario in scenarios}
    for scenario_id in sorted({result.scenario_id for result in results}):
        scenario = scenario_lookup.get(scenario_id)
        if scenario:
            lines.append(f"- `{scenario_id}`: {scenario.notes}")

    lines.extend(["", "## Raw Reply Samples", ""])
    for result in results:
        if not result.ok or result.run_index != 1:
            continue
        lines.append(f"### {result.display_name} / {result.scenario_id}")
        lines.append("")
        lines.append(f"- Input: `{result.user_input}`")
        lines.append(f"- Action: `{result.parsed.get('action') if result.parsed else None}`")
        lines.append(f"- Reply: {result.reply_text}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _run_spec(
    spec: ModelSpec,
    scenarios: Sequence[EvalScenario],
    runs: int,
    timeout: float,
    warmup: bool = True,
) -> List[EvalResult]:
    """All calls for one model, serially, so latency numbers stay clean."""
    results: List[EvalResult] = []
    if warmup and scenarios:
        # Untimed throwaway call: client init and TLS handshake otherwise
        # land in the first measured sample and distort P95 on small runs.
        print(f"[model-eval] {spec.display_name} / warmup", flush=True)
        run_one(spec, scenarios[0], 0, timeout)
    for scenario in scenarios:
        for run_index in range(1, runs + 1):
            print(f"[model-eval] {spec.display_name} / {scenario.scenario_id} / run {run_index}", flush=True)
            results.append(run_one(spec, scenario, run_index, timeout))
    return results


def run_evaluation(
    model_specs: Sequence[ModelSpec],
    scenarios: Sequence[EvalScenario],
    *,
    runs: int,
    timeout: float,
    parallel_models: bool = True,
    warmup: bool = True,
) -> tuple[List[EvalResult], List[tuple[ModelSpec, str]]]:
    runnable: List[ModelSpec] = []
    skipped: List[tuple[ModelSpec, str]] = []
    for spec in model_specs:
        skip = _provider_skip_reason(spec)
        if skip:
            print(f"[model-eval] SKIP {spec.provider}:{spec.display_name} — {skip}", flush=True)
            skipped.append((spec, skip))
        else:
            runnable.append(spec)

    results: List[EvalResult] = []
    if not runnable:
        return results, skipped

    if parallel_models and len(runnable) > 1:
        # One thread per model: each model's calls stay serial (clean latency),
        # while the wall clock is bounded by the slowest model, not the sum.
        with ThreadPoolExecutor(max_workers=len(runnable)) as pool:
            futures = [pool.submit(_run_spec, spec, scenarios, runs, timeout, warmup) for spec in runnable]
            for future in futures:
                results.extend(future.result())
    else:
        for spec in runnable:
            results.extend(_run_spec(spec, scenarios, runs, timeout, warmup))
    return results, skipped


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate diegetic AI model responses.")
    parser.add_argument("--models", action="append", help="Comma-separated model specs, e.g. gpt-5.6-terra:low,anthropic:claude-sonnet-5")
    parser.add_argument("--all", action="store_true", help="Run the full multi-provider slate (ALL_MODEL_SPECS).")
    parser.add_argument("--runs", type=int, default=1, help="Repeated calls per model/scenario. Use 5+ for decisions.")
    parser.add_argument("--timeout", type=float, default=60.0, help="Per-request timeout in seconds.")
    parser.add_argument("--max-scenarios", type=int, help="Only run the first N scenarios.")
    parser.add_argument("--output-dir", type=Path, default=Path("reports/model_eval"), help="Directory for evaluation output.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned models/scenarios without calling the API.")
    parser.add_argument("--no-parallel", action="store_true", help="Run models serially instead of one thread per model.")
    parser.add_argument("--no-warmup", action="store_true", help="Skip the untimed warmup call per model.")
    parser.add_argument("--no-judge", action="store_true", help="Skip the pairwise judge stage.")
    parser.add_argument("--judges", action="append", help="Comma-separated judge specs (default: gpt-5.5 + claude-sonnet-5).")
    parser.add_argument("--judge-runs", type=int, default=3, help="Judge at most the first N runs per scenario.")
    parser.add_argument("--incumbent", default=INCUMBENT_LABEL, help="Display name of the incumbent for pairwise judging.")
    args = parser.parse_args(argv)

    if args.all:
        model_specs = list(ALL_MODEL_SPECS)
    else:
        model_specs = parse_model_specs(args.models)
    scenarios = DEFAULT_SCENARIOS[: args.max_scenarios] if args.max_scenarios else DEFAULT_SCENARIOS
    judges = parse_model_specs(args.judges) if args.judges else list(DEFAULT_JUDGE_SPECS)

    if args.dry_run:
        print("Models:")
        for spec in model_specs:
            skip = _provider_skip_reason(spec)
            tag = f" (SKIP — {skip})" if skip else ""
            print(f"- {spec.provider}:{spec.display_name}{tag}")
        print("Scenarios:")
        for scenario in scenarios:
            marks = []
            if scenario.judge_eligible:
                marks.append("judged")
            if scenario.forbid_words:
                marks.append(f"forbid={','.join(scenario.forbid_words)}")
            suffix = f" [{', '.join(marks)}]" if marks else ""
            print(f"- {scenario.scenario_id}: {scenario.user_input}{suffix}")
        if not args.no_judge:
            print("Judges:")
            for judge in judges:
                print(f"- {judge.provider}:{judge.display_name}")
        return 0

    run_dir = args.output_dir / datetime.now().strftime("%Y%m%d_%H%M%S")
    results, skipped = run_evaluation(
        model_specs,
        scenarios,
        runs=args.runs,
        timeout=args.timeout,
        parallel_models=not args.no_parallel,
        warmup=not args.no_warmup,
    )

    verdicts: List[JudgeVerdict] = []
    if not args.no_judge and results:
        verdicts = run_judging(
            results,
            scenarios,
            judges,
            incumbent_label=args.incumbent,
            judge_runs=args.judge_runs,
            timeout=args.timeout,
        )

    paths = write_outputs(run_dir, results, scenarios, skipped, verdicts)
    print(f"[model-eval] wrote {paths['summary_md']}", flush=True)
    return 1 if any(not result.ok for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
