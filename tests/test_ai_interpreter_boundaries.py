"""Behavioural contracts for the ``game.ai_interpreter`` facade."""

import pytest

import game.ai_interpreter as ai_interpreter


def test_facade_client_cache_reuses_client_per_api_key(monkeypatch):
    created = []

    def fake_openai(**kwargs):
        client = object()
        created.append((kwargs, client))
        return client

    monkeypatch.setattr(ai_interpreter, "OpenAI", fake_openai)
    monkeypatch.setattr(ai_interpreter, "_openai_client", None)
    monkeypatch.setattr(ai_interpreter, "_openai_client_key", None)

    first = ai_interpreter._get_openai_client("first-key")
    repeated = ai_interpreter._get_openai_client("first-key")
    second = ai_interpreter._get_openai_client("second-key")

    assert first is repeated
    assert second is not first
    assert [entry[0] for entry in created] == [
        {
            "api_key": "first-key",
            "timeout": ai_interpreter.OPENAI_TIMEOUT_SECONDS,
            "max_retries": 0,
        },
        {
            "api_key": "second-key",
            "timeout": ai_interpreter.OPENAI_TIMEOUT_SECONDS,
            "max_retries": 0,
        },
    ]


@pytest.mark.parametrize("model_fails", [False, True])
@pytest.mark.parametrize("text, action", [("north", "move"), ("dance", "none")])
def test_fallback_preserves_invalid_move_confidence_and_is_not_cached(
    monkeypatch, model_fails, text, action,
):
    ai_interpreter.clear_response_cache()
    logs = []
    monkeypatch.setattr(ai_interpreter, "log_ai_call", lambda *args: logs.append(args))
    if model_fails:
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setattr(ai_interpreter, "OpenAI", object())

        def unavailable_client(_):
            raise RuntimeError("unavailable")

        monkeypatch.setattr(ai_interpreter, "_get_openai_client", unavailable_client)

    first = ai_interpreter.interpret(text, {"exits": []})
    second = ai_interpreter.interpret(text, {"exits": []})

    assert first == second
    assert first.action == action
    assert first.effects is None
    assert len(logs) == 2  # A cached result would bypass fallback logging.
    if action == "move":
        assert first.args == {"direction": "north"}
        assert first.confidence == 0.5
    else:
        assert first.confidence == 0.0
        assert first.rationale == ("fallback-error" if model_fails else "fallback-no-model")
    assert logs[0][3] == (
        "API call failed: unavailable" if model_fails
        else "No model path - using rule-based fallback" if action == "move"
        else "No model path - no rule match"
    )
