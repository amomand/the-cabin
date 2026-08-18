"""Behavioural contracts for the ``game.ai_interpreter`` facade."""

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
