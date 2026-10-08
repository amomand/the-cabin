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
    monkeypatch.setenv("CABIN_MODEL_PROVIDER", "openai")
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
    intent = ai_interpreter.interpret("sing to the trees", {"room_id": "wilderness_start"})

    assert intent.reply == VALID_RESPONSE["reply"]
    assert len(completions.calls) == 2
    assert isinstance(intent.effects, dict)


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
    from game.ai.rules import offline_none_reply
    assert intent.reply == offline_none_reply("sing to the trees", {"room_id": "wilderness_start"})


class _HTTPResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            request = transport._httpx.Request(
                "POST", "https://api.openai.com/v1/chat/completions"
            )
            response = transport._httpx.Response(
                self.status_code, request=request
            )
            raise transport._httpx.HTTPStatusError(
                "request failed", request=request, response=response
            )

    def json(self):
        return self.payload


def _http_payload(content):
    return {"choices": [{"message": {"content": content}}]}


def test_direct_httpx_transport_posts_nonstreaming_json_without_sdk(monkeypatch):
    calls = []

    def post(url, **kwargs):
        calls.append((url, kwargs))
        return _HTTPResponse(_http_payload(json.dumps(VALID_RESPONSE)))

    monkeypatch.setattr(transport._httpx, "post", post)

    result = transport.request_model_json_httpx(
        "mobile-key",
        "gpt-5.6-terra",
        [{"role": "user", "content": "listen"}],
        reasoning_effort="none",
        debug=lambda _: None,
    )

    assert result == VALID_RESPONSE
    assert len(calls) == 1
    assert calls[0][1]["headers"]["Authorization"] == "Bearer mobile-key"
    assert calls[0][1]["json"]["stream"] is False


def test_direct_httpx_transport_retries_transient_status_once(monkeypatch):
    outcomes = iter(
        [
            _HTTPResponse({}, status_code=503),
            _HTTPResponse(_http_payload(json.dumps(VALID_RESPONSE))),
        ]
    )
    calls = []

    def post(*args, **kwargs):
        calls.append((args, kwargs))
        return next(outcomes)

    monkeypatch.setattr(transport._httpx, "post", post)

    assert transport.request_model_json_httpx(
        "mobile-key",
        "gpt-5.6-terra",
        [{"role": "user", "content": "listen"}],
        reasoning_effort="none",
        debug=lambda _: None,
    ) == VALID_RESPONSE
    assert len(calls) == 2


def test_interpreter_uses_opt_in_direct_httpx_without_openai_sdk(monkeypatch):
    monkeypatch.setenv("CABIN_MODEL_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "mobile-key")
    monkeypatch.setenv("CABIN_MODEL_TRANSPORT", "direct-httpx")
    monkeypatch.setattr(ai_interpreter, "OpenAI", None)
    monkeypatch.setattr(ai_interpreter, "log_ai_call", lambda *_, **__: None)
    monkeypatch.setattr(
        transport,
        "request_model_json_httpx",
        lambda *_, **__: VALID_RESPONSE,
    )
    ai_interpreter.clear_response_cache()

    intent = ai_interpreter.interpret(
        "sing to the trees",
        {"room_id": "wilderness_start"},
    )

    assert intent.reply == VALID_RESPONSE["reply"]


# ---------------------------------------------------------------------------
# Anthropic transport (direct httpx on every surface)


def _anthropic_payload(text, *, stop_reason="end_turn", thinking=True):
    content = []
    if thinking:
        content.append({"type": "thinking", "thinking": "", "signature": "x"})
    content.append({"type": "text", "text": text})
    return {"content": content, "stop_reason": stop_reason, "usage": {}}


def _messages():
    return [
        {"role": "system", "content": "You are the cabin.\n\nConstraints:\n- stay in world"},
        {"role": "user", "content": "listen"},
    ]


def test_build_anthropic_params_turns_thinking_off_per_model():
    sonnet = transport.build_anthropic_params("claude-sonnet-5-5", _messages(), thinking="off")
    haiku = transport.build_anthropic_params("claude-haiku-5-5", _messages(), thinking="off")

    assert sonnet["thinking"] == {"type": "between_tools"}
    assert haiku["thinking"] == {"type": "disabled"}
    assert sonnet["max_tokens"] == transport.ANTHROPIC_REPLY_MAX_TOKENS
    assert "temperature" not in sonnet
    assert sonnet["messages"] == [{"role": "user", "content": "listen"}]
    # Static prefix cached, Constraints tail not.
    assert sonnet["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert sonnet["system"][1]["text"].startswith("Constraints:")


def test_build_anthropic_params_leaves_room_for_thinking():
    low = transport.build_anthropic_params("claude-haiku-5-5", _messages(), thinking="low")

    assert low["output_config"] == {"effort": "low"}
    assert "thinking" not in low
    assert low["max_tokens"] > transport.ANTHROPIC_REPLY_MAX_TOKENS


def test_anthropic_httpx_transport_reads_text_past_thinking_and_fences(monkeypatch):
    calls = []

    def post(url, **kwargs):
        calls.append((url, kwargs))
        return _HTTPResponse(_anthropic_payload("```json\n" + json.dumps(VALID_RESPONSE) + "\n```"))

    monkeypatch.setattr(transport._httpx, "post", post)

    result = transport.request_anthropic_json_httpx(
        "mobile-key",
        "claude-sonnet-5-5",
        _messages(),
        thinking="off",
        debug=lambda _: None,
    )

    assert result == VALID_RESPONSE
    url, kwargs = calls[0]
    assert url == transport.ANTHROPIC_MESSAGES_URL
    assert kwargs["headers"]["x-api-key"] == "mobile-key"
    assert kwargs["headers"]["anthropic-version"] == transport.ANTHROPIC_VERSION
    assert "Authorization" not in kwargs["headers"]
    assert kwargs["json"]["model"] == "claude-sonnet-5-5"


def test_anthropic_httpx_transport_retries_transient_status_once(monkeypatch):
    outcomes = iter(
        [
            _HTTPResponse({}, status_code=529),
            _HTTPResponse(_anthropic_payload(json.dumps(VALID_RESPONSE))),
        ]
    )
    calls = []

    def post(*args, **kwargs):
        calls.append(args)
        return next(outcomes)

    monkeypatch.setattr(transport._httpx, "post", post)

    assert transport.request_anthropic_json_httpx(
        "k", "claude-sonnet-5-5", _messages(), thinking="off", debug=lambda _: None
    ) == VALID_RESPONSE
    assert len(calls) == 2


def test_anthropic_refusal_is_not_retried_and_falls_through(monkeypatch):
    calls = []

    def post(*args, **kwargs):
        calls.append(args)
        return _HTTPResponse(_anthropic_payload("", stop_reason="refusal", thinking=False))

    monkeypatch.setattr(transport._httpx, "post", post)

    with pytest.raises(RuntimeError, match="refusal"):
        transport.request_anthropic_json_httpx(
            "k", "claude-sonnet-5-5", _messages(), thinking="off", debug=lambda _: None
        )
    assert len(calls) == 1


def test_interpreter_defaults_to_anthropic_over_httpx(monkeypatch):
    # No provider pinned: the shipped default is Anthropic, and the OpenAI
    # SDK and key are irrelevant to it.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-key")
    monkeypatch.setattr(ai_interpreter, "OpenAI", None)
    monkeypatch.setattr(ai_interpreter, "log_ai_call", lambda *_, **__: None)
    seen = {}

    def fake_request(api_key, model, messages, *, thinking, debug):
        seen.update(api_key=api_key, model=model, thinking=thinking)
        return VALID_RESPONSE

    monkeypatch.setattr(transport, "request_anthropic_json_httpx", fake_request)
    ai_interpreter.clear_response_cache()

    intent = ai_interpreter.interpret("sing to the trees", {"room_id": "wilderness_start"})

    assert intent.action == "none"
    assert intent.reply == VALID_RESPONSE["reply"]
    assert seen == {"api_key": "anthropic-key", "model": "claude-sonnet-5-5", "thinking": "off"}


def test_interpreter_without_anthropic_key_falls_back_even_with_openai_key(monkeypatch):
    # Provider is Anthropic by default; an OpenAI key alone must not make a
    # live call anywhere.
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setattr(ai_interpreter, "OpenAI", object())
    monkeypatch.setattr(ai_interpreter, "log_ai_call", lambda *_, **__: None)
    monkeypatch.setattr(ai_interpreter, "_get_openai_client", lambda _: pytest.fail("OpenAI client requested"))
    monkeypatch.setattr(transport._httpx, "post", lambda *a, **k: pytest.fail("HTTP request attempted"))
    ai_interpreter.clear_response_cache()

    intent = ai_interpreter.interpret("sing to the trees", {"room_id": "wilderness_start"})

    assert intent.rationale == "fallback-no-model"


def test_interpreter_rejects_unknown_provider_offline(monkeypatch):
    monkeypatch.setenv("CABIN_MODEL_PROVIDER", "gemini")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.setattr(ai_interpreter, "log_ai_call", lambda *_, **__: None)
    monkeypatch.setattr(transport._httpx, "post", lambda *a, **k: pytest.fail("HTTP request attempted"))
    ai_interpreter.clear_response_cache()

    intent = ai_interpreter.interpret("sing to the trees", {"room_id": "wilderness_start"})

    assert intent.rationale == "fallback-no-model"
