"""Act I actions preserve the order and history of the evening."""
import pytest

from game.actions.base import ActionContext, ModelEffectsPolicy
from game.actions.use import UseAction, UseCircuitBreakerAction, TurnOnLightsAction
from game.ai_interpreter import Intent
from game.map import Map
from game.player import Player
from game.story import fear
from game.world_state import WorldState


@pytest.fixture
def ctx():
    game_map = Map()
    game_map._set_current_room_by_id('cabin_main')
    return ActionContext(player=Player(), map=game_map, intent=Intent('use', {}, 1.0))


def use(ctx, item):
    ctx.intent.args = {'item': item}
    return UseAction().execute(ctx)


def test_phone_and_frames_wait_for_the_real_window(ctx):
    ctx.map._set_current_room_by_id('wilderness_start')
    for item in ('phone', 'camera feed'):
        result = use(ctx, item)
        assert 'window' in result.feedback
        assert result.model_effects is ModelEffectsPolicy.BLOCK
    assert not ctx.world_state.voicemail_heard
    assert not ctx.world_state.footage_reviewed
    assert not ctx.world_state.reopening_done


def test_frames_wait_for_voicemail_and_each_evidence_changes_fear_once(ctx):
    assert not use(ctx, 'camera feed').requests
    assert not ctx.world_state.footage_reviewed
    first = use(ctx, 'phone')
    assert "It's... it's lying out there" in first.feedback
    assert ctx.world_state.reopening_done
    assert ctx.player.fear == fear.VOICEMAIL_WARNING
    second = use(ctx, 'phone')
    assert 'Frame five is black' in second.feedback
    assert ctx.world_state.footage_reviewed
    assert ctx.player.fear == fear.VOICEMAIL_WARNING + fear.CAMERA_FOOTAGE
    use(ctx, 'phone')
    assert ctx.player.fear == fear.VOICEMAIL_WARNING + fear.CAMERA_FOOTAGE


def test_sleep_requires_evidence_even_when_the_cabin_is_warm(ctx):
    ctx.world_state.fire_lit = True
    ctx.map._set_current_room_by_id('bedroom')
    result = use(ctx, 'bed')
    assert 'window' in result.feedback
    assert not ctx.world_state.first_morning
    assert not ctx.world_state.evening_meal


def test_cold_sleep_is_charged_once_and_later_fire_does_not_rewrite_it(ctx):
    use(ctx, 'phone')
    use(ctx, 'phone')
    ctx.map._set_current_room_by_id('bedroom')
    result = use(ctx, 'bed')
    assert result.model_effects is ModelEffectsPolicy.BLOCK
    assert ctx.player.health == 90
    assert ctx.world_state.slept_cold
    use(ctx, 'bed')
    assert ctx.player.health == 90
    ctx.map.move('cabin', ctx.player)
    ctx.player.add_item(ctx.map.items['matches'])
    ctx.player.add_item(ctx.map.items['firewood'])
    use(ctx, 'matches')
    restored = WorldState.from_dict(ctx.world_state.to_dict())
    assert restored.slept_cold and restored.fire_lit and restored.morning_started


def test_morning_starts_on_leaving_the_bedroom_and_never_replays(ctx):
    use(ctx, 'phone')
    use(ctx, 'phone')
    ctx.map._set_current_room_by_id('bedroom')
    use(ctx, 'bed')
    assert not ctx.world_state.morning_started
    result = ctx.map.move('cabin', ctx.player)
    assert result.story_beat and 'kettle stays cold' in result[1]
    assert ctx.world_state.morning_started
    ctx.map.move('bedroom', ctx.player)
    assert not ctx.map.move('cabin', ctx.player).story_beat


def test_eating_at_table_is_not_repeated_by_sleep(ctx):
    use(ctx, 'table')
    use(ctx, 'phone')
    use(ctx, 'phone')
    ctx.map._set_current_room_by_id('bedroom')
    result = use(ctx, 'bed')
    assert 'finish the wine' not in result.feedback
    assert ctx.world_state.evening_meal


def test_sauna_heat_does_not_survive_the_night(ctx):
    ctx.map._set_current_room_by_id('sauna')
    use(ctx, 'sauna stove')
    assert ctx.world_state.sauna_used
    ctx.world_state.first_morning = True
    assert 'gone cold' in use(ctx, 'sauna stove').feedback


@pytest.mark.parametrize("real_fire", [False, True])
def test_false_hearth_has_its_own_fire_and_stops_at_refusal(ctx, real_fire):
    ctx.world_state.fire_lit = real_fire
    ctx.world_state.enter_wrong_layer()
    assert "logs glow" in use(ctx, "fireplace").feedback
    ctx.world_state.ending = "escaped"
    assert "grey that gives no light" in use(ctx, "fireplace").feedback
    assert ctx.world_state.fire_lit is real_fire


@pytest.mark.parametrize("power", [False, True])
@pytest.mark.parametrize("action,item", [
    (UseAction(), "circuit breaker"),
    (UseAction(), "light switch"),
    (UseCircuitBreakerAction(), None),
    (TurnOnLightsAction(), None),
])
def test_false_cabin_controls_cannot_change_real_power(ctx, power, action, item):
    ctx.world_state.has_power = power
    ctx.world_state.enter_wrong_layer()
    ctx.intent.args = {"item": item} if item else {}
    result = action.execute(ctx)
    assert ctx.world_state.has_power is power
    assert not result.requests
    assert result.model_effects is ModelEffectsPolicy.BLOCK
    assert "lamp" in result.feedback
    assert "bulb" not in result.feedback and "fridge" not in result.feedback
