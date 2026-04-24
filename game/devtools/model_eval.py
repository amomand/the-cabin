from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

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
    notes: str = ""


@dataclass
class EvalResult:
    model: str
    provider: str
    reasoning_effort: Optional[str]
    scenario_id: str
    run_index: int
    user_input: str
    latency_ms: float
    ok: bool
    raw_output: str
    parsed: Optional[Dict[str, Any]]
    scores: Dict[str, float]
    errors: List[str]


DEFAULT_MODEL_SPECS = [
    ModelSpec(provider="openai", model="gpt-4.1-mini"),
    ModelSpec(provider="openai", model="gpt-5-mini", reasoning_effort="minimal"),
    ModelSpec(provider="openai", model="gpt-5-mini", reasoning_effort="low"),
    ModelSpec(provider="openai", model="gpt-5.4-mini", reasoning_effort="none"),
    ModelSpec(provider="openai", model="gpt-5.4-nano", reasoning_effort="none"),
]


def _base_context(**overrides: Any) -> Dict[str, Any]:
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


DEFAULT_SCENARIOS = [
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


def parse_model_spec(raw: str) -> ModelSpec:
    """Parse provider/model specs like openai:gpt-5-mini:low or gpt-4.1-mini."""
    parts = [part.strip() for part in raw.split(":") if part.strip()]
    if len(parts) == 1:
        return ModelSpec(provider="openai", model=parts[0])
    if len(parts) == 2:
        if parts[0] in {"openai", "anthropic", "gemini"}:
            return ModelSpec(provider=parts[0], model=parts[1])
        return ModelSpec(provider="openai", model=parts[0], reasoning_effort=parts[1])
    if len(parts) == 3:
        return ModelSpec(provider=parts[0], model=parts[1], reasoning_effort=parts[2])
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


def score_response(parsed: Optional[Dict[str, Any]], raw_output: str, scenario: EvalScenario) -> Dict[str, float]:
    if parsed is None:
        return {
            "json_valid": 0.0,
            "action_match": 0.0,
            "reply_present": 0.0,
            "effects_present": 0.0,
            "tone": 0.0,
            "interesting": 0.0,
            "overall": 0.0,
        }

    reply = parsed.get("reply")
    reply_text = str(reply or "").strip()
    reply_lower = reply_text.lower()
    effects = parsed.get("effects") if isinstance(parsed.get("effects"), dict) else {}
    fear_effect = int(effects.get("fear", 0) or 0)
    health_effect = int(effects.get("health", 0) or 0)

    json_valid = 1.0
    action_match = 1.0 if parsed.get("action") == scenario.expected_action else 0.0
    reply_present = 1.0 if (not scenario.expect_reply or reply_text) else 0.0
    effects_present = 1.0
    if scenario.expect_effect:
        effects_present = 1.0 if fear_effect != 0 or health_effect != 0 else 0.0

    second_person = 1.0 if "you" in reply_lower else 0.0
    dark_signal = min(1.0, sum(1 for word in DARK_WORDS if word in reply_lower) / 2)
    no_meta = 0.0 if any(word in reply_lower for word in META_WORDS) else 1.0
    terse = 1.0 if len(reply_text) <= 200 else max(0.0, 1 - ((len(reply_text) - 200) / 200))
    no_exclaim = 0.0 if "!" in reply_text else 1.0
    no_generic = 0.0 if any(phrase in reply_lower for phrase in GENERIC_PHRASES) else 1.0
    tone = statistics.mean([second_person, dark_signal, no_meta, terse, no_exclaim, no_generic])

    sensory = min(1.0, sum(1 for word in SENSORY_WORDS if word in reply_lower) / 2)
    consequence = min(1.0, sum(1 for word in CONSEQUENCE_WORDS if word in reply_lower) / 1)
    specificity = min(1.0, len(set(reply_lower.replace(".", "").replace(",", "").split())) / 18)
    interesting = statistics.mean([sensory, consequence, specificity, no_generic])

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
        "tone": round(tone, 4),
        "interesting": round(interesting, 4),
        "overall": round(overall, 4),
    }


def _collect_stream_content(stream: Iterable[Any]) -> str:
    chunks: List[str] = []
    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            chunks.append(delta.content)
    return "".join(chunks).strip()


def call_openai(spec: ModelSpec, scenario: EvalScenario, timeout: float) -> str:
    if spec.provider != "openai":
        raise NotImplementedError(f"Provider is not implemented yet: {spec.provider}")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required to run model evaluations")

    from openai import OpenAI  # type: ignore

    client = OpenAI()
    messages = build_interpreter_messages(scenario.user_input, scenario.context)
    params = build_openai_chat_params(
        spec.model,
        messages,
        stream=True,
        reasoning_effort=spec.reasoning_effort,
    )
    params["timeout"] = timeout
    params = make_openai_params_compatible(client.chat.completions.create, params)
    return _collect_stream_content(client.chat.completions.create(**params))


def run_one(spec: ModelSpec, scenario: EvalScenario, run_index: int, timeout: float) -> EvalResult:
    started = time.perf_counter()
    raw_output = ""
    parsed: Optional[Dict[str, Any]] = None
    errors: List[str] = []

    try:
        raw_output = call_openai(spec, scenario, timeout)
        parsed = json.loads(raw_output)
    except Exception as exc:
        errors.append(repr(exc))

    latency_ms = (time.perf_counter() - started) * 1000
    scores = score_response(parsed, raw_output, scenario)

    return EvalResult(
        model=spec.model,
        provider=spec.provider,
        reasoning_effort=spec.reasoning_effort,
        scenario_id=scenario.scenario_id,
        run_index=run_index,
        user_input=scenario.user_input,
        latency_ms=round(latency_ms, 2),
        ok=not errors and parsed is not None,
        raw_output=raw_output,
        parsed=parsed,
        scores=scores,
        errors=errors,
    )


def summarize(results: Sequence[EvalResult]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[EvalResult]] = {}
    for result in results:
        key = result.model if not result.reasoning_effort else f"{result.model}:{result.reasoning_effort}"
        grouped.setdefault(key, []).append(result)

    rows: List[Dict[str, Any]] = []
    for label, items in grouped.items():
        latencies = [item.latency_ms for item in items if item.ok]
        rows.append(
            {
                "model": label,
                "provider": items[0].provider,
                "runs": len(items),
                "ok_rate": round(sum(1 for item in items if item.ok) / len(items), 4),
                "avg_latency_ms": round(statistics.mean(latencies), 2) if latencies else None,
                "p95_latency_ms": round(_percentile(latencies, 95), 2) if latencies else None,
                "avg_overall": _avg_score(items, "overall"),
                "avg_tone": _avg_score(items, "tone"),
                "avg_interesting": _avg_score(items, "interesting"),
                "action_match_rate": _avg_score(items, "action_match"),
                "effects_present_rate": _avg_score(items, "effects_present"),
            }
        )
    return sorted(rows, key=lambda row: (-(row["avg_overall"] or 0), row["avg_latency_ms"] or 999999))


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


def write_outputs(output_dir: Path, results: Sequence[EvalResult]) -> Dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / "raw_results.jsonl"
    summary_json_path = output_dir / "summary.json"
    summary_md_path = output_dir / "summary.md"

    with raw_path.open("w", encoding="utf-8") as fh:
        for result in results:
            fh.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")

    summary_rows = summarize(results)
    summary_json_path.write_text(json.dumps(summary_rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary_md_path.write_text(format_markdown_summary(summary_rows, results), encoding="utf-8")

    return {
        "raw": raw_path,
        "summary_json": summary_json_path,
        "summary_md": summary_md_path,
    }


def format_markdown_summary(summary_rows: Sequence[Dict[str, Any]], results: Sequence[EvalResult]) -> str:
    lines = [
        "# AI Model Evaluation",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "| Model | OK | Avg latency | P95 latency | Overall | Tone | Interesting | Action | Effects |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            "| {model} | {ok_rate:.2f} | {avg_latency_ms} | {p95_latency_ms} | "
            "{avg_overall:.2f} | {avg_tone:.2f} | {avg_interesting:.2f} | "
            "{action_match_rate:.2f} | {effects_present_rate:.2f} |".format(**row)
        )

    lines.extend(["", "## Scenario Notes", ""])
    scenario_lookup = {scenario.scenario_id: scenario for scenario in DEFAULT_SCENARIOS}
    for scenario_id in sorted({result.scenario_id for result in results}):
        scenario = scenario_lookup.get(scenario_id)
        if scenario:
            lines.append(f"- `{scenario_id}`: {scenario.notes}")

    lines.extend(["", "## Raw Reply Samples", ""])
    for result in results:
        if not result.ok or result.run_index != 1:
            continue
        reply = ""
        if result.parsed:
            reply = str(result.parsed.get("reply") or "")
        label = result.model if not result.reasoning_effort else f"{result.model}:{result.reasoning_effort}"
        lines.append(f"### {label} / {result.scenario_id}")
        lines.append("")
        lines.append(f"- Input: `{result.user_input}`")
        lines.append(f"- Action: `{result.parsed.get('action') if result.parsed else None}`")
        lines.append(f"- Reply: {reply}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def run_evaluation(
    model_specs: Sequence[ModelSpec],
    scenarios: Sequence[EvalScenario],
    *,
    runs: int,
    timeout: float,
) -> List[EvalResult]:
    results: List[EvalResult] = []
    for spec in model_specs:
        for scenario in scenarios:
            for run_index in range(1, runs + 1):
                print(f"[model-eval] {spec.display_name} / {scenario.scenario_id} / run {run_index}", flush=True)
                results.append(run_one(spec, scenario, run_index, timeout))
    return results


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate diegetic AI model responses.")
    parser.add_argument("--models", action="append", help="Comma-separated model specs, e.g. gpt-4.1-mini,gpt-5-mini:low")
    parser.add_argument("--runs", type=int, default=1, help="Repeated calls per model/scenario.")
    parser.add_argument("--timeout", type=float, default=30.0, help="Per-request timeout in seconds.")
    parser.add_argument("--max-scenarios", type=int, help="Only run the first N scenarios.")
    parser.add_argument("--output-dir", type=Path, default=Path("reports/model_eval"), help="Directory for evaluation output.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned models/scenarios without calling the API.")
    args = parser.parse_args(argv)

    model_specs = parse_model_specs(args.models)
    scenarios = DEFAULT_SCENARIOS[: args.max_scenarios] if args.max_scenarios else DEFAULT_SCENARIOS

    if args.dry_run:
        print("Models:")
        for spec in model_specs:
            print(f"- {spec.provider}:{spec.display_name}")
        print("Scenarios:")
        for scenario in scenarios:
            print(f"- {scenario.scenario_id}: {scenario.user_input}")
        return 0

    run_dir = args.output_dir / datetime.now().strftime("%Y%m%d_%H%M%S")
    results = run_evaluation(model_specs, scenarios, runs=args.runs, timeout=args.timeout)
    paths = write_outputs(run_dir, results)
    print(f"[model-eval] wrote {paths['summary_md']}", flush=True)
    return 1 if any(not result.ok for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
