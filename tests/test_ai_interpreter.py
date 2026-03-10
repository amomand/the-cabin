"""Regression tests for AI interpreter context hashing."""

import pytest

from game.ai_interpreter import _make_cache_key


def _base_context():
    return {
        "room_name": "The Cabin",
        "exits": ["north", "out"],
        "room_items": ["matches"],
        "room_wildlife": [],
        "inventory": ["key"],
        "world_flags": {"has_power": False},
        "fear": 10,
        "health": 100,
        "rooms_visited": 2,
        "been_here_before": False,
        "active_quest": None,
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("room_wildlife", ["owl"]),
        ("rooms_visited", 5),
        ("been_here_before", True),
        ("active_quest", "Restore power to the cabin"),
    ],
)
def test_cache_key_changes_when_prompt_context_changes(field, value):
    """Prompt-affecting context changes should invalidate cached replies."""
    base_context = _base_context()
    changed_context = dict(base_context)
    changed_context[field] = value

    assert _make_cache_key("wait", base_context) != _make_cache_key("wait", changed_context)
