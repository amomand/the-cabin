"""Tests for layer-aware room rendering."""

from game.item import Item
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


class TestItemsDescription:
    def test_real_layer_lists_items(self):
        room = _make_room(items=[Item("rope", "A rope.", room_description="A rope lies here.")])
        world = WorldState()
        assert room.get_items_description(world) == " A rope lies here."

    def test_empty_room_description_is_never_listed(self):
        # Wrong-layer fixtures pass room_description="" to stay out of listings.
        room = _make_room(items=[Item("nika", "Nika.", room_description="")])
        world = WorldState()
        assert room.get_items_description(world) == ""

    def test_wrong_layer_with_overlay_suppresses_item_list(self):
        room = _make_room(
            wrong_description="The cabin is warm. Nika is there.",
            items=[Item("matches", "Matches.", room_description="A matchbox sits on the surface.")],
        )
        world = WorldState()
        world.enter_wrong_layer()
        assert room.get_items_description(world) == ""

    def test_wrong_layer_without_overlay_still_lists_items(self):
        room = _make_room(
            items=[Item("matches", "Matches.", room_description="A matchbox sits on the surface.")],
        )
        world = WorldState()
        world.enter_wrong_layer()
        assert room.get_items_description(world) == " A matchbox sits on the surface."

    def test_no_world_state_lists_items(self):
        room = _make_room(items=[Item("rope", "A rope.", room_description="A rope lies here.")])
        assert room.get_items_description() == " A rope lies here."
