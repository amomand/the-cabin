"""Remaining false-evening dependencies and the coda's closed routes."""
import pytest

from game.actions.base import ActionContext, ModelEffectsPolicy
from game.actions.help import HelpAction
from game.actions.observe import LookAction, ListenAction
from game.actions.use import UseAction
from game.ai.types import Intent
from game.ai.rules import rule_based
from game.ai_context import build_ai_context
from game.devtools.seed_saves import SEEDS
from game.game_state import GameState
from game.story import AnomalyID
from game.story.equipment import EQUIPMENT


def use(state, name):
    return UseAction().execute(ActionContext(
        player=state.player, map=state.map, intent=Intent("use", {"item": name}, 1.0),
    ))


def coda_state():
    state = SEEDS['act5_dawn']()
    state.world_state.transition_ending_to('escaped')
    for direction in ('out', 'south', 'south'):
        assert state.map.move(direction, state.player).moved
    return state


@pytest.mark.parametrize('stage', ['arrival', 'tended', 'seated', 'complete'])
def test_tins_cannot_remember_dinner_until_the_meal_has_landed(stage):
    state = SEEDS['act3_arrival']()
    state.world_state.reunion_stage = stage
    before = state.world_state.to_dict()
    response = use(state, 'tins')
    assert 'Dinner made from them' not in response.feedback
    assert 'never bought' not in response.feedback
    assert state.world_state.to_dict() == before
    if stage == 'complete':
        use(state, 'mug')  # the meal and hand on the plate
        assert state.world_state.wrongness.has(AnomalyID.KNUCKLES_BIRCH.value)
        assert 'Dinner made from them' in use(state, 'tins').feedback
        description = state.current_room.get_description(state.player, state.world_state, revisit=True)
        assert 'cleared the plates' in description
        assert 'cooks at the stove' not in description


@pytest.mark.parametrize('stage, phrase', [
    ('arrival', 'last light is going'), ('dawn', 'Grey fills the window'),
])
def test_window_attention_keeps_the_hour_without_logging_an_early_tell(stage, phrase):
    state = SEEDS['act3_arrival']()
    state.world_state.reunion_stage = stage
    before = state.world_state.to_dict()
    assert phrase in use(state, 'window').feedback
    assert state.world_state.to_dict() == before


def test_coda_all_exposed_outdoor_routes_lead_home_and_cannot_reopen_exploration():
    state = coda_state()
    m = state.map
    allowed = {'cabin_grounds_main': {'cabin_main', 'cabin_clearing'}, 'cabin_clearing': {'cabin_main'}}
    for room_id, destinations in allowed.items():
        m._set_current_room_by_id(room_id)
        exits = dict(m.current_room.effective_exits(state.world_state))
        for direction, (_, target) in exits.items():
            m._set_current_room_by_id(room_id)
            moved = m.move(direction, state.player)
            assert moved.moved is (target in destinations), (room_id, direction)
            if target not in destinations:
                assert m.current_room_id == room_id
                assert 'cabin' in moved.message.lower()
    m._set_current_room_by_id('cabin_main')
    for stage, phrase in [('home', 'signal'), ('called', 'begun to pack'), ('scraping', 'scraping')]:
        state.world_state.coda_stage = stage
        for direction in ('out', 'grounds'):
            moved = m.move(direction, state.player)
            assert not moved.moved
            assert phrase in moved.message
    # Interior visits are still possible and return to the held coda.
    for direction, back in (('bedroom', 'cabin'), ('north', 'south')):
        assert m.move(direction, state.player).moved
        assert m.move(back, state.player).moved


@pytest.mark.parametrize('room_id, direction', [('old_woods', 'back'), ('deer_path', 'south'), ('wood_track', 'south'), ('sauna', 'out'), ('lakeside', 'south')])
def test_older_coda_detour_positions_can_retreat_towards_home(room_id, direction):
    state = coda_state()
    state.map._set_current_room_by_id(room_id)
    assert state.map.move(direction, state.player).moved
    assert state.world_state.coda_stage == 'home'


@pytest.mark.parametrize('seed', ['act3_arrival', 'act5_dawn'])
def test_late_story_attention_keeps_authored_truth_when_the_model_supplies_flavour(seed):
    state = SEEDS[seed]()
    if seed == 'act5_dawn':
        state = coda_state()
        state.map.move('south', state.player)
    for action in (LookAction(), ListenAction()):
        response = action.execute(ActionContext(
            player=state.player, map=state.map,
            intent=Intent(action.name, {}, 1.0, reply='An answering knock comes from the woods.'),
        ))
        assert 'answering knock' not in response.feedback
        assert response.model_effects is ModelEffectsPolicy.BLOCK


def test_coda_fixtures_preserve_old_history_and_the_call_sequence():
    state = coda_state()
    state.world_state.has_power = state.world_state.fire_lit = False
    before = state.world_state.to_dict()
    assert 'another morning' in use(state, 'northern camera').feedback
    state.map.move('south', state.player)
    for item in ('circuit breaker', 'fireplace', 'matches', 'tins', 'table', 'camera feed'):
        use(state, item)
    state.map.move('bedroom', state.player)
    assert 'ribs' in use(state, 'bed').feedback
    state.map.move('cabin', state.player)
    assert state.world_state.to_dict() == before
    use(state, 'phone')
    assert state.world_state.coda_stage == 'called'


def test_old_equipment_copies_migrate_once_without_losing_loose_props():
    old = SEEDS['act1_end']().to_dict()
    old['player']['inventory'] = ['key', 'phone', 'rope']
    old['map']['room_items']['cabin_main'] += ['key', 'camera feed', 'stone']
    for _ in range(2):
        fresh = SEEDS['act1_end']()
        state = GameState.from_dict(old, fresh.player, fresh.map, fresh.quest_manager, fresh.cutscene_manager)
        assert state.player.get_inventory_names() == ['rope']
        assert state.map.locations['cabin_interior'].rooms['cabin_main'].has_item('stone')
        assert all(item.name not in EQUIPMENT for loc in state.map.locations.values() for room in loc.rooms.values() for item in room.items)
        context = build_ai_context(state.player, state.map, state.quest_manager)
        assert 'key' in context['equipment']
        assert rule_based('use cabin key', context).args == {'item': 'key'}
        old = state.to_dict()


def test_the_care_beat_hangs_the_jacket_before_the_phone_can_be_on_its_peg():
    state = SEEDS['act3_arrival']()
    assert 'peg' not in use(state, 'phone').feedback
    assert 'hangs it on the peg' in use(state, 'nika').feedback
    assert 'jacket on the peg' in use(state, 'phone').feedback


def test_saved_frames_obey_the_phone_gate_and_record_the_night_observation():
    state = SEEDS['act3_arrival']()
    for stage in ('arrival', 'tended', 'seated', 'complete', 'consented'):
        state.world_state.reunion_stage = stage
        before = state.world_state.to_dict()
        response = use(state, 'camera feed')
        assert response.feedback == use(state, 'phone').feedback
        assert 'screen' not in response.feedback
        assert state.world_state.to_dict() == before
    state.world_state.reunion_stage = 'bedded'
    assert 'screen will not wake' in use(state, 'camera feed').feedback
    assert state.world_state.wrongness.has(AnomalyID.PHONE_DARK.value)


@pytest.mark.parametrize('room', ['konttori', 'bedroom'])
def test_scraping_remains_audible_from_the_codas_adjoining_rooms(room):
    state = SEEDS['coda_home']()
    state.world_state.coda_stage = 'scraping'
    state.map._set_current_room_by_id(room)
    response = ListenAction().execute(ActionContext(
        player=state.player, map=state.map,
        intent=Intent('listen', {}, 1.0, reply='Nothing else can be heard.'),
    ))
    assert 'scraping reaches you through the doorway' in response.feedback
    assert 'Nothing else' not in response.feedback
    assert response.model_effects is ModelEffectsPolicy.BLOCK
    assert state.world_state.coda_stage == 'scraping'


@pytest.mark.parametrize('room,wrong', [('cabin_clearing', True), ('wood_track', True), ('cabin_grounds_main', False)])
def test_validated_outdoor_fire_requests_do_not_conjure_an_indoor_hearth(room, wrong):
    from game.actions.light import LightAction
    from game.ai.validation import validate_model_response
    state = SEEDS['act5_dawn' if wrong else 'coda_home']()
    state.world_state.ending = 'escaped'
    state.map._set_current_room_by_id(room)
    before = state.world_state.to_dict()
    context = build_ai_context(state.player, state.map, state.quest_manager)
    intent = validate_model_response({'action': 'light', 'args': {'target': 'fire'}, 'confidence': 1}, context)
    assert intent.action == 'light'
    response = LightAction().execute(ActionContext(player=state.player, map=state.map, intent=intent))
    assert 'no hearth here' in response.feedback
    assert response.model_effects is ModelEffectsPolicy.BLOCK
    assert state.world_state.to_dict() == before
