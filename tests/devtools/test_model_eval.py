from game.ai_interpreter import (
    _act_v_offer_active,
    build_interpreter_messages,
)
from game.devtools.model_eval import (
    DEFAULT_SCENARIOS,
    EvalResult,
    EvalScenario,
    JudgeVerdict,
    ROUND5_PROSE_SCENARIOS,
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
    wilson_interval,
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


def test_parse_model_spec_defaults_gpt5_to_none_effort():
    # Bare gpt-5* shorthand must match the incumbent label and production default.
    assert parse_model_spec("gpt-5.4-mini").display_name == "gpt-5.4-mini:none"
    assert parse_model_spec("openai:gpt-5.6-terra").reasoning_effort == "none"


def test_parse_model_spec_leaves_non_gpt5_effort_unset():
    assert parse_model_spec("gpt-4.1-mini").reasoning_effort is None
    assert parse_model_spec("anthropic:claude-sonnet-5").reasoning_effort is None


def test_parse_model_specs_splits_commas():
    specs = parse_model_specs(["gpt-4.1-mini,gpt-5-mini:minimal"])

    assert [spec.display_name for spec in specs] == ["gpt-4.1-mini", "gpt-5-mini:minimal"]


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


def test_strip_code_fences_handles_leading_whitespace_and_json_tag():
    from game.devtools.model_eval import _strip_code_fences

    assert _strip_code_fences('\n```json\n{"action": "none"}\n```') == '{"action": "none"}'
    assert _strip_code_fences('  ```\n{"a": 1}\n```  ') == '{"a": 1}'
    assert _strip_code_fences('{"already": "clean"}') == '{"already": "clean"}'


def test_build_ai_context_allowed_actions_sorted():
    from game.ai_context import build_ai_context
    from game.devtools import seed_saves

    state = seed_saves.SEEDS["act2_mid"]()
    context = build_ai_context(state.player, state.map, state.quest_manager)

    assert context["allowed_actions"] == sorted(context["allowed_actions"])


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
    assert row["n"] == 3


def test_wilson_interval_known_values():
    # p=0.5, n=100: Wilson gives [0.40383, 0.59617]. The tolerance is tight
    # enough (1e-4) to reject the normal approximation, whose bounds are
    # [0.402, 0.598] — a 1.8e-3 gap a loose tolerance would wave through.
    lower, upper = wilson_interval(50, 100)
    assert abs(lower - 0.40383) < 1e-4
    assert abs(upper - 0.59617) < 1e-4
    # Degenerate input must not divide by zero.
    assert wilson_interval(0, 0) == (0.0, 1.0)
    # Bounds stay ordered inside [0, 1]; p=1 pins the upper bound at 1.
    lo_all, hi_all = wilson_interval(10, 10)
    assert 0.0 <= lo_all <= hi_all <= 1.0
    assert abs(hi_all - 1.0) < 1e-9


def test_wilson_interval_narrows_with_sample_size():
    narrow = wilson_interval(300, 600)
    wide = wilson_interval(30, 60)

    assert (narrow[1] - narrow[0]) < (wide[1] - wide[0])


def test_win_rate_read_boundary_is_strict():
    from game.devtools.model_eval import _win_rate_read

    # "Clears 0.5" means strictly: a bound sitting exactly on 0.5 is parity.
    # Exactly-0.5 lower bounds are reachable (e.g. wilson_interval(337, 625)).
    assert _win_rate_read(0.5, 0.9) == "parity"
    assert _win_rate_read(0.1, 0.5) == "parity"
    assert _win_rate_read(0.5001, 0.9) == "better"
    assert _win_rate_read(0.1, 0.4999) == "worse"


def test_cluster_bootstrap_interval_deterministic_and_guarded():
    from game.devtools.model_eval import cluster_bootstrap_interval

    clusters = [(9.0, 10), (8.0, 10), (10.0, 10), (7.0, 10)]
    first = cluster_bootstrap_interval(clusters, seed=7)
    again = cluster_bootstrap_interval(clusters, seed=7)
    assert first == again
    # Fewer than two clusters cannot support a resampling interval.
    assert cluster_bootstrap_interval([(5.0, 10)], seed=7) is None
    assert cluster_bootstrap_interval([], seed=7) is None
    # All-error clusters (total 0) are excluded before the threshold check.
    assert cluster_bootstrap_interval([(0.0, 0), (5.0, 10)], seed=7) is None


def test_cluster_bootstrap_pins_95_percent_level():
    from game.devtools.model_eval import cluster_bootstrap_interval

    # Three equal clusters at rates 1.0 / 0.0 / 0.5. An all-losses resample
    # has probability 1/27 ~ 0.037: above the 2.5% tail, so a 95% interval's
    # lower bound must be exactly 0.0 (and by symmetry the upper exactly 1.0).
    # A silently narrowed level (e.g. 90%, tail 5% > 3.7%) excludes those
    # resamples and fails this — the nominal level is the decision instrument.
    clusters = [(10.0, 10), (0.0, 10), (5.0, 10)]

    lower, upper = cluster_bootstrap_interval(clusters, seed=3)

    assert lower == 0.0
    assert upper == 1.0


def test_cluster_bootstrap_reads_are_seed_stable():
    from game.devtools.model_eval import cluster_bootstrap_interval

    # A borderline verdict must not depend on the seed (which is derived from
    # the challenger's name). With too few resamples the bound wobbles across
    # the 0.5 threshold; at the shipped default the spread stays tiny.
    clusters = [
        (1.0, 6), (5.0, 6), (2.0, 6), (4.0, 6), (0.5, 6), (3.0, 6), (5.5, 6),
        (2.5, 6), (1.5, 6), (4.5, 6), (3.5, 6), (2.0, 6), (3.0, 6),
    ]

    intervals = [cluster_bootstrap_interval(clusters, seed=s) for s in range(5)]

    uppers = [interval[1] for interval in intervals]
    lowers = [interval[0] for interval in intervals]
    assert max(uppers) - min(uppers) < 0.02
    assert max(lowers) - min(lowers) < 0.02


def test_tie_scoring_agrees_between_win_rate_and_cluster_ci():
    # The tie convention exists in one place (_VERDICT_SCORE). If the point
    # estimate and the cluster accumulator ever diverge, an all-ties dataset
    # puts win_rate outside its own CI — pin that they collapse together.
    verdicts = [
        _verdict(scenario_id=f"s{s}", run_index=r, winner="tie")
        for s in range(4)
        for r in range(1, 6)
    ]

    row = summarize_judging(verdicts)["claude-sonnet-5"]

    assert row["win_rate"] == 0.5
    assert row["ci95"] == [0.5, 0.5]
    assert row["ci95"][0] <= row["win_rate"] <= row["ci95"][1]
    assert row["read"] == "parity"


def test_summarize_judging_flags_better_and_worse_on_consistent_clusters():
    # Homogeneous strength across many scenarios is a real signal.
    dominant = [
        _verdict(scenario_id=f"s{s}", run_index=r, winner="challenger" if r < 10 else "incumbent")
        for s in range(10)
        for r in range(1, 11)
    ]
    dominated = [
        _verdict(
            challenger="claude-haiku-4-5",
            scenario_id=f"s{s}",
            run_index=r,
            winner="incumbent" if r < 10 else "challenger",
        )
        for s in range(10)
        for r in range(1, 11)
    ]

    summary = summarize_judging(dominant + dominated)

    assert summary["claude-sonnet-5"]["read"] == "better"
    assert summary["claude-haiku-4-5"]["read"] == "worse"
    assert summary["claude-sonnet-5"]["scenarios"] == 10


def test_cluster_ci_resists_deep_runs_on_few_scenarios():
    # The Round 4 failure mode: three scenarios, 30 verdicts each, going
    # 100%/100%/0%. n=90 at 0.667 makes Wilson confidently "better"; the
    # cluster interval sees three situations, one of which the challenger
    # loses outright, and refuses to call it.
    verdicts = [
        _verdict(scenario_id=f"s{s}", run_index=r, winner="challenger" if s < 2 else "incumbent")
        for s in range(3)
        for r in range(1, 31)
    ]

    row = summarize_judging(verdicts)["claude-sonnet-5"]

    assert row["ci95_wilson"][0] > 0.5  # the naive read would switch models
    assert row["read"] == "parity"


def test_summarize_judging_single_scenario_reports_too_few_clusters():
    verdicts = [_verdict(run_index=r, winner="challenger") for r in range(1, 21)]

    row = summarize_judging(verdicts)["claude-sonnet-5"]

    assert row["scenarios"] == 1
    assert row["ci95"] is None
    assert row["read"] == "too few scenarios"


def test_summarize_judging_keeps_all_error_challenger_visible():
    verdicts = [
        _verdict(winner="challenger"),
        _verdict(challenger="gpt-5.6-terra:none", run_index=1, winner="error"),
        _verdict(challenger="gpt-5.6-terra:none", run_index=2, winner="error"),
    ]

    summary = summarize_judging(verdicts)

    # An outage must not be indistinguishable from never being judged.
    row = summary["gpt-5.6-terra:none"]
    assert row["errors"] == 2
    assert row["n"] == 0
    assert row["win_rate"] is None
    assert row["read"] == "all judge calls errored"


def test_markdown_summary_renders_error_only_challenger():
    from game.devtools.model_eval import format_markdown_summary

    verdicts = [
        _verdict(scenario_id=f"s{s}", run_index=r, winner="challenger")
        for s in range(3)
        for r in range(1, 4)
    ] + [_verdict(challenger="gpt-5.6-terra:none", winner="error")]

    markdown = format_markdown_summary([], [], [], (), verdicts)

    assert "## Judge win-rates vs incumbent" in markdown
    assert "all judge calls errored" in markdown
    assert "gpt-5.6-terra:none" in markdown


def test_judge_payload_includes_world_contents():
    from game.devtools.model_eval import ROUND5_PROSE_SCENARIOS, build_judge_messages

    scenario = next(
        s for s in ROUND5_PROSE_SCENARIOS if s.scenario_id == "near_death_apology"
    )
    import json as json_module

    payload = json_module.loads(build_judge_messages(scenario, "a", "b")[1]["content"])

    situation = payload["situation"]
    # The rubric penalises confirming things not in the world, so the judge
    # must be told what is: the figure at the reunion is in room_items.
    assert "nika" in situation["present_in_room"]
    assert situation["exits"]
    assert situation["reunion_stage"]


def test_judge_agreement_counts_matching_verdicts():
    verdicts = [
        _verdict(judge="judge:gpt-5.5", winner="challenger"),
        _verdict(judge="judge:claude-sonnet-5", winner="challenger"),
        _verdict(judge="judge:gpt-5.5", run_index=2, winner="challenger"),
        _verdict(judge="judge:claude-sonnet-5", run_index=2, winner="incumbent"),
    ]

    assert judge_agreement(verdicts) == 0.5


def test_seed_context_raises_on_unknown_room():
    import pytest

    with pytest.raises(ValueError, match="Unknown room_id"):
        _seed_context("act3_seated", room_id="not_a_real_room")


def test_seed_context_matches_engine_shape():
    context = _seed_context("act3_seated", fear=48)

    assert context["world_flags"]["world_layer"] == "wrong"
    assert context["fear"] == 48
    assert "room_id" in context
    assert "allowed_actions" in context
    # Wrong-layer fixtures are visible.
    assert "nika" in context["room_items"]


def test_act5_scenario_context_has_live_offer():
    act5 = next(s for s in STORY_SCENARIOS if s.scenario_id == "act5_accept_mug")

    assert _act_v_offer_active(act5.context)
    assert act5.expected_action == "accept"


def test_act5_inactive_scenario_has_no_offer():
    inactive = next(s for s in STORY_SCENARIOS if s.scenario_id == "act5_offer_inactive")

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
    assert not by_id["act5_accept_mug"].judge_eligible


def test_score_response_accepts_alternate_actions():
    scenario = EvalScenario(
        scenario_id="two_answers",
        user_input="give me a hint",
        context=_base_context(),
        expected_action="none",
        accepted_actions=("help",),
    )
    reply = {"reply": "The cold offers nothing. The dark keeps its own counsel."}

    canonical = score_response({"action": "none", **reply}, "", scenario)
    alternate = score_response({"action": "help", **reply}, "", scenario)
    wrong = score_response({"action": "move", **reply}, "", scenario)

    assert canonical["action_match"] == 1.0
    assert alternate["action_match"] == 1.0
    assert wrong["action_match"] == 0.0


def test_meta_bait_hint_accepts_help_routing():
    by_id = {scenario.scenario_id: scenario for scenario in DEFAULT_SCENARIOS}

    assert "help" in by_id["meta_bait_hint"].accepted_action_set
    # Canonical answer unchanged, so the scenario is still judged for prose.
    assert by_id["meta_bait_hint"].expected_action == "none"
    assert by_id["meta_bait_hint"].judge_eligible


def test_round5_prose_scenarios_are_all_judge_eligible():
    assert len(ROUND5_PROSE_SCENARIOS) >= 3
    for scenario in ROUND5_PROSE_SCENARIOS:
        assert scenario.judge_eligible, scenario.scenario_id
    ids = {scenario.scenario_id for scenario in DEFAULT_SCENARIOS}
    assert "wrong_layer_her_hands" in ids
    assert "act4_window_question" in ids
    # Uniqueness across the merged slate.
    assert len(ids) == len(DEFAULT_SCENARIOS)


def test_round5_seeded_scenarios_use_real_wrong_layer_state():
    by_id = {scenario.scenario_id: scenario for scenario in ROUND5_PROSE_SCENARIOS}

    seated = by_id["wrong_layer_her_hands"].context
    night = by_id["act4_window_question"].context
    assert seated["world_flags"]["world_layer"] == "wrong"
    assert night["world_flags"]["world_layer"] == "wrong"
    assert by_id["near_death_apology"].context["fear"] == 98


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
