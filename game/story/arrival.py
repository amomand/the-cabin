"""The real evening's shared beats. Description functions never call these."""

from __future__ import annotations

from game.story import AnomalyID

COLD_NIGHT_HEALTH = 10


def reopen_cabin(ws) -> str:
    """Discover the missing mug once, with or without heat or electricity."""
    if ws.reopening_done:
        return ""
    ws.reopening_done = True
    bedding = (
        "You shake the bedding from the chest and hang it near the hearth to lose its cold."
        if ws.fire_lit else
        "You shake the bedding from the chest and spread it over the bed. The cloth is cold through."
    )
    return (
        "You fetch two buckets from the pump before settling inside. " + bedding + "\n\n"
        "Your hand goes to the hook by the stove. Empty. The blue mug has hung there "
        "since before you could reach it. Nika must have moved it. You open the "
        "cupboard above the sink: plates, old glasses, the coffee tin. No blue mug. "
        "You take a white one from the cupboard and set it on the table."
    )


def evening_meal(ws) -> str:
    """The meal may be taken at the table or finished before going to bed."""
    if ws.evening_meal:
        return ""
    opening = reopen_cabin(ws)
    ws.evening_meal = True
    food = (
        "You heat packet soup on the stove and cut bread beside it."
        if ws.fire_lit else
        "You cut bread and spread it with butter. The packet soup stays in your bag."
    )
    meal = (
        food + " You sit at the square table and pour one glass from the airport bottle. "
        "For a while the stillness outside reads as peace. You finish the wine and "
        "cork the bottle on the counter, the empty glass beside it."
    )
    return "\n\n".join(part for part in (opening, meal) if part)


def begin_morning(ws) -> str:
    """Leaving the bedroom advances the waking into the grey morning, once."""
    if ws.morning_started:
        return ""
    ws.morning_started = True
    breakfast = (
        "You put the kettle over the banked fire and eat while it heats. "
        "At the window you hold the white mug between both hands."
        if ws.fire_lit else
        "You eat the last of the cut bread. The kettle stays cold. "
        "At the window you tuck your hands into your sleeves."
    )
    return (
        ("You pull on your boots and come through to the main room. " if ws.slept_cold else
         "You dress and come through to the main room. ") + breakfast + " "
        "By the time the light comes up it is grey and directionless. You cross "
        "to the outer door and look north along the wall. Every spruce needle "
        "holds its frost. Nothing moves. The camera waits under the eave."
    )


def evening_thought(ws, room_id=None) -> str:
    """A held thought for q; no obsolete quest history after the day turns."""
    if ws.first_morning:
        if room_id == "old_woods":
            return "The deer path should be here. Your own marks lead back. Go back."
        if room_id == "deer_path":
            return "The old deer path should begin just ahead. Find it, then back."
        if room_id == "wood_track" and ws.camera_errand_done:
            return "The roots settle nothing. Grey needles lie beyond the birch. How far does the damage go?"
        if ws.wrongness.has(AnomalyID.HARE.value):
            return "You have left the hare behind. Keep to your own boot marks."
        if ws.camera_errand_done:
            return "The forked birch. You want to see the ground where it stands."
        if ws.camera_stage == "tested":
            return "The old battery reads full. The fresh one is in your pocket. Try it."
        if ws.camera_stage == "powered":
            return "The live picture on the phone. Set it beside frame one."
        return "The northern camera. Battery, moisture, board. Something your hands can settle."
    if not ws.voicemail_heard:
        return "Nika's message is on the phone. One bar at the main-room window, angled at the road."
    if not ws.footage_reviewed:
        return "The message ends. The saved pictures wait beneath it on the phone."
    return "The message and the pictures stay with you. The bed waits in the other room."
