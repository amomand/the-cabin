"""Tests for action result construction contracts."""

import pytest

from game.actions.base import ActionResult


@pytest.mark.parametrize(
    "factory",
    [ActionResult.success_result, ActionResult.authored],
)
def test_result_factories_preserve_explicit_empty_containers(factory):
    events = []
    state_changes = {}

    result = factory(
        "Nothing moves.",
        events=events,
        state_changes=state_changes,
    )

    assert result.events is events
    assert result.state_changes is state_changes
