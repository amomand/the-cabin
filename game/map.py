
from __future__ import annotations

from typing import Dict, Tuple, Optional

from game.location import Location
from game.room import Room
from game.requirements import WorldFlagTrue
from game.item import create_items
from game.wildlife import create_wildlife, get_random_wildlife
from game.world_state import WorldState
from game.story import AnomalyID, log_tell, maybe_finish_the_knowing


class Map:
    def __init__(self) -> None:
        # Global world state flags - now using typed WorldState
        self.world_state: WorldState = WorldState()
        
        # Track visited rooms
        self.visited_rooms: set = {"wilderness_start"}
        self.current_room_been_here_before: bool = False
        
        # Create items and wildlife for the game
        self.items = create_items()
        self.wildlife = create_wildlife()

        # Build locations and rooms
        wilderness = Location(
            location_id="wilderness",
            name="The Wilderness",
            overview_description=(
                "You are in the wilderness. The trees lean close, silent and unmoving."
            ),
        )

        cabin_grounds = Location(
            location_id="cabin_grounds",
            name="The Cabin Grounds",
            overview_description=(
                "The clearing opens around The Cabin, snow packed thin where feet remember paths."
            ),
        )

        cabin_interior = Location(
            location_id="cabin_interior",
            name="The Cabin",
            overview_description=(
                "Inside, old wood and stale heat. The air holds a memory of smoke."
            ),
        )

        # Rooms
        start_room = Room(
            name="Wilderness",
            description=(
                "You stand at the edge of your family's forest, where the gravel road thins into a winding track and vanishes beneath the trees. "
                "The air is cold, and still. Behind you, the rented car clicks as it cools. Ahead, a wall of pine and birch closes in, tall, dark and familiar. "
                "Somewhere past them lies the cabin — yours now, though it never quite feels like it. You hadn’t planned to come back, not this year. But a blur across the northern camera, followed by silence, was enough. "
                "No signal from the other feeds. Nothing since. So here you are, boot soles crunching on frosted ground, phone in your pocket searching for signal, and ten acres of wilderness between you and whatever waits beyond the bend."
            ),
            room_id="wilderness_start",
            items=[self.items["stick"], self.items["stone"]],  # Add some items to wilderness
            wildlife=get_random_wildlife(self.wildlife, max_count=1),  # Add random wildlife
            max_wildlife=1,
            wildlife_pool=self.wildlife,
        )

        clearing = Room(
            name="The Clearing",
            description=(
                "You can see the faint outline of The Cabin ahead, blurred by distance and dark."
            ),
            room_id="cabin_clearing",
            items=[self.items["rope"]],  # Add rope to clearing
            wildlife=get_random_wildlife(self.wildlife, max_count=1),  # Add random wildlife
            max_wildlife=1,
            wildlife_pool=self.wildlife,
            wrong_description=(
                "The clearing, wrong. No driveway. No car. The treeline is ancient, towering, "
                "interlocking. The ground is a deep matt black, as if burnt. The sky is a flat "
                "ceiling that gives the impression, without any feature you could point to, of "
                "not being far away.\n\n"
                "Nothing out here is looking at you. That is new, and it is worse."
            ),
            wrong_exits={
                # The wrong clearing is only crossed on the walk out, after
                # the refusal. South is the compass. The cabin stays behind.
                "cabin": ("cabin_interior", "cabin_main"),
                "south": ("cabin_grounds", "wood_track"),
            },
        )

        cabin = Room(
            name="The Cabin",
            description=(
                "You are inside a small cabin. You take a deep breath, inhaling the scent of wood.\n"
                "As you exhale, familiarity wraps around you.\n\nThis is your cabin\n\n"
                "A door leads to the konttori (office). Another opens onto the bedroom. The cabin grounds are outside."
            ),
            room_id="cabin_main",
            items=[
                self.items["matches"],
                self.items["key"],
                self.items["light switch"],
                self.items["fireplace"],
                self.items["phone"],
                self.items["window"],
                self.items["mug"],
                self.items["nika"],
                self.items["mattress"],
                self.items["tins"],
            ],
            wildlife=[],  # No wildlife inside the cabin
            max_wildlife=0,
            wildlife_pool={},
            is_indoors=True,
            description_fn=self._cabin_description,
            wrong_description=(
                "The door swings shut behind you. The fire is burning, low and steady, tended. "
                "The cabin is warm. The square table, the enamel sink, the small window. "
                "Every detail correct. A towel warms by the stove. A mug waits on the table, "
                "made exactly how you take it. The fire keeps the room ready for you.\n\n"
                "Nika is there. Sitting at the table, leafing through the old paperback from the shelf. "
                "She looks up and takes you in, bloody nose and torn jacket and wild face. "
                "The place is not merely familiar. It is prepared for you. Your name sits warm in the walls."
            ),
            wrong_description_fn=self._wrong_cabin_description,
            wrong_exits={
                # No konttori, no bedroom in the wrong layer. Only "out" — and "out"
                # leads into the wrong clearing, not the real one.
                "out": ("cabin_grounds", "cabin_clearing"),
            },
        )

        konttori = Room(
            name="Konttori",
            description=(
                "A small office space. Papers are scattered across a desk.\n"
                "The circuit breaker panel hums quietly on the wall."
            ),
            room_id="konttori",
            items=[self.items["circuit_breaker"], self.items["camera feed"]],
            wildlife=[],  # No wildlife in the office
            max_wildlife=0,
            wildlife_pool={},
            is_indoors=True,
        )

        bedroom = Room(
            name="Bedroom",
            description=(
                "The real bedroom. Low ceiling, a single window, the old bed made up under heavy covers. "
                "The smell of dry wood. From here the rest of the cabin feels further away than it is."
            ),
            room_id="bedroom",
            items=[self.items["bed"]],
            wildlife=[],
            max_wildlife=0,
            wildlife_pool={},
            is_indoors=True,
        )

        cabin_grounds_room = Room(
            name="Cabin Grounds",
            description=(
                "The area around The Cabin. Snow is packed thin where feet remember paths.\n"
                "A woodshed stands nearby, its door slightly ajar. A separate sauna building sits a short walk through the trees."
            ),
            room_id="cabin_grounds_main",
            items=[self.items["firewood"]],  # Move firewood to cabin grounds
            wildlife=get_random_wildlife(self.wildlife, max_count=1),  # Add random wildlife
            max_wildlife=1,
            wildlife_pool=self.wildlife,
            description_fn=self._grounds_description,
        )

        sauna = Room(
            name="Sauna",
            description=(
                "The sauna, low and cedar-dark. Through the small window the lake shows between the trunks, "
                "a black plate under dusk. The stove waits in the corner, stones piled on top."
            ),
            room_id="sauna",
            items=[self.items["sauna stove"]],
            wildlife=[],
            max_wildlife=0,
            wildlife_pool={},
            is_indoors=True,
        )

        lakeside = Room(
            name="Lakeside",
            description=(
                "You stand by the edge of a dark lake. The water is still and black.\n"
                "To the north, the shore narrows into a frozen inlet. East, the bank bends away from the cabin, "
                "a darker line of trees leaning over it."
            ),
            room_id="lakeside",
            items=[],  # Remove firewood from lakeside
            wildlife=get_random_wildlife(self.wildlife, max_count=1),  # Add random wildlife
            max_wildlife=1,
            wildlife_pool=self.wildlife,
        )

        frozen_inlet = Room(
            name="Frozen Inlet",
            description=(
                "The inlet pinches narrow between reeds frozen stiff in the black ice. "
                "You reach the end of it after a few paces. Nothing ahead but ice and black reed."
            ),
            room_id="frozen_inlet",
            items=[],
            wildlife=get_random_wildlife(self.wildlife, max_count=1),
            max_wildlife=1,
            wildlife_pool=self.wildlife,
        )

        shoreline_bend = Room(
            name="Shoreline Bend",
            description=(
                "The shoreline bends east here, taking the track with it. Behind you, the cabin is already hidden. "
                "North, the trees thin just enough to suggest a way through."
            ),
            room_id="shoreline_bend",
            items=[],
            wildlife=get_random_wildlife(self.wildlife, max_count=1),
            max_wildlife=1,
            wildlife_pool=self.wildlife,
        )

        wood_track = Room(
            name="Wood Track",
            description=(
                "A narrow track winds through the dense woods. The trees press close on either side.\n"
                "The path is well-worn but overgrown in places. North, a thin deer path slips between young birch. "
                "West, the real track turns under older trees."
            ),
            room_id="wood_track",
            items=[self.items["knife"]],  # Add knife to wood track
            wildlife=get_random_wildlife(self.wildlife, max_count=2),  # More wildlife in deeper woods
            max_wildlife=2,
            wildlife_pool=self.wildlife,
            description_fn=self._wood_track_description,
            wrong_description=(
                "The woods, indifferent. No path offers itself. No clearing opens. "
                "The trees stand where trees stand, one and then the next, and nothing "
                "arranges itself, and nothing follows. The compass on your jacket says "
                "south. It is the only thing out here you know to be real."
            ),
            wrong_exits={
                # The walk out continues south. Back is the black clearing.
                "south": ("cabin_grounds", "cabin_grounds_main"),
                "back": ("cabin_grounds", "cabin_clearing"),
            },
        )

        deer_path = Room(
            name="Deer Path",
            description=(
                "You push into the deer path. It gives out inside twenty paces, brush closing over the way. "
                "Branches knot low in front of you, wet bark against your sleeves when you try to press through."
            ),
            room_id="deer_path",
            items=[],
            wildlife=get_random_wildlife(self.wildlife, max_count=1),
            max_wildlife=1,
            wildlife_pool=self.wildlife,
        )

        old_woods = Room(
            name="Old Woods",
            description=(
                "Ancient trees tower overhead, their branches interlocking to form a dark canopy.\n"
                "The air is thick with the scent of moss and decay. This place feels old, older than memory."
            ),
            room_id="old_woods",
            items=[self.items["amulet"]],  # Add amulet to old woods
            wildlife=get_random_wildlife(self.wildlife, max_count=2),  # More wildlife in deepest woods
            max_wildlife=2,
            wildlife_pool=self.wildlife,
            description_fn=self._old_woods_description,
        )

        # Optional example: gate leaving the cabin interior unless power restored (diegetic placeholder)
        # Not applied globally here; instead, we add a requirement on a specific exit if desired.

        # Register rooms to locations
        wilderness.add_room(start_room)
        cabin_grounds.add_room(clearing)
        cabin_grounds.add_room(cabin_grounds_room)
        cabin_grounds.add_room(sauna)
        cabin_grounds.add_room(lakeside)
        cabin_grounds.add_room(frozen_inlet)
        cabin_grounds.add_room(shoreline_bend)
        cabin_grounds.add_room(wood_track)
        cabin_grounds.add_room(deer_path)
        cabin_grounds.add_room(old_woods)
        cabin_interior.add_room(cabin)
        cabin_interior.add_room(konttori)
        cabin_interior.add_room(bedroom)

        # Room-level exits: direction -> (target_location_id, target_room_id)
        # The real Act II forest bends after the lake and includes dead ends;
        # the wrong layer remains tighter and more pointed.
        start_room.exits = {"north": ("cabin_grounds", "cabin_clearing")}
        clearing.exits = {
            "south": ("wilderness", "wilderness_start"),
            "north": ("cabin_interior", "cabin_main"),
            "cabin": ("cabin_interior", "cabin_main"),
        }
        cabin.exits = {
            "out": ("cabin_grounds", "cabin_clearing"),
            "north": ("cabin_interior", "konttori"),
            "bedroom": ("cabin_interior", "bedroom"),
            "grounds": ("cabin_grounds", "cabin_grounds_main"),
        }
        konttori.exits = {
            "south": ("cabin_interior", "cabin_main"),
            "north": ("cabin_grounds", "cabin_grounds_main"),
        }
        bedroom.exits = {
            "out": ("cabin_interior", "cabin_main"),
            "cabin": ("cabin_interior", "cabin_main"),
        }
        cabin_grounds_room.exits = {
            "south": ("cabin_interior", "konttori"),
            "north": ("cabin_grounds", "lakeside"),
            "sauna": ("cabin_grounds", "sauna"),
            "clearing": ("cabin_grounds", "cabin_clearing"),
        }
        sauna.exits = {
            "out": ("cabin_grounds", "cabin_grounds_main"),
            "grounds": ("cabin_grounds", "cabin_grounds_main"),
        }
        lakeside.exits = {
            "south": ("cabin_grounds", "cabin_grounds_main"),
            "grounds": ("cabin_grounds", "cabin_grounds_main"),
            "north": ("cabin_grounds", "frozen_inlet"),
            "inlet": ("cabin_grounds", "frozen_inlet"),
            "east": ("cabin_grounds", "shoreline_bend"),
            "shore": ("cabin_grounds", "shoreline_bend"),
        }
        frozen_inlet.exits = {
            "south": ("cabin_grounds", "lakeside"),
            "back": ("cabin_grounds", "lakeside"),
            "lake": ("cabin_grounds", "lakeside"),
        }
        shoreline_bend.exits = {
            "west": ("cabin_grounds", "lakeside"),
            "back": ("cabin_grounds", "lakeside"),
            "north": ("cabin_grounds", "wood_track"),
            "track": ("cabin_grounds", "wood_track"),
        }
        wood_track.exits = {
            "south": ("cabin_grounds", "shoreline_bend"),
            "shore": ("cabin_grounds", "shoreline_bend"),
            "north": ("cabin_grounds", "deer_path"),
            "deer": ("cabin_grounds", "deer_path"),
            "west": ("cabin_grounds", "old_woods"),
            "deeper": ("cabin_grounds", "old_woods"),
        }
        deer_path.exits = {
            "south": ("cabin_grounds", "wood_track"),
            "back": ("cabin_grounds", "wood_track"),
            "track": ("cabin_grounds", "wood_track"),
        }
        old_woods.exits = {
            "east": ("cabin_grounds", "wood_track"),
            "track": ("cabin_grounds", "wood_track"),
            "back": ("cabin_grounds", "wood_track"),
        }

        # Map registries
        self.locations: Dict[str, Location] = {
            wilderness.id: wilderness,
            cabin_grounds.id: cabin_grounds,
            cabin_interior.id: cabin_interior,
        }

        # Starting position
        self.current_location_id = wilderness.id
        self.current_room_id = start_room.id

    @property
    def current_location(self) -> Location:
        return self.locations[self.current_location_id]

    @property
    def current_room(self) -> Room:
        return self.locations[self.current_location_id].rooms[self.current_room_id]

    def move(self, direction: str, player=None) -> Tuple[bool, str]:
        """Attempt to move in a direction. Returns (moved, message).

        - Checks room-level `exit_criteria` in order.
        - Performs cross-location transition when target location differs.
        - Returns diegetic denial text on failure.
        - Intercepts the Act II Lyer encounter when the threshold is met.
        """
        room = self.current_room
        exits = room.effective_exits(self.world_state)
        if direction not in exits:
            return False, "You turn that way and stop. Just trees and dark."

        # Check room exit criteria (if any)
        for requirement in room.exit_criteria:
            if not requirement.is_met(player, self.world_state):
                return False, requirement.denial_text(player, self.world_state)

        # Act II: if the wrongness has accumulated and Elli is in the old woods,
        # any attempt to leave triggers the Lyer encounter instead of the move.
        if (
            self.current_room_id == "old_woods"
            and self.world_state.first_morning
            and self.world_state.wrongness.threshold_met(n=3)
            and not self.world_state.lyer_encountered
            and not self.world_state.is_wrong_layer()
        ):
            return self._trigger_lyer_encounter(player)

        # Act III: in the wrong cabin, the copy won't let Elli leave until the
        # reunion has landed. She has just crashed through the door, bloody,
        # terrified. The lie works precisely by keeping her inside it.
        if (
            self.current_room_id == "cabin_main"
            and self.world_state.is_wrong_layer()
            and direction == "out"
            and not self.world_state.reunion_complete()
        ):
            return False, (
                "You move to the door. The door stays closed. Not locked. Patient. "
                "Nika catches your arm. \"Sit down. Drink. Not back out there like this.\" Her grip is steady. "
                "You let yourself be turned around."
            )

        # Act III: the consent beat. First time Elli opens the door after the
        # reunion lands, she sees the wrong outside, hears the right thing
        # said in the right voice, and chooses the warm room. The door does
        # not stop her. She lets it close.
        if (
            self.current_room_id == "cabin_main"
            and self.world_state.is_wrong_layer()
            and direction == "out"
            and self.world_state.ending == "none"
            and not self.world_state.consent_given
        ):
            self.world_state.consent_given = True
            self.world_state.reunion_stage = "consented"
            return False, self._consent_door_beat()

        # After the consent beat the night holds her. The way out of this
        # room is the choice at dawn, not the door.
        if (
            self.current_room_id == "cabin_main"
            and self.world_state.is_wrong_layer()
            and direction == "out"
            and self.world_state.ending == "none"
        ):
            if self.world_state.reunion_stage == "dawn":
                return False, (
                    "It stands between you and the door, the mug still held out, patient. "
                    "Whatever leaves this room leaves through that."
                )
            return False, (
                "You look at the door. First light, together, on the compass. "
                "The dark outside is total, and your ribs agree with it. You let the door be."
            )

        target_location_id, target_room_id = exits[direction]
        target_was_visited = target_room_id in self.visited_rooms

        # Act V: the walk out. After the refusal the woods let her pass, and
        # that is the worst part. The final southward step exits the layer.
        walkout_beat = ""
        if self.world_state.is_wrong_layer() and self.world_state.ending == "escaped":
            if self.current_room_id == "cabin_main" and target_room_id == "cabin_clearing":
                walkout_beat = self._walkout_threshold_beat()
            elif self.current_room_id == "cabin_clearing" and target_room_id == "wood_track":
                walkout_beat = self._walkout_woods_beat()
            elif self.current_room_id == "wood_track" and target_room_id == "cabin_grounds_main":
                return self._arrive_home(player)

        # Move
        self.current_location_id = target_location_id
        self.current_room_id = target_room_id
        self.current_room_been_here_before = target_was_visited

        # Mark the new room as visited
        self.visited_rooms.add(target_room_id)

        # Trigger on-enter hooks
        self.current_room.on_enter(player, self.world_state)

        return True, walkout_beat

    # --- Act II scripted content ---------------------------------------------

    def _trigger_lyer_encounter(self, player) -> Tuple[bool, str]:
        """The Act II climax. Flips into the wrong layer and drops Elli at the Wrong Cabin."""
        self.world_state.lyer_encountered = True

        # Bleed some fear and health from the tree collision. Clamp short of
        # the death thresholds so this story beat can't end the run mid-scene.
        if player is not None:
            try:
                player.fear = min(99, getattr(player, "fear", 0) + 40)
                player.health = max(1, getattr(player, "health", 100) - 20)
            except Exception:
                pass

        # Flip layer and teleport to the Wrong Cabin.
        self.world_state.enter_wrong_layer()
        self.current_location_id = "cabin_interior"
        self.current_room_id = "cabin_main"
        # She 'knows' this cabin, which is the point.
        self.current_room_been_here_before = True
        self.visited_rooms.add("cabin_main")
        self.current_room.on_enter(player, self.world_state)

        text = (
            "You turn to go back.\n"
            "The temperature drops, not gradually, a wall of cold against your face. The silence becomes absolute.\n"
            "Something is behind you. You know it the way you know a hand is near your face in the dark.\n"
            "You begin not to turn. Then do.\n"
            "It is there. Close. Height, a leaning-forward patience, a suggestion of a face where your eyes cannot make a face settle. "
            "The smell of split stone and old smoke.\n"
            "What undoes you is not its shape. It is its attention.\n"
            "You run.\n"
            "You crash through the undergrowth, the cold behind you pressing close. The shoulder. The cheekbone. A tree full on.\n"
            "The ground meets you sideways. Pine needles against your face. A high, clean tone in your ear.\n"
            "You stand, barely. You do not look back. You run south.\n"
            "The trees thin. A clearing opens. You burst into it without slowing.\n"
            "The cabin. Maybe fifty metres away. You cross the clearing at a stumble and throw yourself at the door."
        )
        return True, text

    # --- Act III: the consent-door beat ---------------------------------------

    @staticmethod
    def _consent_door_beat() -> str:
        """Elli opens the door to look for the cars, and the lie goes spatial.

        Fires once. Sets `consent_given` and advances the stage to
        "consented" at the call site. The horror is that she chooses the
        warm room, and the choosing is hers.
        """
        return (
            "You lift the latch. You mean only to look for the cars. The rental at the end "
            "of the drive, Nika's Toyota beside it. The ordinary arithmetic of vehicles.\n"
            "There is no drive. There is no car, yours or hers. The clearing runs fifty "
            "metres to a treeline that is not the treeline, trees too old and too dark and "
            "grown too close together, interlocked overhead. The ground is a deep matt "
            "black, as if burnt. And above it all, no stars, and no cloud to blame for it. "
            "A flat black ceiling that gives the impression, without any feature you could "
            "point to, of not being far away.\n"
            "The cold reaches in past you and stirs the fire behind.\n\n"
            "\"First light,\" Nika says, from close behind your shoulder. There is no alarm "
            "in her voice at all. \"We'll walk out at first light, together, on the compass. "
            "No sense in it now, in the dark, with your head.\" A hand settles on your "
            "shoulder. Warm. Certain. \"Come inside. I'm here now.\"\n\n"
            "It is the right thing to say. It is word for word what she would say.\n"
            "You step back from the doorway. You let the door close. You choose the warm room."
        )

    # --- Act V: the walk out ---------------------------------------------------

    @staticmethod
    def _walkout_threshold_beat() -> str:
        """Out of the false cabin, across the black ground, into the trees."""
        return (
            "The cold meets you at the threshold. You cross the black ground towards the "
            "treeline with your ribs in one hand, and the woods take you in without any "
            "interest at all."
        )

    @staticmethod
    def _walkout_woods_beat() -> str:
        """The worst hour: mattering to nothing."""
        return (
            "No path offers itself. No clearing opens. The trees stand where trees stand, "
            "and you walk between them in the dark of the morning, one tree and then the "
            "next, and nothing arranges itself, and nothing follows. This is the worst "
            "hour. Worse than the running. To move through a forest that has finished "
            "with you, mattering to nothing, a small warm error the woods are done "
            "with, south on the little compass clipped to your jacket.\n"
            "Twice you go down. Once on ice hidden under the crust. Once because your "
            "legs simply stop, and you lie against the frozen ground until your ribs "
            "agree to lift you again."
        )

    def _arrive_home(self, player) -> Tuple[bool, str]:
        """The final southward step. The layer releases; the coda begins."""
        self.world_state.exit_wrong_layer()
        self.world_state.coda_stage = "home"
        self.current_location_id = "cabin_grounds"
        self.current_room_id = "cabin_grounds_main"
        self.current_room_been_here_before = True
        self.visited_rooms.add("cabin_grounds_main")
        self.current_room.on_enter(player, self.world_state)
        return True, (
            "The frost, when it comes back to the ground, comes back patchy and real, "
            "grey-white, catching the torch. The trees thin into birch. Somewhere off to "
            "your left a mass of snow slides from a branch and lands, a soft ordinary "
            "crash, the first sound the world has made in hours. You stand still with "
            "your eyes shut and listen to the last of it like music.\n"
            "The light comes up while you walk, real light with a direction to it. You "
            "cross your own boot prints from the morning before, a night's new crystal "
            "grown over them, and come out of the trees fifty metres from the wood store.\n"
            "Beyond them, low roof, dark wall, dead windows, no smoke, stands the cabin."
        )

    # --- Act II anomalies: description + wrongness logging --------------------

    @staticmethod
    def _grounds_description(player, world_state, base: str) -> str:
        if not world_state.first_morning:
            return base
        return (
            base
            + "\n\nNear the north edge, the snow is marked in a thin line, too neat to be wind."
        )

    @staticmethod
    def _wood_track_description(player, world_state, base: str) -> str:
        if not world_state.first_morning:
            return base
        return (
            base
            + "\n\nSomething pale sits in the middle of the track ahead, small enough to be harmless, still enough not to be."
        )

    @staticmethod
    def _old_woods_description(player, world_state, base: str) -> str:
        if not world_state.first_morning:
            return base
        return (
            base
            + "\n\nThe moss rises and breaks in low shapes ahead, half-buried, too regular for roots."
        )

    def observe_current_room(self, mode: str, player=None) -> str:
        """Return authored attention prose for the current room, if any.

        Covers the Act II forest tells, the Act IV night seams in the false
        cabin, and the coda's scraping. Each observation logs its tell once;
        re-observing narrates without double-counting.
        """
        ws = self.world_state

        # Act IV: the night in the false cabin. Look and listen gather seams.
        if ws.is_wrong_layer():
            if (
                self.current_room_id == "cabin_main"
                and ws.reunion_stage in ("bedded", "night")
                and ws.ending == "none"
            ):
                if mode == "listen":
                    log_tell(ws, AnomalyID.BREATHING_TIDE)
                    text = (
                        "You lie still and listen to the breathing below you. Long, even "
                        "breaths, someone going down into sleep. They do not change. Sleep "
                        "has weather in it. Breath should catch at its edge, slow, shift "
                        "with the body shifting. This breathing is a tide without a moon. "
                        "In and out. Identical. Patient. You count forty breaths, and "
                        "every one of them is the same breath.\n"
                        "The hare, sitting composed at the side of the path, its flanks "
                        "not moving at all."
                    )
                    scene = maybe_finish_the_knowing(ws)
                    return text + ("\n\n" + scene if scene else "")
                if mode == "look":
                    log_tell(ws, AnomalyID.BLACK_BOARDS)
                    text = (
                        "The fire has burned down further than it should have, and the "
                        "warmth has pulled back from the walls towards the hearth. Along "
                        "the floor, where the light is lowest, the boards have gone a "
                        "deep matt black. The black of the ground outside. When you look "
                        "directly, they are boards. The room holds its shape from "
                        "attention. From yours."
                    )
                    scene = maybe_finish_the_knowing(ws)
                    return text + ("\n\n" + scene if scene else "")
            return ""

        # Coda: the real cabin, after the escape.
        if ws.ending == "escaped" and self.current_room_id == "cabin_main":
            if mode == "listen":
                if ws.coda_stage == "scraping":
                    return (
                        "The scraping goes on. Under the boards, or along them. Slow. "
                        "Rhythmic. Something dragged with patience across a floor. Not "
                        "something trying to get in. Something letting you know it is there."
                    )
                return (
                    "The cabin is quiet. The old, ordinary quiet: the fridge, the wind "
                    "finding the eaves, your own breath."
                )
            return ""

        if not ws.first_morning:
            return ""

        if mode == "look":
            if self.current_room_id == "cabin_grounds_main":
                log_tell(self.world_state, AnomalyID.FOX_TRACKS)
                return (
                    "Near the north edge, a line of fox tracks crosses the open ground. "
                    "Neat, trotting, and then gone. The last print pressed firm, and beyond it nothing. "
                    "No turn, no scatter. Just the end of a fox."
                )

            if self.current_room_id == "wood_track":
                log_tell(self.world_state, AnomalyID.HARE)
                return (
                    "A hare sits in the middle of the path, forepaws together, ears upright. "
                    "Frost on its fur. No breath in its flanks. It looks at you the way a person looks at someone they've been expecting."
                )

            if self.current_room_id == "old_woods":
                log_tell(self.world_state, AnomalyID.STONE_FORMATIONS)
                return (
                    "The birch here are thinner. Pine needles on the ground, grey not brown. "
                    "A branch brushes your arm and snaps, dry, pale as bone inside. "
                    "Half-buried in the moss, stone formations, arranged, old. The engravings are almost gone. "
                    "The cold comes from underneath."
                )

        if mode == "listen" and self.current_room_id == "wood_track":
            log_tell(self.world_state, AnomalyID.HARE)
            return (
                "You listen for the tiny animal sounds that should be there: claws in frost, "
                "breath, the panicked drag of a living thing. Nothing. The hare does not breathe."
            )

        return ""

    @staticmethod
    def _wrong_cabin_description(player, world_state, base: str) -> str:
        """Compose the Wrong Cabin description across the false-cabin night.

        The stage machine spans the whole night (arrival → dawn). Evening
        tells and night seams surface in the room description as callbacks
        once they have been observed. After the refusal, the room stops
        pretending.
        """
        stage = world_state.reunion_stage

        if world_state.ending == "escaped":
            return (
                "The pretence has stopped. The lamp burns. The fire has gone to a grey "
                "that gives no light. The black of the ground outside has come up the "
                "walls to the height of the window sills, and the frost on the glass has "
                "finished its pattern, rings within rings, the grain of a thing split "
                "open. The warmth remaining in the room ends in a clean line half a "
                "metre from the hearth.\n"
                "Something stands by the stove in Nika's fleece. You do not look at it. "
                "Nothing in the cabin is interested in you any more."
            )

        if stage == "arrival":
            return (
                "You have fallen into heat. The door swung shut behind you on its own "
                "weight, and the cold is gone. The fire is burning low and steady. Not "
                "freshly lit. The logs have collapsed inward and glow along their "
                "centres, hours old, tended. The square table. The enamel sink with its "
                "crack. The same scorch mark on the hearth stone. A towel hangs warming "
                "over the rail by the stove, and on the table, waiting, stands a mug.\n\n"
                "Nika is at the table, the old green book open under one hand. She is on "
                "her feet before she has finished speaking, a chair scraping back, three "
                "steps.\n"
                "\"Christ. What happened to you?\""
            )

        if stage == "tended":
            return (
                "Your face has been cleaned, chin steadied between finger and thumb, "
                "short businesslike strokes that hurt exactly as much as they had to and "
                "no more. Nika has looked into one eye and then the other, pressed along "
                "your cheekbone and down your ribs. Nothing's moving that shouldn't, she "
                "says, to the fire, already deciding the evening. Concussion. Cracked or "
                "bruised. Either way you're not walking anywhere tonight.\n"
                "\"First light, we walk out together.\""
            )

        if stage == "seated":
            return (
                "You are in the chair by the fire. Nika pressed you into it. The mug is "
                "in front of you, steam rising, not yet tasted.\n"
                "Nika is at the other side of the table, watching you, annoyed in the "
                "way that means she is frightened. The fire crackles. The room waits. "
                "Your name sits warm in the walls."
            )

        if stage == "complete":
            additions = []
            if world_state.wrongness.has(AnomalyID.FROST_WOOD_GRAIN.value):
                additions.append(
                    "On the window, the frost still patterns like wood grain - growth rings spreading from some unseen centre."
                )
            if world_state.wrongness.has(AnomalyID.KNUCKLES_BIRCH.value):
                additions.append(
                    "Nika's hand tightens on the mug. You do not look at it directly."
                )
            if world_state.wrongness.has(AnomalyID.DELAYED_SMILE.value):
                additions.append(
                    "She smiles at something you said. The smile arrives a fraction late, as if laid across the face."
                )

            seated = (
                "You are still in the chair. The blue mug is warm in your hands. Nika is "
                "across from you, present, solid, entirely here."
            )
            if not additions:
                return seated
            return seated + "\n\n" + "\n".join(additions)

        if stage == "consented":
            return (
                "The door is closed. You chose the warm room, and the room knows it.\n"
                "Nika stacks the fire for the night, not looking at you, and pulls the "
                "spare mattress from the chest, the one that has lived there since "
                "before either of you could carry it.\n"
                "\"We should get some sleep if we're walking out early,\" she says. "
                "\"Sauna will have to wait. You'd cook your brain in that state anyway.\""
            )

        if stage in ("bedded", "night"):
            lines = [
                "The lamp is down. Firelight moves on the boards of the ceiling. "
                "Nika lies on the mattress between you and the door, where she has "
                "always lived."
            ]
            if world_state.wrongness.has(AnomalyID.BREATHING_TIDE.value):
                lines.append(
                    "Below you, the breathing goes on. In and out. Identical. A tide without a moon."
                )
            if world_state.wrongness.has(AnomalyID.BLACK_BOARDS.value):
                lines.append(
                    "Along the floor, where the light is lowest, the boards hold their black."
                )
            if world_state.wrongness.has(AnomalyID.PHONE_DARK.value):
                lines.append("Your phone lies where you left it. Dark all through.")
            if world_state.wrongness.has(AnomalyID.WRONG_TINS.value):
                lines.append("The tins sit stacked by the stove. Not yours. None of it yours.")
            if stage == "night":
                lines.append(
                    "You do not sleep. You lie in the warmth it keeps for you and do the "
                    "accounting. You drank the coffee. You let yourself be settled. You "
                    "lay in the bed it made, wanting it. That part is yours."
                )
            return "\n".join(lines)

        if stage == "dawn":
            return (
                "Grey has come into the window at last. The wrong grey, sourceless.\n"
                "The thing that is not Nika is up in one motion, the kettle already on. "
                "It pours coffee into the blue mug and holds the mug out to you, and its "
                "face makes Nika's morning face, the half-scowl before the day's first "
                "words.\n"
                "\"Drink up. We'll want the light.\""
            )

        # stage == "none": not in the false-cabin night at all.
        return base

    def display_map(self, visited_rooms: set) -> str:
        """Display an ASCII map of visited areas.
        
        Args:
            visited_rooms: Set of room IDs the player has visited
            
        Returns:
            ASCII map string
        """
        width = 60

        def visited(room_id: str) -> bool:
            return room_id in visited_rooms

        def connected(a: str, b: str) -> bool:
            return visited(a) and visited(b)

        def render_line(*segments: tuple[int, str, bool]) -> str:
            cells = [" "] * width
            wrote = False
            for start, text, should_render in segments:
                if not should_render:
                    continue
                wrote = True
                for offset, char in enumerate(text):
                    idx = start + offset
                    if 0 <= idx < width:
                        cells[idx] = char
            return "".join(cells).rstrip() if wrote else ""

        map_lines = [
            render_line((28, "Deer Path", visited("deer_path"))),
            render_line((32, "|", connected("deer_path", "wood_track"))),
            render_line(
                (17, "Old Woods", visited("old_woods")),
                (26, " - ", connected("old_woods", "wood_track")),
                (29, "Wood Track", visited("wood_track")),
            ),
            render_line((32, "|", connected("wood_track", "shoreline_bend"))),
            render_line(
                (16, "Frozen Inlet", visited("frozen_inlet")),
                (32, "|", connected("wood_track", "shoreline_bend")),
            ),
            render_line(
                (21, "|", connected("frozen_inlet", "lakeside")),
                (32, "|", connected("wood_track", "shoreline_bend")),
            ),
            render_line((10, "Sauna", visited("sauna"))),
            render_line((10, "|", connected("sauna", "cabin_grounds_main"))),
            render_line(
                (0, "Cabin Grounds", visited("cabin_grounds_main")),
                (13, " - ", connected("cabin_grounds_main", "lakeside")),
                (16, "Lakeside", visited("lakeside")),
                (24, " - ", connected("lakeside", "shoreline_bend")),
                (27, "Shoreline Bend", visited("shoreline_bend")),
            ),
            render_line(
                (5, "||", connected("cabin_grounds_main", "konttori")),
            ),
            render_line(
                (2, "Konttori", visited("konttori")),
            ),
            render_line(
                (5, "||", connected("konttori", "cabin_main")),
            ),
            render_line(
                (1, "The Cabin", visited("cabin_main")),
                (10, " - ", connected("cabin_main", "bedroom")),
                (13, "Bedroom", visited("bedroom")),
            ),
            render_line((5, "|", connected("cabin_main", "cabin_clearing"))),
            render_line((0, "The Clearing", visited("cabin_clearing"))),
            render_line((5, "|", connected("cabin_clearing", "wilderness_start"))),
            render_line((0, "The Wilderness", visited("wilderness_start"))),
        ]

        map_lines = [line for line in map_lines if line]
        return "\n".join(map_lines)

    def get_visited_rooms(self) -> set:
        """Get a set of all room IDs that have been visited."""
        return self.visited_rooms.copy()

    @staticmethod
    def _cabin_description(player, world_state, base: str) -> str:
        """Dynamic cabin description based on world state."""
        # Coda: the real cabin after the escape. Yesterday's warmth is gone
        # and the flags that made it are beside the point now.
        if world_state.ending == "escaped":
            lines = [
                "Cold, dark, the smell of yesterday's fire. Through the bedroom door "
                "the bed stands open where you left it. The wine bottle stands corked "
                "on the counter, the empty glass beside it.",
                "By the stove, the hook is empty. You stand in front of it a while.",
            ]
            if world_state.coda_stage == "scraping":
                lines.append(
                    "Under the boards, slow and rhythmic, the scraping goes on. Your "
                    "bag sits where you set it down. Your grandmother's chair faces "
                    "the empty hook."
                )
            return "\n\n".join(lines)

        additions = []
        if world_state.get("fire_lit", False):
            additions.append("A fire crackles in the hearth, casting warm light across the walls.")
        if world_state.get("has_power", False):
            additions.append("The overhead light hums faintly.")
        if not world_state.get("has_power", False) and not world_state.get("fire_lit", False):
            additions.append("The cabin is dark. Cold seeps through the floorboards.")
        if additions:
            return base + "\n\n" + " ".join(additions)
        return base

    def _set_current_room_by_id(
        self,
        room_id: str,
        been_here_before: bool = False,
    ) -> bool:
        """
        Set current room by ID (for save/load).
        
        Returns True if room was found and set, False otherwise.
        """
        for location_id, location in self.locations.items():
            if room_id in location.rooms:
                self.current_location_id = location_id
                self.current_room_id = room_id
                self.current_room_been_here_before = been_here_before
                return True
        return False
