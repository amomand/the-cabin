"""Closer attention to the authored rooms, without arrival acts or new state.

Discoveries still belong to Map.observe_current_room and the existing story
handlers. These descriptions supply the surrounding physical observation.
"""
from game.story import AnomalyID


def cabin_look(ws):
    if ws.ending == "escaped":
        hearth = "The hearth holds the ash of your fire" if ws.fire_lit else "The hearth is bare; you never lit it"
        light = "The ceiling bulb still burns weak and yellow" if ws.has_power else "The ceiling bulb is dark"
        return (
            f"{hearth}. {light}. Above the stove the hook is empty. "
            "Through the bedroom door the bed stands open where you left it. Your wine "
            "bottle stands corked on the counter with the empty glass beside it, "
            "undisturbed through everything that has happened to you."
        )
    table = (
        "Your white mug stands where you left it on the square table, within reach of the chair. "
        if ws.reopening_done else "The square table takes up most of the room, with four chairs drawn around it. "
    )
    if ws.evening_meal:
        table += "Beyond it, the corked wine bottle and empty glass stand together on the counter."
    else:
        table += "There is room here for supper once you clear a place among your supplies."
    sink = "By the window, the buckets crowd the enamel sink" if ws.reopening_done else "By the window, the enamel sink catches what light there is"
    table += " " + sink + "; its old hairline crack runs down towards the plughole."
    if ws.fire_lit:
        hearth = "The fire burns low" if ws.first_morning and ws.slept_cold else "The banked fire holds its heat" if ws.first_morning else "Split pine burns in the hearth"
        hearth += ", lighting the edge of the shelf above it."
    else:
        hearth = "The cold hearth is laid out for work, with space for kindling beneath the chimney."
    if ws.reopening_done:
        hearth += " Beside it the hook is empty."
    cupboard = "where you reset the breaker" if ws.has_power else "with the breaker behind it"
    return table + "\n\n" + hearth + f" Near the outer door the snow shovel leans against the porch cupboard, {cupboard}."


def monitor_look(ws):
    if not ws.has_power:
        return "The monitor is dark. Beside it the router has no lights; invoices and camera manuals lie in uneven stacks across the desk."
    feed = "All four feeds are live now, including the northern camera" if ws.camera_repaired else "Three live feeds hold grey pictures; the northern feed is black"
    return feed + ". The router's lights hold beside the screen, half hidden by a stack of invoices."


def false_cabin_look(room, player, ws):
    stage = ws.reunion_stage
    if ws.ending == "escaped":
        return (
            "The lamp still burns above a fire gone grey. Frost has finished its rings "
            "across the glass, and the black along the walls reaches the window sills. "
            "Your eyes stay on the door; something stands by the stove in Nika's fleece."
        )
    if stage == "arrival":
        return (
            "Nika stands beside the table, waiting for you to answer. Behind her the "
            "green book lies open beside a steaming mug. Your eyes go past it to the "
            "towel warming on the rail by the stove, then to the old scorch mark in "
            "the hearth stone. Even that is here, the mark a coal left before you "
            "were born. Heat reaches through your torn sleeve."
        )
    if stage == "tended":
        return "The bowl and damp towel are close by. Nika's hand is steady beside your face; behind her, steam rises from the mug on the table."
    if stage == "seated":
        return "Steam rises between you and Nika from the mug she has put within reach. Beyond her shoulder the lamp lights the open green book; the rest of the room can wait until your head steadies."
    if stage == "complete":
        text = (
            "The plates stand stacked by the sink; Nika's hand rests beside them, "
            "the white scar at her thumb familiar again."
            if ws.wrongness.has(AnomalyID.KNUCKLES_BIRCH.value) else
            "Nika cooks at the stove with the blue mug warm in your hands. On the rail "
            "beside her, the towel is drying; everything you need is close enough to reach."
        )
        if ws.wrongness.has(AnomalyID.FROST_WOOD_GRAIN.value):
            text += " At the window, frost branches from a centre in the grain of split wood."
        if ws.wrongness.has(AnomalyID.DELAYED_SMILE.value):
            text += " When she smiles at you, the mouth moves a half-beat before the eyes."
        return text
    if stage == "consented":
        return "The narrow bed is ready, its blankets folded back. Nika stands by the chest with the spare mattress; your jacket hangs on the peg beside the door you have let close."
    if stage in ("bedded", "night"):
        sleeper = "The thing that is not Nika" if ws.recognition else "Nika"
        text = sleeper + " lies on the mattress between you and the door. Beyond it, your jacket hangs on the peg and the blue mug stands rinsed by the sink."
        # The boards themselves are supplied by their existing attention beat.
        if ws.wrongness.has(AnomalyID.PHONE_DARK.value):
            text += " The phone is back in your jacket pocket; its screen will not wake."
        return text
    if stage == "dawn":
        return "The blue mug stays held out above the table. Behind it, the half-scowl in Nika's morning face does not alter; grey fills the window without lighting the room."
    return room.get_description(player, ws, revisit=True)


def look(room, player, ws):
    """Return a room's closer view; generic rooms keep their existing fallback."""
    rid = room.id
    if ws.is_wrong_layer():
        if rid == "cabin_main":
            return false_cabin_look(room, player, ws)
        if rid == "cabin_clearing":
            return "Where the drive should leave the clearing, old trunks stand close enough to touch. There is no car beyond them, no frost on the black ground, and above their interlocked branches no sky you can use. The compass holds south."
        if rid == "wood_track":
            return "Bark passes through the beam, one trunk at a time. The black ground between them offers no path; your compass is the only thing that gives the next step a direction. South."
    if rid == "cabin_main":
        return cabin_look(ws)
    if rid == "konttori":
        return monitor_look(ws)
    if rid == "bedroom":
        bed = "The covers lie open where you pushed them back" if ws.first_morning else "The heavy covers reach almost to the floor"
        bedding = "You have already taken out the bedding" if ws.reopening_done else "There is bedding inside"
        return f"{bed}. At the foot of the bed the chest holds the spare mattress; {bedding.lower()}. The small window faces the trees."
    if rid == "sauna":
        light = "The low electric lights burn above the bench" if ws.has_power else "The electric lights are dark"
        stones = "still give back heat" if ws.sauna_used and not ws.first_morning else "are cold"
        lake = "grey ice" if ws.first_morning else "dark water"
        return f"{light}. Below them the stones on the iron stove {stones}, just below the top bench. Through the small window, {lake} shows between the trunks."
    if rid == "wilderness_start":
        car = "Frost covers the rental's windows" if ws.first_morning else "The rental stands where you left it"
        return car + ". Beyond it the road runs back towards Korpikylä. Ahead, the drive bends north through pine and birch; you cannot see the cabin until you are almost at its door."
    if rid == "cabin_clearing":
        if ws.ending == "escaped":
            return "Your boot marks and the fox's cross the frost below the window. Beyond them the drive leads south, but the cabin door is close and your ribs have had enough."
        return "The wood store stands at the cabin's corner, split pine stacked under its roof. A path passes it towards the north side of the building; behind you the drive narrows towards the rental. The key is in your pocket."
    if rid == "cabin_grounds_main":
        if ws.ending == "escaped":
            return "The wood store is where it should be. Your day-old marks pass the wall towards the door, and the frost around them is ordinary, uneven beneath your boots."
        camera = "the casing is open and its screws lie together on the log" if ws.camera_stage == "tested" else "the casing is shut and its green light holds" if ws.camera_repaired else "the camera has no light"
        return (
            f"Under the north eave, {camera}. The split log stands beside the wall, "
            "below it; at the corner, the wood store keeps the pine dry beneath its roof. "
            "Beyond the open frost young spruce closes around the northern path. "
            "West, the familiar way down to the lake passes the sauna among the trees."
        )
    if rid == "lakeside":
        if ws.first_morning:
            return "You follow the edge of the black ice with your eyes. There is no snow on it, no crack or pressure line, nothing to break the smooth reach from the willow to the reeds. Behind you the path climbs back to the grounds."
        return "Ice holds along the edge, a pale border between the pewter water and the dark stems of the willow. Farther north, a bird moves in the reeds, too low for you to make out what it is. Behind you the path climbs towards the cabin, its familiar turn still visible through the scrub."
    if rid == "frozen_inlet":
        if ws.first_morning:
            return "Every reed stem meets the black ice at the same angle. Your eyes follow one after another, finding no broken stem, no disturbance between them. The bank ends here."
        return "Water reaches between the reed stems where the bank gives out. Ice has caught at their bases, leaving narrow openings too small to follow; farther north there is only the bed of reeds."
    if rid == "shoreline_bend":
        if ws.first_morning:
            return "Frost holds each spruce needle separately, without a branch stirring. Through the break you can follow the climb towards the treeline path; the way west curves back along the lake."
        return "The climb is steepest where it leaves the bank, then disappears into the young spruce. You can still make out the shore route west, but the light is going from the path under the trees."
    if rid == "wood_track":
        if not ws.camera_errand_done:
            return "The young spruce hides the cabin from here. Your marks lead south; the camera is still waiting at the wall."
        return "Moss banks around the birch's roots without a break in it. Beyond the fork, grey needles cover the way north into the pines; south, the spruce hides every part of the cabin."
    if rid == "deer_path":
        return "The fallen branches have no spring left in them. Grey needles lie under pines that still hold their bark, and there is nothing feeding in the litter. The ground dips north towards the old woods."
    if rid == "old_woods":
        return "You look up between the trunks. Spruce and pine have grown into one another overhead until there is no opening through the canopy; what light reaches the moss has passed through all of it. Your boot marks are the only way back south."
    return room.get_description(player, ws, revisit=True)


def listen(room, ws):
    """Ambient sound below the existing discovery and late-story responses."""
    rid = room.id
    if ws.is_wrong_layer():
        return "The trees do not stir. Your coat moves against itself when you breathe."
    if rid in ("cabin_main", "konttori", "bedroom"):
        sources = []
        if ws.has_power:
            sources.append("The fridge hums beyond the wall" if rid == "cabin_main" else "Through the doorway you hear the fridge humming in the main room")
        if ws.fire_lit and ws.ending == "none":
            sources.append("the fire ticks in the hearth" if rid == "cabin_main" else "the fire ticks beyond the doorway")
        if sources:
            sound = ", and ".join(sources)
            text = sound[0].upper() + sound[1:] + ". You stop moving to hear past it."
        else:
            text = "With the fridge silent and no fire in the hearth, your sleeve against your jacket is loud in the room."
        if ws.first_morning:
            return text + " Outside, no wind, no birds; the stillness begins beyond the walls."
        return text + " Nothing outside draws your ear."
    if rid == "sauna":
        if ws.sauna_used and not ws.first_morning:
            return "The iron stove ticks as its heat settles. You hear it from the bench after the hiss of water has faded, with the door shut on the trees outside."
        return "You listen beside the cold stove. There is no hiss from the stones, only your coat moving as you breathe."
    if ws.first_morning or ws.ending == "escaped":
        if rid in ("lakeside", "frozen_inlet", "shoreline_bend"):
            return "No water touches the bank. You wait for a crack from the ice, a stem moving in the reeds, but your own breathing is the only sound."
        return "You hold still. No wind moves the branches, and no bird answers from farther in. Your coat moves when you breathe."
    if rid == "lakeside":
        return "Water touches the ice along the bank. You stand still long enough to separate it from the small rustling farther north, where the bird moves among the reeds."
    if rid == "frozen_inlet":
        return "Water touches the reed stems close to your boots. Farther into the bed of reeds something rustles, then settles beyond where you can see."
    if rid == "shoreline_bend":
        return "From behind the bend you hear water against the bank. It reaches you more faintly here, below the trees that close over the path."
    if rid == "wilderness_start":
        return "You listen along the drive. Nothing carries from the cabin; close by, the trees let through the small rustling of the woods."
    if rid in ("cabin_clearing", "cabin_grounds_main"):
        return "You hear the woods around the clearing, small movements too far apart to follow. Down towards the lake, a bird calls once beyond the trees."
    return "You hold still and listen. Your own breathing is close; nothing farther off draws your ear."
