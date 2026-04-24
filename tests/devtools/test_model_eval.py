from game.ai_interpreter import (
    build_interpreter_messages,
    build_openai_chat_params,
    make_openai_params_compatible,
)
from game.devtools.model_eval import (
    EvalResult,
    EvalScenario,
    _base_context,
    parse_model_spec,
    parse_model_specs,
    score_response,
    summarize,
)


def test_parse_model_spec_defaults_to_openai():
    spec = parse_model_spec("gpt-5-mini:low")

    assert spec.provider == "openai"
    assert spec.model == "gpt-5-mini"
    assert spec.reasoning_effort == "low"


def test_parse_model_spec_accepts_provider_prefix():
    spec = parse_model_spec("openai:gpt-5.4-mini:none")

    assert spec.provider == "openai"
    assert spec.model == "gpt-5.4-mini"
    assert spec.reasoning_effort == "none"


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
    assert scores["tone"] > 0.8
    assert scores["interesting"] > 0.6


def test_summarize_groups_model_and_reasoning_effort():
    result = EvalResult(
        model="gpt-5-mini",
        provider="openai",
        reasoning_effort="low",
        scenario_id="sample",
        run_index=1,
        user_input="wait",
        latency_ms=123.0,
        ok=True,
        raw_output="{}",
        parsed={},
        scores={
            "overall": 0.5,
            "tone": 0.6,
            "interesting": 0.7,
            "action_match": 1.0,
            "effects_present": 1.0,
        },
        errors=[],
    )

    rows = summarize([result])

    assert rows[0]["model"] == "gpt-5-mini:low"
    assert rows[0]["avg_latency_ms"] == 123.0
