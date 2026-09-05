"""State-aware descriptions of the real cabin. These functions only read state."""

from game.story import AnomalyID


def road(player, ws, base, revisit=False):
    if ws.first_morning:
        return "The rental stands under frost. Grey light lies along the drive between pine and birch."
    if revisit:
        return "The rental is silent now. The gravel drive bends north between pine and birch."
    return base


def clearing(player, ws, base, revisit=False):
    if ws.first_morning:
        return "The cabin stands above the drive in grey daylight. The wood store is at the corner. Your key is in your pocket."
    if revisit:
        return "The drive widens before the cabin door. The wood store stands at the corner. Your key is in your pocket."
    return base


def cabin(player, ws, base, revisit=False):
    if ws.ending == "escaped":
        hearth = "The hearth holds the ash of your fire." if ws.fire_lit else "The hearth is bare; you never lit it."
        light = "The ceiling bulb still burns weak and yellow." if ws.has_power else "The ceiling bulb is dark."
        text = (
            "The room is cold. " + hearth + " " + light + " Through the bedroom door "
            "the bed stands open where you left it. The wine bottle stands corked "
            "on the counter, the empty glass beside it. By the stove, the hook is empty."
        )
        if ws.coda_stage == "scraping":
            text += " Under the boards, slow and rhythmic, the scraping goes on. Your bag lies open beside the chair."
        return text
    parts = []
    if ws.first_morning:
        parts.append("Grey daylight lies across the table." if ws.morning_started else "The window is still black.")
        parts.append(
            ("The fire burns low in the hearth." if ws.slept_cold else "The banked fire holds a little heat.")
            if ws.fire_lit else "The hearth is cold. Your breath shows."
        )
    else:
        parts.append("Firelight moves over the log walls. The room gives back a little heat." if ws.fire_lit else "The hearth is cold. Your breath shows in the room.")
    parts.append("The ceiling bulb burns weak and yellow. The fridge hums through the wall." if ws.has_power else "The ceiling bulb stays dark. The fridge is silent.")
    if ws.reopening_done:
        parts.append("The white mug stands on the table. The hook by the stove is empty. The buckets stand by the sink.")
    if ws.evening_meal:
        parts.append("The wine bottle stands corked on the counter, the empty glass beside it.")
    else:
        parts.append("Bread and butter wait in your supplies. There is room to eat at the table.")
    return base + "\n\n" + " ".join(parts)


def konttori(player, ws, base, revisit=False):
    if not ws.has_power:
        return base + " The router has no lights. The monitor is dark."
    repaired = ws.camera_repaired
    feed = "All four feeds are live now, including the northern camera." if repaired else "Three live feeds hold grey pictures. The northern feed is black."
    return base + " The router's lights are on. " + feed


def bedroom(player, ws, base, revisit=False):
    if ws.first_morning:
        return "The bed stands open where you left it, the covers pushed back. The chest is shut."
    warmth = "Heat reaches through the doorway." if ws.fire_lit else "The heavy covers hold the room's cold."
    return "The bed stands under the low ceiling. The chest holds the spare mattress. " + warmth


def sauna(player, ws, base, revisit=False):
    light = "The low lights burn above the bench." if ws.has_power else "The lights are dark."
    stones = "The stones still give back heat." if ws.sauna_used and not ws.first_morning else "The stones on the iron stove are cold."
    lake = "Grey daylight shows the ice between the trunks." if ws.first_morning else "Through the window the lake lies between the trunks like a dark plate."
    return "The sauna is low, its benches polished by years of bare skin. " + light + " " + stones + " " + lake


def lakeside(player, ws, base, revisit=False):
    if ws.first_morning:
        return base
    return "The childhood path reaches pewter water between scrub willow. Ice holds at the edges. A bird moves somewhere in the reeds. The bank bends east; north is the inlet."


def inlet(player, ws, base, revisit=False):
    if ws.first_morning:
        return base
    return "Reeds close around the inlet. Water touches their stems. After a few paces there is no bank left to follow. Your marks lead back south."


def shoreline(player, ws, base, revisit=False):
    if ws.first_morning:
        return base
    return "The bank bends east and climbs into young spruce. The last light lies on the water behind you. The climb can wait for morning."
