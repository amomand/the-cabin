"""Tests for action result construction contracts."""

from dataclasses import FrozenInstanceError

import pytest

from game.actions.base import ActionResult
from game.events.requests import PowerRestoredRequest


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


class FalseyRequests:
    def __bool__(self):
        return False

    def __iter__(self):
        yield PowerRestoredRequest()


@pytest.mark.parametrize(
    "factory",
    [ActionResult.success_result, ActionResult.authored],
)
def test_result_factories_consume_falsey_request_iterables(factory):
    result = factory("Power moves.", requests=FalseyRequests())

    assert result.requests == (PowerRestoredRequest(),)


@pytest.mark.parametrize("unsupported", ["", 0, False])
@pytest.mark.parametrize(
    "factory",
    [ActionResult.success_result, ActionResult.authored],
)
def test_result_factories_reject_falsey_non_request_values(factory, unsupported):
    with pytest.raises(TypeError):
        factory("Nothing moves.", requests=unsupported)


def test_action_result_requests_cannot_be_rebound_after_validation():
    result = ActionResult.success_result(
        "Power moves.",
        requests=[PowerRestoredRequest()],
    )

    with pytest.raises(FrozenInstanceError):
        result.requests = (PowerRestoredRequest(), "legacy-label")
