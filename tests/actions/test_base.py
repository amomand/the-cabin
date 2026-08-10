"""Tests for action result construction contracts."""

import pytest

from game.actions.base import ActionResult


@pytest.mark.parametrize(
    "factory",
    [ActionResult.success_result, ActionResult.authored],
)
def test_result_factories_freeze_explicit_empty_request_iterables(factory):
    requests = []

    result = factory(
        "Nothing moves.",
        requests=requests,
    )

    assert result.requests == ()
    requests.append(object())
    assert result.requests == ()
