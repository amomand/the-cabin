"""Compatibility contracts for the ``game.ai_interpreter`` facade."""

import hashlib
import json

import game.ai_interpreter as ai_interpreter


def _prompt_contexts():
    return [
        (
            "look around",
            {
                "room_name": "The Cabin",
                "room_id": "cabin_main",
                "exits": ["north", "out"],
                "room_items": ["matches"],
                "carryable_room_items": ["matches"],
                "inventory": ["key"],
                "world_flags": {"has_power": False},
                "can_advance_to_dawn": False,
                "is_dawn_offer_active": False,
                "fear": 10,
                "health": 100,
                "rooms_visited": 2,
                "been_here_before": False,
                "active_quest": None,
            },
            "b8ff17c90ea3ff7a4f4c6aaa10af74fd36b954679e6b511003331b14e193fd58",
        ),
        (
            "no thank you",
            {
                "room_name": "The Cabin",
                "room_id": "cabin_main",
                "exits": ["out"],
                "room_items": ["Nika", "mug"],
                "carryable_room_items": [],
                "inventory": [],
                "world_flags": {
                    "world_layer": "wrong",
                    "ending": "none",
                    "reunion_stage": "dawn",
                },
                "can_advance_to_dawn": False,
                "is_dawn_offer_active": True,
                "fear": 80,
                "health": 35,
                "rooms_visited": 12,
                "been_here_before": True,
                "active_quest": "Choose what remains",
            },
            "c5e317910e53a4742627e1bf887c30186dee95753ec618c0c4cf403db10c160e",
        ),
    ]


def test_prompt_template_bytes_are_unchanged():
    prompt_bytes = ai_interpreter._SYSTEM_PROMPT_TEMPLATE.encode()

    assert len(prompt_bytes) == 4939
    assert hashlib.sha256(prompt_bytes).hexdigest() == (
        "9298aa27cf1f9553cdaca0ff646685aea2b6ac3d90cb91b3a0c8342dd90d1d3c"
    )


def test_prompt_messages_are_unchanged_across_runtime_contexts():
    for user_text, context, expected_hash in _prompt_contexts():
        messages = ai_interpreter.build_interpreter_messages(user_text, context)
        payload = json.dumps(
            messages,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()

        assert hashlib.sha256(payload).hexdigest() == expected_hash


def test_facade_keeps_public_and_test_harness_seams():
    expected_names = {
        "ALLOWED_ACTIONS",
        "Intent",
        "OpenAI",
        "_get_openai_client",
        "_make_cache_key",
        "_cache_get",
        "_cache_put",
        "_response_cache",
        "_rule_based",
        "_sanitize_diegetic_reply",
        "build_interpreter_messages",
        "build_openai_chat_params",
        "clear_response_cache",
        "interpret",
        "log_ai_call",
        "make_openai_params_compatible",
    }

    assert expected_names <= set(vars(ai_interpreter))
    assert ai_interpreter.Intent.__module__ == "game.ai_interpreter"


def test_facade_client_cache_remains_patchable(monkeypatch):
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
        },
        {
            "api_key": "second-key",
            "timeout": ai_interpreter.OPENAI_TIMEOUT_SECONDS,
        },
    ]
