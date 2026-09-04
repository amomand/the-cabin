"""Behavioural coverage for UseAction handlers not exercised elsewhere."""

from unittest.mock import MagicMock

import pytest

from game.actions import UseAction
from game.actions.base import ActionContext, ModelEffectsPolicy
from game.events.requests import FireplaceUsedRequest
from game.map import Map
from game.world_state import WorldState

from tests.test_acts_3_4_5 import _ctx_for_use, _wrong_cabin_map


def _mock_context(
    item_name: str,
    *,
    has_firewood: bool = False,
    ai_reply: str | None = None,
) -> ActionContext:
    player = MagicMock()
    item = MagicMock()
    item.name = item_name
    player.get_item.return_value = item
    player.has_item.return_value = has_firewood

    game_map = MagicMock()
    game_map.current_room = MagicMock()
    game_map.world_state = WorldState()
    intent = MagicMock()
    intent.args = {"item": item_name}
    intent.reply = ai_reply
    return ActionContext(player=player, map=game_map, intent=intent)


def _real_cabin_map() -> Map:
    game_map = Map()
    game_map.current_location_id = "cabin_interior"
    game_map.current_room_id = "cabin_main"
    return game_map


@pytest.mark.parametrize(
    ("has_firewood", "expected_phrase", "expected_request"),
    [
        (True, "kindling is laid", FireplaceUsedRequest(has_fuel=True)),
        (False, "grate is bare", FireplaceUsedRequest(has_fuel=False)),
    ],
)
def test_fireplace_reports_fuel_state_and_blocks_model_effects(
    has_firewood, expected_phrase, expected_request
):
    ctx = _mock_context("fireplace", has_firewood=has_firewood)

    result = UseAction().execute(ctx)

    assert expected_phrase in result.feedback
    assert result.requests == (expected_request,)
    assert result.model_effects is ModelEffectsPolicy.BLOCK


def test_sauna_reuse_keeps_the_first_use_state_unchanged():
    ctx = _mock_context("sauna stove")
    ctx.world_state.sauna_used = True

    result = UseAction().execute(ctx)

    assert "still hold their heat" in result.feedback
    assert ctx.world_state.sauna_used is True


@pytest.mark.parametrize(
    ("fire_lit", "has_power"),
    [(False, False), (False, True), (True, False), (True, True)],
)
def test_real_cabin_mug_discovery_does_not_require_warmth_or_power(fire_lit, has_power):
    game_map = _real_cabin_map()
    game_map.world_state.fire_lit = fire_lit
    game_map.world_state.has_power = has_power

    result = UseAction().execute(_ctx_for_use(game_map, "mug"))

    assert "No blue mug" in result.feedback
    assert game_map.world_state.reopening_done
    assert result.model_effects is ModelEffectsPolicy.BLOCK
    repeated = UseAction().execute(_ctx_for_use(game_map, "mug"))
    assert "open the cupboard" not in repeated.feedback


@pytest.mark.parametrize(
    ("stage", "expected_phrase"),
    [
        ("seated", "Drink. Then tell me."),
        ("consented", "Sleep first."),
        ("night", "between you and the door"),
        ("dawn", "holds the mug out to you"),
    ],
)
def test_nika_non_transition_stages_do_not_advance(stage, expected_phrase):
    game_map = _wrong_cabin_map(stage)

    result = UseAction().execute(_ctx_for_use(game_map, "nika"))

    assert expected_phrase in result.feedback
    assert game_map.world_state.reunion_stage == stage


def test_nika_is_absent_in_the_real_cabin():
    result = UseAction().execute(_ctx_for_use(_real_cabin_map(), "nika"))

    assert result.feedback == "Nika isn't here."


def test_nika_after_refusal_is_not_named_as_nika():
    game_map = _wrong_cabin_map("dawn")
    game_map.world_state.ending = "escaped"

    result = UseAction().execute(_ctx_for_use(game_map, "nika"))

    assert "Nika's fleece" in result.feedback
    assert not result.feedback.startswith("Nika ")


@pytest.mark.parametrize(
    ("stage", "expected_phrase"),
    [
        ("night", "already under the covers"),
        ("arrival", "Sleep is not the shape of this hour yet"),
    ],
)
def test_wrong_cabin_mattress_non_transition_paths_do_not_advance(
    stage, expected_phrase
):
    game_map = _wrong_cabin_map(stage)

    result = UseAction().execute(_ctx_for_use(game_map, "mattress"))

    assert expected_phrase in result.feedback
    assert game_map.world_state.reunion_stage == stage


def test_real_cabin_mattress_remains_generic_observation():
    result = UseAction().execute(_ctx_for_use(_real_cabin_map(), "mattress"))

    assert "No reason to drag it out now" in result.feedback
    assert result.model_effects is ModelEffectsPolicy.APPLY


@pytest.mark.parametrize(
    ("game_map", "expected_phrase", "expected_policy"),
    [
        (_real_cabin_map(), "Tinned food in the cupboard", ModelEffectsPolicy.APPLY),
        (
            _wrong_cabin_map("complete"),
            "Tins, stacked by the stove",
            ModelEffectsPolicy.BLOCK,
        ),
    ],
)
def test_tins_outside_the_night_seam_are_stable(
    game_map, expected_phrase, expected_policy
):
    result = UseAction().execute(_ctx_for_use(game_map, "tins"))

    assert expected_phrase in result.feedback
    assert result.model_effects is expected_policy


def test_repeated_coda_phone_call_does_not_advance_state_again():
    game_map = _real_cabin_map()
    game_map.world_state.ending = "escaped"
    game_map.world_state.coda_stage = "called"

    result = UseAction().execute(_ctx_for_use(game_map, "phone"))

    assert "The call is made" in result.feedback
    assert game_map.world_state.coda_stage == "called"


def test_generic_fixture_prefers_ai_reply_without_requests_or_authored_policy():
    ctx = _mock_context("stone", ai_reply="The stone sits cold in your palm.")

    result = UseAction().execute(ctx)

    assert result.feedback == "The stone sits cold in your palm."
    assert result.requests == ()
    assert result.model_effects is ModelEffectsPolicy.APPLY
