"""Authored story beats own their complete outcome across Acts I-V."""

from unittest import mock

import pytest

from game import turn
from game.actions import create_default_registry
from game.ai_interpreter import Intent
from game.events import EventBus
from game.map import Map
from game.player import Player
from game.story import AnomalyID, log_tell


def _run_turn(game_map: Map, player: Player, intent: Intent) -> str:
    feedback = []
    with mock.patch("game.turn.build_ai_context", return_value={}), mock.patch(
        "game.turn.interpret", return_value=intent
    ):
        turn.take_turn(
            "story action",
            player=player,
            game_map=game_map,
            quest_manager=mock.MagicMock(),
            action_registry=create_default_registry(),
            event_bus=EventBus(),
            set_feedback=feedback.append,
        )
    return feedback[-1]


def _assert_model_effect_blocked(game_map: Map, player: Player, intent: Intent) -> str:
    proposed_effects = {"health": -2}
    intent.effects = proposed_effects
    health_before = player.health

    feedback = _run_turn(game_map, player, intent)

    assert player.health == health_before
    assert intent.effects is proposed_effects
    return feedback


def _act_i_evidence() -> Map:
    game_map = Map()
    game_map.current_location_id = "cabin_interior"
    game_map.current_room_id = "konttori"
    return game_map


def _act_ii_observation() -> Map:
    game_map = Map()
    game_map.current_location_id = "cabin_grounds"
    game_map.current_room_id = "cabin_grounds_main"
    game_map.world_state.first_morning = True
    return game_map


def _wrong_cabin(reunion_stage: str | None = None) -> Map:
    game_map = Map()
    game_map.current_location_id = "cabin_interior"
    game_map.current_room_id = "cabin_main"
    game_map.world_state.enter_wrong_layer()
    if reunion_stage is not None:
        game_map.world_state.reunion_stage = reunion_stage
    return game_map


def _act_v_dawn_choice() -> Map:
    game_map = _wrong_cabin("dawn")
    game_map.world_state.recognition = True
    for anomaly in (
        AnomalyID.MEMORY_ALOUD,
        AnomalyID.BREATHING_TIDE,
        AnomalyID.PHONE_DARK,
        AnomalyID.WRONG_TINS,
    ):
        log_tell(game_map.world_state, anomaly)
    return game_map


def _act_v_walk_out() -> Map:
    game_map = _wrong_cabin("dawn")
    game_map.world_state.ending = "escaped"
    return game_map


AUTHORED_BEATS = [
    pytest.param(
        _act_i_evidence,
        Intent(action="use", args={"item": "camera feed"}, confidence=1.0),
        "Five frames",
        lambda m: m.world_state.footage_reviewed is True,
        id="act-i-evidence",
    ),
    pytest.param(
        _act_ii_observation,
        Intent(action="look", args={}, confidence=1.0),
        "fox",
        lambda m: m.world_state.wrongness.has(AnomalyID.FOX_TRACKS.value),
        id="act-ii-observation",
    ),
    pytest.param(
        _wrong_cabin,
        Intent(action="use", args={"item": "nika"}, confidence=1.0),
        "Look at me",
        lambda m: m.world_state.reunion_stage == "tended",
        id="act-iii-reunion",
    ),
    pytest.param(
        lambda: _wrong_cabin("consented"),
        Intent(action="use", args={"item": "mattress"}, confidence=1.0),
        "Night, Elli",
        lambda m: m.world_state.reunion_stage == "bedded",
        id="act-iv-night-beat",
    ),
    pytest.param(
        _act_v_dawn_choice,
        Intent(action="refuse", args={}, confidence=1.0),
        '"No," you say.',
        lambda m: m.world_state.ending == "escaped",
        id="act-v-dawn-choice",
    ),
    pytest.param(
        _act_v_walk_out,
        Intent(action="move", args={"direction": "out"}, confidence=1.0),
        "without any interest",
        lambda m: m.current_room_id == "cabin_clearing",
        id="act-v-walk-out",
    ),
]


@pytest.mark.parametrize(
    ("make_map", "intent", "expected_prose", "beat_landed"), AUTHORED_BEATS
)
def test_authored_beat_blocks_model_effects_without_mutating_intent(
    make_map, intent, expected_prose, beat_landed
):
    """Every authored beat owns its outcome: the model's proposed effects are
    dropped (not applied, and not scrubbed from the intent), the authored prose
    is what the player reads, and the beat's own state change lands."""
    game_map = make_map()
    player = Player()

    feedback = _assert_model_effect_blocked(game_map, player, intent)

    assert expected_prose in feedback
    assert beat_landed(game_map)


def test_generic_action_still_applies_permitted_model_effects():
    game_map = Map()
    game_map.current_location_id = "cabin_grounds"
    game_map.current_room_id = "cabin_clearing"
    player = Player()
    proposed_effects = {"health": -2}
    intent = Intent(
        action="use",
        args={"item": "rope"},
        confidence=1.0,
        reply="You draw the rope through your hands. The fibres rasp your gloves.",
        effects=proposed_effects,
    )

    feedback = _run_turn(game_map, player, intent)

    assert feedback == intent.reply
    assert player.health == 98
    assert intent.effects is proposed_effects
