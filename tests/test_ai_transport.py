"""Retry and deadline contracts for the production model transport."""

import json
from types import SimpleNamespace

import pytest

import game.ai_interpreter as ai_interpreter
from game.ai import transport


VALID_RESPONSE = {
    "action": "none",
    "args": {},
    "confidence": 0.8,
    "reply": "You listen. The trees give nothing back.",
    "effects": {},
}


def _stream(content):
    return [
        SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content=content))]
        )
    ]


class _Completions:
    def __init__(self, outcomes):
        self.outcomes = iter(outcomes)
        self.calls = []

    def create(self, **params):
        self.calls.append(params)
        outcome = next(self.outcomes)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def _client(*outcomes):
    completions = _Completions(outcomes)
    return (
        SimpleNamespace(chat=SimpleNamespace(completions=completions)),
        completions,
    )


def _request(client):
    return transport.request_model_json(
        client,
        "gpt-5.6-terra",
        [{"role": "user", "content": "listen"}],
        reasoning_effort="none",
        debug=lambda _: None,
    )


@pytest.fixture(autouse=True)
def _no_real_retry_delay(monkeypatch):
    monkeypatch.setattr(transport, "sleep", lambda _: None)


def test_connection_failure_retries_once_and_returns_json():
    client, completions = _client(
        ConnectionResetError("stream reset"),
        _stream(json.dumps(VALID_RESPONSE)),
    )

    assert _request(client) == VALID_RESPONSE
    assert len(completions.calls) == 2
    assert all(call["timeout"] <= transport.OPENAI_TIMEOUT_SECONDS for call in completions.calls)


@pytest.mark.parametrize("status_code", [429, 500, 503])
def test_retryable_status_retries_once(status_code):
    error = RuntimeError("temporary API response")
    error.status_code = status_code
    client, completions = _client(error, _stream(json.dumps(VALID_RESPONSE)))

    assert _request(client) == VALID_RESPONSE
    assert len(completions.calls) == 2


def test_two_retryable_failures_raise_the_second_error():
    first = ConnectionError("first")
    second = ConnectionError("second")
    client, completions = _client(first, second)

    with pytest.raises(ConnectionError, match="second"):
        _request(client)
    assert len(completions.calls) == 2


@pytest.mark.parametrize("error", [TimeoutError("slow"), RuntimeError("bad request")])
def test_non_retryable_failure_is_not_retried(error):
    if isinstance(error, RuntimeError):
        error.status_code = 400
    client, completions = _client(error, _stream(json.dumps(VALID_RESPONSE)))

    with pytest.raises(type(error)):
        _request(client)
    assert len(completions.calls) == 1


def test_openai_timeout_is_not_retried():
    request = transport._httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    error = transport._openai_mod.APITimeoutError(request=request)
    client, completions = _client(error, _stream(json.dumps(VALID_RESPONSE)))

    with pytest.raises(transport._openai_mod.APITimeoutError):
        _request(client)
    assert len(completions.calls) == 1


def test_malformed_json_retries_once_in_production_play():
    client, completions = _client(
        _stream("not json"),
        _stream(json.dumps(VALID_RESPONSE)),
    )

    assert _request(client) == VALID_RESPONSE
    assert len(completions.calls) == 2


def test_slow_first_failure_does_not_start_a_retry_past_deadline(monkeypatch):
    clock = iter([100.0, 100.0, 119.8])
    monkeypatch.setattr(transport, "monotonic", lambda: next(clock))
    client, completions = _client(
        ConnectionError("late failure"),
        _stream(json.dumps(VALID_RESPONSE)),
    )

    with pytest.raises(ConnectionError, match="late failure"):
        _request(client)
    assert len(completions.calls) == 1


def _install_interpreter_client(monkeypatch, *outcomes):
    client, completions = _client(*outcomes)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(ai_interpreter, "OpenAI", object())
    monkeypatch.setattr(ai_interpreter, "_get_openai_client", lambda _: client)
    monkeypatch.setattr(ai_interpreter, "log_ai_call", lambda *_, **__: None)
    ai_interpreter.clear_response_cache()
    return completions


def test_retry_success_returns_model_intent_without_fallback(monkeypatch):
    completions = _install_interpreter_client(
        monkeypatch,
        ConnectionResetError("stream reset"),
        _stream(json.dumps(VALID_RESPONSE)),
    )
    real_rule_based = ai_interpreter._rule_based
    rule_calls = []

    def counting_rule_based(user_text, context):
        rule_calls.append(user_text)
        return real_rule_based(user_text, context)

    monkeypatch.setattr(ai_interpreter, "_rule_based", counting_rule_based)

    intent = ai_interpreter.interpret("sing to the trees", {"room_id": "wilderness_start"})

    assert intent.reply == VALID_RESPONSE["reply"]
    assert len(completions.calls) == 2
    assert rule_calls == ["sing to the trees"]


def test_two_retryable_failures_keep_existing_fallback_rationale(monkeypatch):
    completions = _install_interpreter_client(
        monkeypatch,
        ConnectionError("first"),
        ConnectionError("second"),
    )

    intent = ai_interpreter.interpret(
        "sing to the trees",
        {"room_id": "wilderness_start"},
    )

    assert len(completions.calls) == 2
    assert intent.rationale == "fallback-error"
    assert intent.reply == "You sing one line. It comes back thin between the trunks."
