"""Carried story objects, separate from movable inventory."""
from game.actions.base import ActionResult

EQUIPMENT = ("phone", "camera feed", "key", "compass", "head torch", "meter")


def equipment_names(game_map):
    names = list(EQUIPMENT)
    if not ("cabin_clearing" in game_map.visited_rooms or game_map.world_state.first_morning):
        names.remove("key")
    return names


def use_equipment(ctx, name):
    ws = ctx.world_state
    if name == "key":
        if name not in equipment_names(ctx.map):
            return ActionResult.authored("The key is kept up at the cabin. You close the empty jacket pocket.")
        return ActionResult.authored("Your thumb finds the cabin key in your pocket. You keep it there, where you can reach it.")
    if name == "compass":
        if ws.is_wrong_layer():
            return ActionResult.authored(
                "The needle holds south. The torch lights the ground in that direction."
                if ws.ending == "escaped" and ctx.room.id != "cabin_main" else
                "You check the compass clipped to your jacket. The needle settles; you leave it where it is."
            )
        if ws.ending == "escaped":
            return ActionResult.authored("The compass rests against your jacket. It has brought you back; the cabin is here.")
        return ActionResult.authored("You hold the compass level and let the needle settle. South is towards the road.")
    if name == "head torch":
        if ws.is_wrong_layer():
            return ActionResult.authored(
                "The torch picks out the next trunk. You keep its beam on the ground ahead of your boots."
                if ws.ending == "escaped" and ctx.room.id != "cabin_main" else
                "Your hand finds the head torch in the jacket pocket. You leave it there for the walk."
            )
        return ActionResult.authored("You check the head torch in your pocket, thumb resting on the switch, then put it away.")
    if name == "meter":
        if ctx.room.id == "cabin_grounds_main" and ws.ending == "none" and ws.first_morning:
            from game.story.morning import use_northern_camera
            # Testing is one physical stage. A second meter check cannot
            # silently replace the battery or compare images.
            if ws.camera_stage == "untouched":
                return use_northern_camera(ctx, None)
            return ActionResult.authored("The old battery reads full. You have checked it; the reading does not explain the dead camera.")
        return ActionResult.authored("The meter stays in its case. There is nothing here you need it to settle.")
    raise ValueError(name)
