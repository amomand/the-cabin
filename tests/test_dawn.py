"""Focused tests for the runtime-owned Act V dawn predicates."""

from __future__ import annotations

import pytest

from game.story import (
    AnomalyID,
    can_advance_to_dawn,
    is_dawn_offer_active,
)
from game.world_state import WorldState


def _completed_night(stage: str = "night") -> WorldState:
    state = WorldState()
    state.enter_wrong_layer()
    state.reunion_stage = stage  # type: ignore[assignment]
    state.recognition = True
    for anomaly in (
        AnomalyID.MEMORY_ALOUD,
        AnomalyID.BREATHING_TIDE,
        AnomalyID.PHONE_DARK,
        AnomalyID.MUG_IMPOSSIBLE,
    ):
        state.wrongness.add(anomaly.value)
    return state


def test_completed_night_can_advance_but_offer_is_not_yet_active():
    state = _completed_night("night")

    assert can_advance_to_dawn(state, "cabin_main") is True
    assert is_dawn_offer_active(state, "cabin_main") is False


def test_dawn_offer_is_active_only_after_the_transition():
    state = _completed_night("dawn")

    assert can_advance_to_dawn(state, "cabin_main") is False
    assert is_dawn_offer_active(state, "cabin_main") is True


@pytest.mark.parametrize(
    ("change", "value"),
    [
        ("world_layer", "real"),
        ("ending", "stayed"),
        ("recognition", False),
        ("reunion_stage", "bedded"),
    ],
)
def test_near_miss_state_cannot_advance_to_dawn(change, value):
    state = _completed_night("night")
    setattr(state, change, value)

    assert can_advance_to_dawn(state, "cabin_main") is False


@pytest.mark.parametrize(
    ("change", "value"),
    [
        ("world_layer", "real"),
        ("ending", "escaped"),
        ("recognition", False),
        ("reunion_stage", "night"),
    ],
)
def test_near_miss_state_has_no_active_offer(change, value):
    state = _completed_night("dawn")
    setattr(state, change, value)

    assert is_dawn_offer_active(state, "cabin_main") is False


@pytest.mark.parametrize("stage", ["night", "dawn"])
def test_dawn_truth_requires_the_false_cabin_room(stage):
    state = _completed_night(stage)

    assert can_advance_to_dawn(state, "konttori") is False
    assert is_dawn_offer_active(state, "konttori") is False


@pytest.mark.parametrize("stage", ["night", "dawn"])
def test_dawn_truth_rejects_recognition_without_gathered_seams(stage):
    state = _completed_night(stage)
    state.wrongness.entries.clear()

    assert can_advance_to_dawn(state, "cabin_main") is False
    assert is_dawn_offer_active(state, "cabin_main") is False


@pytest.mark.parametrize("malformed", ["yes", 1, [], {}])
@pytest.mark.parametrize(
    ("stage", "predicate"),
    [
        ("night", can_advance_to_dawn),
        ("dawn", is_dawn_offer_active),
    ],
)
def test_persisted_non_boolean_recognition_does_not_unlock_dawn(
    malformed, stage, predicate
):
    state = _completed_night(stage)
    payload = state.to_dict()
    payload["recognition"] = malformed
    loaded = WorldState.from_dict(payload)

    assert loaded.recognition == malformed
    assert predicate(loaded, "cabin_main") is False
