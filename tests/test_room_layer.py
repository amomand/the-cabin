"""Tests for layer-aware room rendering."""

from game.room import Room
from game.world_state import WorldState


def _make_room(**kwargs) -> Room:
    return Room(
        name="Test Room",
        description="Real description.",
        room_id="test",
        **kwargs,
    )


class TestWrongDescription:
    def test_real_layer_uses_real_description(self):
        room = _make_room(wrong_description="Wrong description.")
        world = WorldState()
        assert room.get_description(player=None, world_state=world) == "Real description."

    def test_wrong_layer_uses_wrong_description(self):
        room = _make_room(wrong_description="Wrong description.")
        world = WorldState()
        world.enter_wrong_layer()
        assert room.get_description(player=None, world_state=world) == "Wrong description."

    def test_missing_wrong_description_falls_back_to_real(self):
        room = _make_room()
        world = WorldState()
        world.enter_wrong_layer()
        assert room.get_description(player=None, world_state=world) == "Real description."

    def test_wrong_description_fn_can_compose(self):
        def compose(player, world_state, base):
            return base + " Something is off."

        room = _make_room(
            wrong_description="The room is warm.",
            wrong_description_fn=compose,
        )
        world = WorldState()
        world.enter_wrong_layer()
        assert (
            room.get_description(player=None, world_state=world)
            == "The room is warm. Something is off."
        )


class TestEffectiveExits:
    def test_real_layer_uses_real_exits(self):
        room = _make_room()
        room.exits = {"north": ("loc", "other")}
        room.wrong_exits = {"north": ("loc", "wrong")}
        world = WorldState()
        assert room.effective_exits(world) == {"north": ("loc", "other")}

    def test_wrong_layer_uses_wrong_exits(self):
        room = _make_room()
        room.exits = {"north": ("loc", "other")}
        room.wrong_exits = {"north": ("loc", "wrong")}
        world = WorldState()
        world.enter_wrong_layer()
        assert room.effective_exits(world) == {"north": ("loc", "wrong")}

    def test_wrong_layer_without_overrides_uses_real_exits(self):
        room = _make_room()
        room.exits = {"north": ("loc", "other")}
        world = WorldState()
        world.enter_wrong_layer()
        assert room.effective_exits(world) == {"north": ("loc", "other")}
