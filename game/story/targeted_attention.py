"""Perceptible subjects use attention, never an accidental operating action."""
from game.ai.rules import normalise_interaction_target
from game.story import AnomalyID, observe_night_seam
from game.story import perception


ALIASES = {
    "fridge hum": "fridge", "humming": "fridge", "hum": "fridge",
    "stove": "fireplace", "sauna stove": "fireplace", "fire": "fireplace", "hearth": "fireplace",
    "breaker": "circuit breaker", "fusebox": "circuit breaker",
    "porch cupboard": "circuit breaker", "switch": "light switch",
    "camera": "northern camera", "casing": "northern camera",
    "battery": "northern camera", "camera battery": "northern camera",
    "screen": "monitor", "router": "monitor", "manuals": "monitor",
    "coffee": "mug", "blue mug": "mug", "white mug": "mug", "hook": "mug",
    "nika's breathing": "breathing", "nika breathing": "breathing",
    "boards": "floorboards", "floor": "floorboards", "scraping": "floorboards",
    "frost": "window", "glass": "window", "book": "green book",
    "wine bottle": "wine", "bottle": "wine", "cupboard": "tins",
    "reeds": "lake", "water": "lake", "ice": "lake", "bird": "lake",
    "woods": "trees", "forest": "trees", "outside": "trees",
    "birch": "trees", "roots": "trees", "path": "trees",
}


def observe_target(ctx, mode, target):
    ws, room = ctx.world_state, ctx.room
    name = normalise_interaction_target(target)
    name = ALIASES.get(name, name)
    rid = room.id
    wrong = ws.is_wrong_layer()
    if name in {"room", "around", room.name.lower(), room.display_name(ws).lower()}:
        if mode == "listen":
            attention = ctx.map.observe_current_room(mode, ctx.player)
            return attention or perception.listen(room, ws)
        text = perception.look(room, ctx.player, ws) + room.get_items_description(ws)
        attention = ctx.map.observe_current_room(mode, ctx.player)
        return text + ("\n\n" + attention if attention else "")

    if mode == "listen":
        if name in {"nika", "breathing"} and wrong and rid == "cabin_main":
            return ctx.map.observe_current_room("listen", ctx.player)
        if name == "fridge" and not wrong and rid in {"cabin_main", "konttori", "bedroom"}:
            return "The fridge hums behind the wall. You can follow the low vibration without moving." if ws.has_power else "You listen towards the fridge. Without power it is silent."
        if name == "fireplace" and rid in {"cabin_main", "sauna", "bedroom", "konttori"}:
            hot = (ws.ending == "none" if wrong else ws.fire_lit and ws.ending == "none")
            if rid == "sauna":
                hot = ws.sauna_used and not ws.first_morning and ws.ending == "none"
            return "The fire ticks softly in the stove. Between the small collapses you hear your own breathing." if hot else "You listen towards the stove. There is no fire sounding in it."
        if name == "kettle" and rid == "cabin_main":
            if wrong and ws.reunion_stage not in {"bedded", "night"}:
                return ctx.map.observe_current_room("listen", ctx.player)
            return "The kettle is quiet. You stand still beside the stove, listening past it."
        if name == "hare" and rid == "deer_path" and not wrong:
            return ctx.map.observe_current_room("listen", ctx.player) or perception.listen(room, ws)
        if name == "floorboards" and rid in {"cabin_main", "bedroom", "konttori"}:
            if not wrong and ws.ending == "escaped" and ws.coda_stage == "scraping":
                return ctx.map.observe_current_room("listen", ctx.player)
            return "You hold your feet still. Nothing sounds beneath the boards."
        if name == "trees" or (name == "lake" and rid in {"lakeside", "frozen_inlet", "shoreline_bend", "sauna"}):
            if not wrong and ws.first_morning:
                return "You listen beyond your own breathing. No wind, no birds, no water; nothing farther off breaks the stillness."
            return perception.listen(room, ws) if not room.is_indoors else "You listen past the wall. No sound outside is close enough to follow."
        item = room.get_item(name) or ctx.player.get_item(name)
        if item and item.is_carryable():
            return "You hold still beside it. It makes no sound of its own."
        return "You listen for it, but cannot separate it from the sounds already around you."

    if not wrong and rid == "cabin_main":
        if name in {"circuit breaker", "light switch"}:
            return "The breaker rests in the ON position behind the snow shovel. The old white light switch is beside the door." if ws.has_power else "Behind the snow shovel the main breaker rests in the OFF position. The white light switch by the door has done nothing to wake the bulb."
        if name == "fridge":
            return "The fridge stands against the wall, its motor running." if ws.has_power else "The fridge stands against the wall. Without power there is no sound from it."
        if name == "window":
            light = "Grey daylight" if ws.first_morning else "The last light"
            return light + " catches in the glass above the sink. This is where the phone can find its one bar, angled towards the road."
        if name in {"table", "wine", "fireplace"}:
            return perception.cabin_look(ws)
        if name == "mug":
            if ws.reopening_done or ws.ending == "escaped":
                return "The hook by the stove is empty. Your white mug is where you left it on the table."
            return "The cupboard above the sink is still closed. You have not unpacked the kitchen yet."
    if rid == "konttori" and name == "monitor":
        return perception.monitor_look(ws)
    if rid == "bedroom" and name in {"bed", "mattress", "chest", "window"}:
        return perception.look(room, ctx.player, ws)
    if rid == "sauna" and name in {"fireplace", "sauna stove", "stones", "bench", "window", "lake"}:
        return perception.look(room, ctx.player, ws)
    if rid == "cabin_grounds_main" and name in {"northern camera", "wood store", "log"}:
        return perception.look(room, ctx.player, ws)
    if wrong and rid == "cabin_main":
        if name == "window":
            from game.actions.use_handlers.false_cabin import use_window
            return use_window(ctx, ctx.map.items['window']).feedback
        if name in {"phone", "mug", "tins", "floorboards"} and ws.reunion_stage in {"bedded", "night"} and ws.ending == "none":
            anomaly = {'phone': AnomalyID.PHONE_DARK, 'mug': AnomalyID.MUG_IMPOSSIBLE, 'tins': AnomalyID.WRONG_TINS, 'floorboards': AnomalyID.BLACK_BOARDS}[name]
            text, _ = observe_night_seam(ws, anomaly, ctx.player)
            return text
        if name in {"nika", "mug", "table", "mattress", "fireplace", "floorboards"}:
            return perception.false_cabin_look(room, ctx.player, ws)
        if name == "green book" and ws.ending == "none":
            return "The old green book lies open where Nika left it, its title faded on the cover. You leave the pages alone."
    if name == "phone":
        if not wrong:
            return "Your phone is in your pocket. Nika's message and the saved pictures are still there."
        if ws.ending == "escaped":
            return "Your phone stays dark in your jacket pocket. You turn towards the door."
        return "Your phone is in your jacket. You leave it there for now."
    if name in {"trees", "hare", "lake"} and not room.is_indoors:
        # Each tell keeps the same room, stage guard and callback as general attention.
        if name == "hare" and rid != "deer_path":
            return "You look along the ground. There is no hare here to follow."
        text = perception.look(room, ctx.player, ws)
        attention = ctx.map.observe_current_room("look", ctx.player)
        return text + ("\n\n" + attention if attention else "")
    item = room.get_item(name) or ctx.player.get_item(name)
    if item and item.is_carryable() and not wrong:
        return item.description
    return "You look for it among what is here, but nothing draws your eye."
