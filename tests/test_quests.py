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
    lake must no longer arm the survival quest. Activation is carried by
    entering the cold cabin, not by wandering into the room the fuel is in.
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


def test_entering_the_cold_cabin_activates_warm_up():
    """The cold room is what opens the quest.

    Walking in is the only beat that precedes both halves of the objective, so
    it is the only one that can carry the opening overlay without describing a
    cabin state the player has already changed.
    """
    manager = _manager()
    triggered = manager.check_triggers(
        "location", {"room_id": "cabin_main"}, Player(), {}
    )
    assert triggered is not None
    assert triggered.quest_id == "warm_up"


def test_the_cold_hearth_also_activates_warm_up():
    """`use_fireplace` reaches a trigger check only from the no-fuel failure
    path, which is the cabin refusing her rather than answering her."""
    manager = _manager()
    triggered = manager.check_triggers(
        "action", {"action": "use_fireplace"}, Player(), {}
    )
    assert triggered is not None
    assert triggered.quest_id == "warm_up"


def test_success_actions_do_not_activate_warm_up():
    """A beat that completes half the quest must never open it (#186).

    The quest listener runs `_check_triggers` on the success paths too, so
    listing `light_fire` or `turn_on_lights` as trigger conditions made
    restoring power print an overlay saying the lights don't respond.
    """
    for action in ("light_fire", "turn_on_lights"):
        manager = _manager()
        triggered = manager.check_triggers(
            "action", {"action": action}, Player(), {}
        )
        assert triggered is None, f"{action} should not open the quest"


def test_dead_action_strings_are_not_trigger_conditions():
    """`use_light_switch` and `use_circuit_breaker` are not listed as triggers.

    The quest listener never passes those action values to a *trigger* check.
    (`use_circuit_breaker` is still used, but only as the action on the
    `power_restored` *update*.) Carrying them as trigger conditions was dead and
    misleading, so they are gone.
    """
    manager = _manager()
    for action in ("use_light_switch", "use_circuit_breaker"):
        triggered = manager.check_triggers(
            "action", {"action": action}, Player(), {}
        )
        assert triggered is None, f"{action} should not be a trigger condition"


def test_completed_status_is_not_re_armed_by_an_action():
    """A quest already marked COMPLETED is not re-armed by a matching action.

    This covers only the in-memory guard in `check_triggers` (status must be
    INACTIVE to trigger). Restoring that COMPLETED status across a save/load is
    a separate persistence concern handled in the load path, not asserted here.
    """
    manager = _manager()
    warm_up = manager.quests["warm_up"]
    warm_up.status = QuestStatus.COMPLETED

    triggered = manager.check_triggers(
        "action", {"action": "light_fire"}, Player(), {}
    )
    assert triggered is None
