"""The camera errand and the three one-way forest tells."""
from game.story import AnomalyID, log_tell

BIRCH_ARRIVAL = (
    "The birch is fifty metres from the wall. You kneel beside it and clear the "
    "loose frost with a glove. Moss banks around the root flare. There is no "
    "torn earth, no lifted turf, no drag mark. Frost sits undisturbed in the "
    "bark seams. It has grown here for fifty years. Five weeks ago it stood "
    "somewhere else.\n\n"
    "{approach} You check the compass. South is still south. "
    "Beyond the birch the needles underfoot are grey. You take a few more "
    "steps, looking for the edge of the damage."
)

def birch_arrival(from_room):
    approach = (
        "You stand and look back. The cabin is gone. You lost it after two dozen "
        "metres of young spruce, though you know precisely where it ought to be."
        if from_room == "cabin_grounds_main" else
        "You turn towards the cabin. Young spruce shuts off the view. The grounds "
        "are just south of here, above the lake, but no part of the roof shows."
    )
    return BIRCH_ARRIVAL.format(approach=approach)


FOREST_TELLS = {
    "cabin_grounds_main": AnomalyID.FOX_TRACKS,
    "deer_path": AnomalyID.HARE,
    "old_woods": AnomalyID.STONE_FORMATIONS,
}

DISCOVERIES = {
    AnomalyID.FOX_TRACKS: (
        "Past the wood store, a fox has trotted forty metres across the open frost. "
        "You follow beside the prints, keeping your boots clear of them. The last print "
        "is perfect: four toes, heel pad, the scrape of a back foot lifting. Beyond it "
        "the ground is clean. No turn. No leap mark. No landing.\n\n"
        "Six weeks ago Nika sent you a photograph of tracks like these. \"Your fox learnt "
        "to fly,\" she wrote. You read it in a taxi, put the phone away, and answered "
        "an email. You crouch where she must have crouched, with your forearms on your "
        "knees. There is still no answer you could send her. "
        "You go back to the wall. The camera is something your hands can settle."
    ),
    AnomalyID.HARE: (
        "A dead branch catches your sleeve and snaps without spring, pale and dry "
        "right through. Whole pines stand with their bark on and nothing feeding "
        "on them. The deterioration has come on so gradually that you are well "
        "inside it before you stop.\n\n"
        "A hare sits in the open path, forepaws together, ears upright. You take a "
        "step. It stays. Another, and you can see the unmelted frost in its fur. "
        "Its chest should flutter, even at rest. There is no heartbeat shimmer. "
        "No breath. It looks at you the way you look at someone you have been "
        "waiting for. "
        "You pass it slowly. You do not look back. Ahead, the ground dips towards "
        "the old deer path. You keep walking far enough to see where it begins."
    ),
    AnomalyID.STONE_FORMATIONS: (
        "You stop where the deer path should begin. There is no path. No droppings, "
        "no browse line, no break in the moss. You search the ground beside the "
        "nearest trunk, then the next. Nothing has passed here. "
        "The forest has been emptied. Every animal instinct you have says the "
        "same word: back."
    ),
}
CALLBACKS = {
    AnomalyID.FOX_TRACKS: "You keep to your own boot marks by the wall. The last fox print stays in your mind.",
    AnomalyID.HARE: "You watch the ground ahead of your boots. You do not try to find the hare again.",
    AnomalyID.STONE_FORMATIONS: "The gap you remember should be here. Moss runs unbroken between the trunks. Go back.",
}


def observe_forest(room_id, ws, player=None, *, arrival=False):
    if not ws.first_morning or ws.is_wrong_layer() or ws.ending != "none":
        return ""
    anomaly = FOREST_TELLS.get(room_id)
    if anomaly is None:
        return ""
    if room_id != "cabin_grounds_main" and not ws.camera_errand_done:
        return ""  # an older save can retreat to finish the errand
    if log_tell(ws, anomaly, player):
        return DISCOVERIES[anomaly]
    return "" if arrival else CALLBACKS[anomaly]


def use_northern_camera(ctx, _item):
    from game.actions.base import ActionResult

    ws = ctx.world_state
    if ctx.room.id != "cabin_grounds_main" or ws.is_wrong_layer() or ws.ending != "none":
        return ActionResult.authored("You leave the camera alone. The work belongs to another morning.")
    if not ws.first_morning:
        return ActionResult.authored("The camera is above your head on the north eave. You leave its screws for daylight.")
    fox = observe_forest(ctx.room.id, ws, ctx.player, arrival=True)
    if ws.camera_stage == "untouched":
        ws.camera_stage = "tested"
        return ActionResult.authored(
            (fox + "\n\n" if fox else "") + "You bring the split log against the wall and stand on it, one hand on "
            "the eave. You bring out the screwdriver, meter and spare batteries. "
            "The screwdriver fits the worn heads of the casing screws. "
            "You catch each screw in your palm.\n\n"
            "No crack in the casing, no moisture on the board. The battery is seated "
            "properly and reads full on the meter. The camera is dead. Cold comes "
            "through your gloves from the plastic, deeper than the air's cold. "
            "You take a fresh battery from your pocket. A full reading is not the "
            "same thing as a working battery. You can at least rule it out."
        )
    if ws.camera_stage == "tested":
        ws.camera_stage = "powered"
        return ActionResult.authored(
            (fox + "\n\n" if fox else "") + "You ease out the old battery and press the new one into its contacts. "
            "The green light comes on at once. You wait. It holds. "
            "You close the casing, tightening the screws in their old seats, then "
            "connect the phone directly to the camera, its own short-range signal. "
            "The live picture fills the screen. Your breath drifts through its "
            "lower edge. The repair is done. You still have frame one saved."
        )
    if ws.camera_stage == "powered":
        ws.camera_stage = "compared"
        return ActionResult.authored(
            (fox + "\n\n" if fox else "") + "You set the live feed beside saved frame one. The bracken matches. "
            "The fallen trunk matches. The forked birch does not. In frame one it "
            "stands at the right edge. Now it stands left of centre, and nearer. "
            "You flick between the pictures until your thumb aches. No camera "
            "fault walks a birch thirty metres sideways. "
            "Before the forest moved. Your grandmother said it as plainly as "
            "before the war, then went back to pinching pastry. She has been dead "
            "twenty years.\n\n"
            "You climb down. Photograph everything, drive south, call Nika. You "
            "know the sensible things. But the birch is fifty metres into the "
            "trees, and the ground at its roots will either be disturbed or it "
            "will not. You put the phone away and check the head torch in your "
            "pocket. The compass is clipped to your jacket. Half a day of light."
        )
    return ActionResult.authored(
        (fox + "\n\n" if fox else "") + "The green light holds. You leave the casing shut. You have compared the "
        "pictures; the question is in the ground at the birch."
    )
