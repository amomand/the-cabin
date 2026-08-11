"""Authored story beats own their complete outcome across Acts I-V."""

from unittest import mock

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


def test_act_i_evidence_blocks_model_effects_without_mutating_intent():
    game_map = Map()
    game_map.current_location_id = "cabin_interior"
    game_map.current_room_id = "konttori"
    player = Player()

    feedback = _assert_model_effect_blocked(
        game_map,
        player,
        Intent(action="use", args={"item": "camera feed"}, confidence=1.0),
    )

    assert "Five frames" in feedback
    assert game_map.world_state.footage_reviewed is True


def test_act_ii_observation_blocks_model_effects():
    game_map = Map()
    game_map.current_location_id = "cabin_grounds"
    game_map.current_room_id = "cabin_grounds_main"
    game_map.world_state.first_morning = True
    player = Player()

    feedback = _assert_model_effect_blocked(
        game_map,
        player,
        Intent(action="look", args={}, confidence=1.0),
    )

    assert "fox" in feedback.lower()
    assert game_map.world_state.wrongness.has(AnomalyID.FOX_TRACKS.value)


def test_act_iii_reunion_blocks_model_effects():
    game_map = Map()
    game_map.current_location_id = "cabin_interior"
    game_map.current_room_id = "cabin_main"
    game_map.world_state.enter_wrong_layer()
    player = Player()

    feedback = _assert_model_effect_blocked(
        game_map,
        player,
        Intent(action="use", args={"item": "nika"}, confidence=1.0),
    )

    assert "Look at me" in feedback
    assert game_map.world_state.reunion_stage == "tended"


def test_act_iv_night_beat_blocks_model_effects():
    game_map = Map()
    game_map.current_location_id = "cabin_interior"
    game_map.current_room_id = "cabin_main"
    game_map.world_state.enter_wrong_layer()
    game_map.world_state.reunion_stage = "consented"
    player = Player()

    feedback = _assert_model_effect_blocked(
        game_map,
        player,
        Intent(action="use", args={"item": "mattress"}, confidence=1.0),
    )

    assert "Night, Elli" in feedback
    assert game_map.world_state.reunion_stage == "bedded"


def test_act_v_dawn_choice_blocks_model_effects():
    game_map = Map()
    game_map.current_location_id = "cabin_interior"
    game_map.current_room_id = "cabin_main"
    game_map.world_state.enter_wrong_layer()
    game_map.world_state.reunion_stage = "dawn"
    game_map.world_state.recognition = True
    for anomaly in (
        AnomalyID.MEMORY_ALOUD,
        AnomalyID.BREATHING_TIDE,
        AnomalyID.PHONE_DARK,
        AnomalyID.WRONG_TINS,
    ):
        log_tell(game_map.world_state, anomaly)
    player = Player()

    feedback = _assert_model_effect_blocked(
        game_map,
        player,
        Intent(action="refuse", args={}, confidence=1.0),
    )

    assert '"No," you say.' in feedback
    assert game_map.world_state.ending == "escaped"


def test_act_v_walk_out_blocks_model_effects():
    game_map = Map()
    game_map.current_location_id = "cabin_interior"
    game_map.current_room_id = "cabin_main"
    game_map.world_state.enter_wrong_layer()
    game_map.world_state.reunion_stage = "dawn"
    game_map.world_state.ending = "escaped"
    player = Player()

    feedback = _assert_model_effect_blocked(
        game_map,
        player,
        Intent(action="move", args={"direction": "out"}, confidence=1.0),
    )

    assert "without any interest" in feedback
    assert game_map.current_room_id == "cabin_clearing"


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
