"""Selective arrivals in the real rooms. These functions only read state."""


def road(player, ws, base, revisit=False):
    if ws.first_morning:
        return "The rental stands under frost. Grey light lies along the drive between pine and birch."
    if revisit:
        return "The rental is silent now. The gravel drive bends north between pine and birch."
    return base


def clearing(player, ws, base, revisit=False):
    if ws.ending == "escaped":
        return "The drive is white in the first proper daylight. Your marks cross the frost below the cabin window; the door is just ahead."
    if ws.first_morning:
        return "In grey daylight the cabin stands plain above the drive, with the wood store at the corner and your own marks leading to the door."
    if revisit:
        return "The drive widens before the cabin door. You have the key now; the wood store stands just beyond the corner."
    return base


def cabin(player, ws, base, revisit=False):
    if ws.ending == "escaped":
        text = (
            "Cold reaches you through your jacket as you stand beside the stove. "
            "Above it the hook is empty, and you keep coming back to it while "
            "your eyes adjust to the room."
        )
        if ws.coda_stage == "scraping":
            text += " The scraping goes on, under the boards or along them. Your bag lies open beside the chair."
        return text
    if ws.first_morning:
        light = "Grey daylight lies across the table" if ws.morning_started else "The window is still black"
        if ws.fire_lit:
            heat = "the fire you lit this morning burns low" if ws.slept_cold else "the banked fire still gives back a little heat"
            return f"{light}, and {heat}. Through the outer door lies the morning's work; for a moment you stay beside the stove."
        return f"{light}. You keep your jacket on in the cold room, with the stove at your back and the morning's work beyond the outer door."
    if ws.fire_lit:
        light = "The bulb's weak yellow light scarcely reaches the corners" if ws.has_power else "Beyond the firelight the corners stay dark"
        return (
            "Warmth reaches you as you come past the table. " + light + "; close to the stove "
            "you can loosen your jacket. The konttori and bedroom open off this one warm room."
        )
    light = "The bulb gives the log walls a weak yellow cast, but the room is still cold." if ws.has_power else "The light from the window barely reaches across the cold room."
    work = (
        "you have brought water in and laid out the bedding, and the stove is the work still waiting for you."
        if ws.reopening_done else
        "beside the outer door the snow shovel leans against the porch cupboard. You know where to begin."
    )
    return light + " Beyond the table, the doors to the konttori and bedroom stand open; " + work


def konttori(player, ws, base, revisit=False):
    if not ws.has_power:
        return "You have to come close to the desk to make out the monitor among the manuals. Its screen is dark; the low ceiling keeps what little light there is near the door."
    return "Light from the monitor falls across the camera manuals on the desk. You stand beneath the low ceiling, with the main-room door at your back."


def bedroom(player, ws, base, revisit=False):
    if ws.first_morning:
        return "The bed stands open where you left it, the covers pushed back. There is barely room to pass its foot on the way to the window."
    if ws.fire_lit:
        return "Heat reaches through the doorway, bringing the smell of the hearth into the little bedroom. Under the low ceiling, the heavy-covered bed looks worth the journey."
    return "The bedroom holds the cold shut in it all year. You pause by the heavy-covered bed, your jacket brushing the doorframe in the narrow space."


def sauna(player, ws, base, revisit=False):
    if ws.sauna_used and not ws.first_morning:
        return "Heat meets you at the sauna door. The benches have lost their chill, and the small window holds the lake between the trunks like a dark plate."
    light = "The low electric lights pick out the benches" if ws.has_power else "Light from the small window falls across the benches"
    return light + ", polished by years of bare skin. The iron stove is cold; you keep your coat on."


def lakeside(player, ws, base, revisit=False):
    if ws.first_morning:
        return "The childhood path brings you out between scrub willow. Black ice reaches away from the bank under the grey sky; to the north the reeds close around the inlet. The shore bends east beneath the trees."
    return "The childhood path brings you out between scrub willow, with the lake open ahead and the last light spread thinly over the water. The bank bends east beneath the trees; to the north, reeds close around the inlet."


def inlet(player, ws, base, revisit=False):
    if ws.first_morning:
        return "Reeds close around the frozen inlet until there is no bank left to follow. You stand at the end of your own marks, with the way back south behind you."
    return "The bank narrows between the reeds and the water until you have nowhere left to put your next foot. You stop, with your own marks leading back towards the lake."


def shoreline(player, ws, base, revisit=False):
    light = "Grey light holds over the ice" if ws.first_morning else "The last light lies on the water"
    return "The shore turns east and the cabin disappears behind the bend. " + light + "; ahead, a break in the young spruce offers a climb back towards the treeline path."
