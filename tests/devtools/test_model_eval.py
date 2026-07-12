from game.ai_interpreter import (
    _act_v_offer_active,
    build_interpreter_messages,
    build_openai_chat_params,
    make_openai_params_compatible,
)
from game.devtools.model_eval import (
    DEFAULT_SCENARIOS,
    EvalResult,
    EvalScenario,
    JudgeVerdict,
    STORY_SCENARIOS,
    _base_context,
    _seed_context,
    build_ab_sheet,
    challenger_position,
    judge_agreement,
    parse_model_spec,
    parse_model_specs,
    score_response,
    split_system_for_cache,
    summarize,
    summarize_judging,
)


def _result(**overrides):
    defaults = dict(
        model="gpt-5-mini",
        provider="openai",
        reasoning_effort="low",
        scenario_id="sample",
        run_index=1,
        user_input="wait",
        latency_ms=123.0,
        ttft_ms=45.0,
        ok=True,
        raw_output="{}",
        parsed={},
        scores={
            "overall": 0.5,
            "mech": 0.8,
            "guardrail": 1.0,
            "tone": 0.6,
            "interesting": 0.7,
            "action_match": 1.0,
            "effects_present": 1.0,
        },
        usage={"input_tokens": 900, "output_tokens": 80},
        errors=[],
    )
    defaults.update(overrides)
    return EvalResult(**defaults)


def test_parse_model_spec_defaults_to_openai():
    spec = parse_model_spec("gpt-5-mini:low")

    assert spec.provider == "openai"
    assert spec.model == "gpt-5-mini"
    assert spec.reasoning_effort == "low"


def test_parse_model_spec_accepts_provider_prefix():
    spec = parse_model_spec("anthropic:claude-sonnet-5")

    assert spec.provider == "anthropic"
    assert spec.model == "claude-sonnet-5"
    assert spec.reasoning_effort is None


def test_parse_model_specs_splits_commas():
    specs = parse_model_specs(["gpt-4.1-mini,gpt-5-mini:minimal"])

    assert [spec.display_name for spec in specs] == ["gpt-4.1-mini", "gpt-5-mini:minimal"]


def test_openai_param_builder_keeps_legacy_temperature_for_non_gpt5():
    params = build_openai_chat_params("gpt-4.1-mini", build_interpreter_messages("wait", _base_context()))

    assert params["max_tokens"] == 400
    assert params["temperature"] == 0
    assert "reasoning_effort" not in params


def test_openai_param_builder_uses_reasoning_effort_for_gpt5():
    params = build_openai_chat_params(
        "gpt-5-mini",
        build_interpreter_messages("wait", _base_context()),
        reasoning_effort="low",
    )

    assert params["max_completion_tokens"] == 800
    assert params["reasoning_effort"] == "low"
    assert "temperature" not in params


def test_openai_param_compat_moves_newer_fields_to_extra_body_for_old_sdks():
    def old_create(*, model, messages, response_format, stream, max_tokens=None, extra_body=None):
        return None

    params = {
        "model": "gpt-5.4-mini",
        "messages": [],
        "response_format": {"type": "json_object"},
        "stream": True,
        "max_completion_tokens": 800,
        "reasoning_effort": "none",
    }

    compatible = make_openai_params_compatible(old_create, params)

    assert "max_completion_tokens" not in compatible
    assert "reasoning_effort" not in compatible
    assert compatible["extra_body"] == {
        "max_completion_tokens": 800,
        "reasoning_effort": "none",
    }


def test_score_response_rewards_diegetic_reply():
    scenario = EvalScenario(
        scenario_id="sample",
        user_input="fly",
        context=_base_context(),
        expected_action="none",
        expect_effect=True,
    )
    parsed = {
        "action": "none",
        "args": {},
        "confidence": 0.8,
        "reply": "You tense your legs. The cold bites your lungs; the dark stays above you.",
        "effects": {"fear": 1, "health": 0, "inventory_add": [], "inventory_remove": []},
    }

    scores = score_response(parsed, "", scenario)

    assert scores["json_valid"] == 1.0
    assert scores["action_match"] == 1.0
    assert scores["effects_present"] == 1.0
    assert scores["guardrail"] == 1.0
    assert scores["mech"] == 1.0
    assert scores["tone"] > 0.8
    assert scores["interesting"] > 0.6


def test_score_response_flags_forbidden_and_unbounded():
    scenario = EvalScenario(
        scenario_id="bait",
        user_input="shout at the trees",
        context=_base_context(),
        expected_action="none",
        forbid_words=("lyer",),
    )
    parsed = {
        "action": "none",
        "reply": "The Lyer watches you from the treeline.",
        "effects": {"fear": 9, "health": 0},
    }

    scores = score_response(parsed, "", scenario)

    # Forbidden word, Lyer-naming, and out-of-bounds fear delta all bite.
    assert scores["guardrail"] < 0.8
    assert scores["mech"] < 1.0


def test_score_response_meta_check_ignores_innocent_substrings():
    scenario = EvalScenario(
        scenario_id="prose",
        user_input="wait",
        context=_base_context(),
        expected_action="none",
    )
    # "afraid", "air", "wait" all contain the substring "ai" but are not meta.
    parsed = {
        "action": "none",
        "reply": "You wait in the cold air, afraid to breathe. The dark holds still.",
    }

    scores = score_response(parsed, "", scenario)

    assert scores["guardrail"] == 1.0
    assert scores["tone"] > 0.8


def test_score_response_meta_check_still_catches_whole_words():
    scenario = EvalScenario(
        scenario_id="meta",
        user_input="help",
        context=_base_context(),
        expected_action="none",
    )
    parsed = {"action": "none", "reply": "As an AI model, I cannot do that in this game."}

    scores = score_response(parsed, "", scenario)

    assert scores["guardrail"] < 1.0


def test_score_response_lyer_check_ignores_flyer():
    scenario = EvalScenario(
        scenario_id="prose",
        user_input="look",
        context=_base_context(),
        expected_action="none",
    )
    parsed = {"action": "none", "reply": "A faded flyer is pinned to the wall, curling at the edge."}

    scores = score_response(parsed, "", scenario)

    # "flyer" contains "lyer" but is not the proper noun.
    assert scores["guardrail"] == 1.0


def test_parse_model_spec_rejects_unsupported_three_part_provider():
    import pytest

    with pytest.raises(ValueError, match="Unsupported provider"):
        parse_model_spec("gemini:gemini-2.5:low")


def test_score_response_lyer_naming_checked_everywhere():
    scenario = EvalScenario(
        scenario_id="plain",
        user_input="breathe",
        context=_base_context(),
        expected_action="none",
    )
    clean = score_response({"action": "none", "reply": "You breathe. The cold answers."}, "", scenario)
    named = score_response({"action": "none", "reply": "The lyer breathes with you."}, "", scenario)

    assert named["guardrail"] < clean["guardrail"]


def test_summarize_groups_model_and_reasoning_effort():
    rows = summarize([_result()])

    assert rows[0]["model"] == "gpt-5-mini:low"
    assert rows[0]["avg_latency_ms"] == 123.0
    assert rows[0]["avg_ttft_ms"] == 45.0
    assert rows[0]["avg_input_tokens"] == 900
    assert rows[0]["avg_output_tokens"] == 80


def test_run_one_retries_transport_errors_not_bad_json(monkeypatch):
    import game.devtools.model_eval as me

    calls = {"n": 0}

    def flaky_call(spec, messages, timeout):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("401 insufficient permissions")
        return {"text": '{"action": "none", "reply": "You wait."}', "ttft_ms": 10.0, "usage": {}}

    monkeypatch.setattr(me, "call_model", flaky_call)
    monkeypatch.setattr(me.time, "sleep", lambda _s: None)
    spec = me.ModelSpec(provider="openai", model="gpt-5.6-terra", reasoning_effort="none")
    scenario = me.DEFAULT_SCENARIOS[0]

    result = me.run_one(spec, scenario, 1, timeout=5.0)

    assert result.ok
    assert result.attempts == 2

    def bad_json_call(spec, messages, timeout):
        calls["n"] += 1
        return {"text": "not json", "ttft_ms": 10.0, "usage": {}}

    calls["n"] = 0
    monkeypatch.setattr(me, "call_model", bad_json_call)
    result = me.run_one(spec, scenario, 1, timeout=5.0)

    # Malformed output is a quality failure: no retry, scored as not ok.
    assert not result.ok
    assert result.attempts == 1
    assert calls["n"] == 1


def test_summarize_reports_variance():
    rows = summarize(
        [
            _result(run_index=1, scores={**_result().scores, "overall": 0.4}),
            _result(run_index=2, scores={**_result().scores, "overall": 0.8}),
        ]
    )

    assert rows[0]["stdev_overall"] > 0.2


def test_split_system_for_cache_marks_static_prefix():
    messages = build_interpreter_messages("wait", _base_context())
    system_text = messages[0]["content"]

    blocks = split_system_for_cache(system_text)

    assert len(blocks) == 2
    assert blocks[0]["cache_control"] == {"type": "ephemeral"}
    assert blocks[1]["text"].startswith("Constraints:")
    # Nothing scenario-specific may sit in the cacheable prefix.
    assert "stick" not in blocks[0]["text"]
    assert blocks[0]["text"] + blocks[1]["text"] == system_text


def test_split_system_for_cache_handles_missing_marker():
    blocks = split_system_for_cache("no marker here")

    assert blocks == [{"type": "text", "text": "no marker here"}]


def test_challenger_position_is_deterministic_and_swaps():
    first = challenger_position("impossible_backflip", 1)
    again = challenger_position("impossible_backflip", 1)
    swapped = challenger_position("impossible_backflip", 2)

    assert first == again
    assert first != swapped
    assert {first, swapped} == {"A", "B"}


def _verdict(**overrides):
    defaults = dict(
        judge="judge:gpt-5.5",
        scenario_id="sample",
        run_index=1,
        challenger="claude-sonnet-5",
        incumbent="gpt-5.4-mini:none",
        challenger_position="A",
        winner="challenger",
        reason="better",
    )
    defaults.update(overrides)
    return JudgeVerdict(**defaults)


def test_summarize_judging_computes_win_rate_with_ties():
    verdicts = [
        _verdict(winner="challenger"),
        _verdict(run_index=2, winner="tie"),
        _verdict(run_index=3, winner="incumbent"),
        _verdict(run_index=4, winner="error"),
    ]

    summary = summarize_judging(verdicts)

    row = summary["claude-sonnet-5"]
    assert row["wins"] == 1
    assert row["ties"] == 1
    assert row["losses"] == 1
    assert row["win_rate"] == 0.5


def test_judge_agreement_counts_matching_verdicts():
    verdicts = [
        _verdict(judge="judge:gpt-5.5", winner="challenger"),
        _verdict(judge="judge:claude-sonnet-5", winner="challenger"),
        _verdict(judge="judge:gpt-5.5", run_index=2, winner="challenger"),
        _verdict(judge="judge:claude-sonnet-5", run_index=2, winner="incumbent"),
    ]

    assert judge_agreement(verdicts) == 0.5


def test_seed_context_matches_engine_shape():
    context = _seed_context("act3_seated", fear=48)

    assert context["world_flags"]["world_layer"] == "wrong"
    assert context["fear"] == 48
    assert "room_id" in context
    assert "allowed_actions" in context
    # Wrong-layer fixtures are visible; nothing lives there.
    assert "nika" in context["room_items"]
    assert context["room_wildlife"] == []


def test_act5_scenario_context_has_live_offer():
    act5 = next(s for s in STORY_SCENARIOS if s.scenario_id == "act5_accept_door")

    assert _act_v_offer_active(act5.context)
    assert act5.expected_action == "accept"


def test_act5_inactive_scenario_has_no_offer():
    inactive = next(s for s in STORY_SCENARIOS if s.scenario_id == "act5_threshold_inactive")

    assert not _act_v_offer_active(inactive.context)
    assert inactive.expected_action == "none"


def test_default_scenarios_include_legacy_and_story():
    ids = {scenario.scenario_id for scenario in DEFAULT_SCENARIOS}

    assert "impossible_backflip" in ids  # Round 3 comparability
    assert "lyer_bait_shout" in ids
    assert len(ids) == len(DEFAULT_SCENARIOS)


def test_judge_eligibility_covers_prose_scenarios_only():
    by_id = {scenario.scenario_id: scenario for scenario in DEFAULT_SCENARIOS}

    assert by_id["impossible_backflip"].judge_eligible
    assert by_id["wrong_layer_heartbeats"].judge_eligible
    assert not by_id["take_visible_stone"].judge_eligible  # expect_reply=False
    assert not by_id["look_at_sky"].judge_eligible  # not action none
    assert not by_id["act5_accept_door"].judge_eligible


def test_build_ab_sheet_shuffles_and_keys():
    scenario = DEFAULT_SCENARIOS[0]
    results = [
        _result(
            model=f"model-{i}",
            reasoning_effort=None,
            scenario_id=scenario.scenario_id,
            parsed={"reply": f"Reply number {i}."},
        )
        for i in range(3)
    ]

    markdown, key = build_ab_sheet(results, [scenario])

    letters = key[scenario.scenario_id]
    assert sorted(letters.keys()) == ["A", "B", "C"]
    assert sorted(letters.values()) == ["model-0", "model-1", "model-2"]
    # Sheet shows replies but never model names.
    assert "model-0" not in markdown
    assert "Reply number 0." in markdown
