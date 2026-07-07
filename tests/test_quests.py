"""Tests for the Warm Up quest trigger conditions."""
from __future__ import annotations

from game.player import Player
from game.quest import QuestStatus
from game.quests import create_quest_manager


def _manager():
    return create_quest_manager()


def test_entering_lakeside_does_not_activate_warm_up():
    """The stale lakeside location trigger is gone.

    Firewood moved from the lakeside to the cabin grounds, so walking to the
    lake must no longer arm the survival quest. Activation is carried entirely
    by the power/warmth action triggers.
    """
    manager = _manager()
    triggered = manager.check_triggers(
        "location", {"room_id": "lakeside"}, Player(), {}
    )
    assert triggered is None


def test_entering_cabin_grounds_does_not_activate_warm_up():
    """The trigger was dropped, not re-pointed at the firewood's new room.

    Guards against re-coupling quest activation to wherever the firewood item
    happens to live.
    """
    manager = _manager()
    triggered = manager.check_triggers(
        "location", {"room_id": "cabin_grounds_main"}, Player(), {}
    )
    assert triggered is None


def test_action_triggers_activate_warm_up():
    """Each power/warmth action the listener emits arms the quest."""
    for action in ("light_fire", "turn_on_lights", "use_fireplace"):
        manager = _manager()
        triggered = manager.check_triggers(
            "action", {"action": action}, Player(), {}
        )
        assert triggered is not None, f"{action} should activate Warm Up"
        assert triggered.quest_id == "warm_up"


def test_dead_action_strings_are_not_trigger_conditions():
    """`use_light_switch` and `use_circuit_breaker` are not listed as triggers.

    The quest listener never emits those action values; using the light switch
    or the circuit breaker reaches the quest through the `turn_on_lights` action
    it does emit. Carrying them as trigger conditions was dead and misleading,
    so they are gone.
    """
    manager = _manager()
    for action in ("use_light_switch", "use_circuit_breaker"):
        triggered = manager.check_triggers(
            "action", {"action": action}, Player(), {}
        )
        assert triggered is None, f"{action} should not be a trigger condition"


def test_completed_warm_up_does_not_retrigger():
    """A completed quest stays completed even when a live trigger fires."""
    manager = _manager()
    warm_up = manager.quests["warm_up"]
    warm_up.status = QuestStatus.COMPLETED

    triggered = manager.check_triggers(
        "action", {"action": "light_fire"}, Player(), {}
    )
    assert triggered is None
