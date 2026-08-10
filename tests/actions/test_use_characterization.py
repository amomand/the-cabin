"""Characterization coverage for the UseAction decomposition boundary."""

from unittest.mock import MagicMock

import pytest

from game.actions import UseAction, create_default_registry
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


def test_use_action_remains_the_registry_facing_api():
    action = create_default_registry().get("use")

    assert isinstance(action, UseAction)
    assert action.name == "use"


@pytest.mark.parametrize(
    ("has_firewood", "expected_feedback", "expected_request"),
    [
        (
            True,
            "The kindling is laid. You need the matches.",
            FireplaceUsedRequest(has_fuel=True),
        ),
        (
            False,
            "The grate is bare. Flame would have nothing to take.",
            FireplaceUsedRequest(has_fuel=False),
        ),
    ],
)
def test_fireplace_preserves_fuel_payload_and_authored_policy(
    has_firewood, expected_feedback, expected_request
):
    ctx = _mock_context("fireplace", has_firewood=has_firewood)

    result = UseAction().execute(ctx)

    assert result.feedback == expected_feedback
    assert result.requests == (expected_request,)
    assert result.model_effects is ModelEffectsPolicy.BLOCK


def test_sauna_reuse_keeps_the_first_use_state_unchanged():
    ctx = _mock_context("sauna stove")
    ctx.world_state.sauna_used = True

    result = UseAction().execute(ctx)

    assert result.feedback == (
        "The stones still hold their heat. Steam lifts from the ladle and is gone."
    )
    assert ctx.world_state.sauna_used is True


@pytest.mark.parametrize(
    ("fire_lit", "has_power", "expected_feedback"),
    [
        (
            False,
            True,
            "The hook is empty. The cupboard can wait until the cabin is warm.",
        ),
        (
            True,
            False,
            "The hook is empty. The cupboard can wait until the cabin is warm.",
        ),
        (
            True,
            True,
            "The white enamel mug is yours, brought from Rovaniemi. It has no chip.",
        ),
    ],
)
def test_real_cabin_mug_keeps_its_warmth_gate(
    fire_lit, has_power, expected_feedback
):
    game_map = _real_cabin_map()
    game_map.world_state.fire_lit = fire_lit
    game_map.world_state.has_power = has_power

    result = UseAction().execute(_ctx_for_use(game_map, "mug"))

    assert result.feedback == expected_feedback
    assert result.model_effects is ModelEffectsPolicy.APPLY


@pytest.mark.parametrize(
    ("stage", "expected_feedback"),
    [
        (
            "seated",
            "Nika nods at the mug. \"Drink. Then tell me.\" The order is "
            "familiar enough that you obey it without yet moving.",
        ),
        (
            "consented",
            "\"First light,\" she says again, without looking up from the "
            "fire. \"Sleep first.\" The spare mattress is already down by "
            "the narrow bed.",
        ),
        (
            "bedded",
            "She lies between you and the door, where she has always lived. "
            "You keep your own breath slow and say nothing into the dark.",
        ),
        (
            "night",
            "She lies between you and the door, where she has always lived. "
            "You keep your own breath slow and say nothing into the dark.",
        ),
        (
            "dawn",
            "It holds the mug out to you. The face makes Nika's morning "
            "face and keeps making it. \"You'll want something in you,\" it "
            "says. Nika's cadence, exact. \"It's a long walk on the compass.\"",
        ),
    ],
)
def test_nika_non_transition_stages_keep_their_exact_narration(
    stage, expected_feedback
):
    game_map = _wrong_cabin_map(stage)

    result = UseAction().execute(_ctx_for_use(game_map, "nika"))

    assert result.feedback == expected_feedback
    assert game_map.world_state.reunion_stage == stage


def test_nika_is_absent_in_the_real_cabin():
    result = UseAction().execute(_ctx_for_use(_real_cabin_map(), "nika"))

    assert result.feedback == "Nika isn't here."


def test_nika_after_refusal_is_not_named_as_nika():
    game_map = _wrong_cabin_map("dawn")
    game_map.world_state.ending = "escaped"

    result = UseAction().execute(_ctx_for_use(game_map, "nika"))

    assert result.feedback == (
        "You do not look at what is standing by the stove in Nika's "
        "fleece. Whatever is under the face has never once been shown to "
        "you. You keep it that way."
    )


@pytest.mark.parametrize(
    ("stage", "expected_feedback"),
    [
        (
            "bedded",
            "You are already under the covers. Nika lies on the mattress "
            "below, between you and the door.",
        ),
        (
            "night",
            "You are already under the covers. Nika lies on the mattress "
            "below, between you and the door.",
        ),
        (
            "arrival",
            "The chest sits where it has always sat. Sleep is not the shape "
            "of this hour yet.",
        ),
    ],
)
def test_wrong_cabin_mattress_non_transition_paths_are_stable(
    stage, expected_feedback
):
    game_map = _wrong_cabin_map(stage)

    result = UseAction().execute(_ctx_for_use(game_map, "mattress"))

    assert result.feedback == expected_feedback
    assert game_map.world_state.reunion_stage == stage


def test_real_cabin_mattress_remains_generic_observation():
    result = UseAction().execute(_ctx_for_use(_real_cabin_map(), "mattress"))

    assert result.feedback == (
        "The chest holds the spare mattress it has always held. "
        "No reason to drag it out now."
    )
    assert result.model_effects is ModelEffectsPolicy.APPLY


@pytest.mark.parametrize(
    ("game_map", "expected_feedback", "expected_policy"),
    [
        (
            _real_cabin_map(),
            "Tinned food in the cupboard. Yours, bought in Rovaniemi.",
            ModelEffectsPolicy.APPLY,
        ),
        (
            _wrong_cabin_map("complete"),
            "Tins, stacked by the stove. Dinner made from them was better than "
            "you would have made of them. You let the thought pass.",
            ModelEffectsPolicy.BLOCK,
        ),
    ],
)
def test_tins_outside_the_night_seam_are_stable(
    game_map, expected_feedback, expected_policy
):
    result = UseAction().execute(_ctx_for_use(game_map, "tins"))

    assert result.feedback == expected_feedback
    assert result.model_effects is expected_policy


def test_repeated_coda_phone_call_does_not_advance_state_again():
    game_map = _real_cabin_map()
    game_map.world_state.ending = "escaped"
    game_map.world_state.coda_stage = "called"

    result = UseAction().execute(_ctx_for_use(game_map, "phone"))

    assert result.feedback == (
        "The call is made. The shop, the coffee, the road past the "
        "lake. The phone has done what it can do."
    )
    assert game_map.world_state.coda_stage == "called"


def test_generic_fixture_prefers_ai_reply_without_requests_or_authored_policy():
    ctx = _mock_context("stone", ai_reply="The stone sits cold in your palm.")

    result = UseAction().execute(ctx)

    assert result.feedback == "The stone sits cold in your palm."
    assert result.requests == ()
    assert result.model_effects is ModelEffectsPolicy.APPLY
