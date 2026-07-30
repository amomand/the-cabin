"""Tests for layer-aware room rendering."""

from game.item import Item
from game.room import DENIAL_INDOORS, DENIAL_OUTDOORS, Room
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


class TestMovementDenial:
    """A refused direction is answered by where the player is standing."""

    def test_outdoor_room_keeps_the_wilderness_line(self):
        room = _make_room()
        assert room.movement_denial(WorldState()) == DENIAL_OUTDOORS

    def test_indoor_room_does_not_get_trees(self):
        """The regression: an interior answered with a description of trees."""
        room = _make_room(is_indoors=True)
        denial = room.movement_denial(WorldState())
        assert denial == DENIAL_INDOORS
        assert "trees" not in denial

    def test_authored_line_wins_over_the_default(self):
        room = _make_room(is_indoors=True, denial_text="The corridor ends.")
        assert room.movement_denial(WorldState()) == "The corridor ends."

    def test_wrong_layer_override_wins(self):
        room = _make_room(
            is_indoors=True,
            denial_text="The corridor ends.",
            wrong_denial_text="The room does not continue.",
        )
        world = WorldState()
        world.enter_wrong_layer()
        assert room.movement_denial(world) == "The room does not continue."

    def test_wrong_layer_falls_back_to_the_authored_real_line(self):
        room = _make_room(is_indoors=True, denial_text="The corridor ends.")
        world = WorldState()
        world.enter_wrong_layer()
        assert room.movement_denial(world) == "The corridor ends."

    def test_wrong_denial_is_ignored_in_the_real_layer(self):
        room = _make_room(is_indoors=True, wrong_denial_text="The room does not continue.")
        assert room.movement_denial(WorldState()) == DENIAL_INDOORS

    def test_denials_stay_diegetic(self):
        for line in (DENIAL_INDOORS, DENIAL_OUTDOORS):
            lower = line.lower()
            for banned in ("invalid", "error", "you can't", "cannot", "exit"):
                assert banned not in lower, line
