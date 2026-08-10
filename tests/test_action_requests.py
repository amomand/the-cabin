"""Contract tests for the typed action-to-turn boundary."""

import pytest

from game.actions.base import ActionResult
from game.events.requests import ItemTakenRequest, PlayerMovedRequest


def test_required_event_payload_cannot_be_omitted() -> None:
    with pytest.raises(TypeError):
        PlayerMovedRequest(from_room_id="path", to_room_id="cabin")

    with pytest.raises(TypeError):
        ItemTakenRequest(item_name="firewood")


def test_action_result_rejects_the_old_string_protocol() -> None:
    with pytest.raises(TypeError, match="Unsupported turn request type: str"):
        ActionResult.success_result("moved", requests=["player_moved"])
