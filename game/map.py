
from __future__ import annotations

from typing import Dict, Optional

from game.location import Location
from game.room import Room
from game.requirements import WorldFlagTrue
from game.item import create_items
from game.world_state import WorldState
from game.story import AnomalyID, fear, log_tell, observe_night_seam
from game.story.evening import observe_remaining_evening_tells


# The tree, taken full on. Health only; the fear half is `fear.CLIMAX_FLIGHT`.
CLIMAX_INJURY_HEALTH = 20


class MoveOutcome(tuple):
    """A movement decision plus whether its narration is a story beat.

    This remains a real two-tuple so existing callers keep equality, indexing,
    length, and unpacking semantics.  ``story_beat`` is additional metadata for
    callers that need the authored-story signal.
    """

    story_beat: bool

    def __new__(
        cls,
        moved: bool,
        message: str,
        story_beat: bool = False,
    ) -> "MoveOutcome":
        outcome = super().__new__(cls, (moved, message))
        outcome.story_beat = story_beat
        return outcome

    @property
    def moved(self) -> bool:
        return self[0]

    @property
    def message(self) -> str:
        return self[1]

    def __getnewargs__(self) -> tuple[bool, str, bool]:
        """Preserve tuple data and story metadata when reconstructing."""
        return self.moved, self.message, self.story_beat

    @classmethod
    def story(cls, moved: bool, message: str) -> "MoveOutcome":
        return cls(moved, message, story_beat=True)


class Map:
    def __init__(self) -> None:
        # Global world state flags - now using typed WorldState
        self.world_state: WorldState = WorldState()
        
        # Track visited rooms
        self.visited_rooms: set = {"wilderness_start"}
        self.current_room_been_here_before: bool = False
        
        # Create items for the game
        self.items = create_items()

        # Build locations and rooms
        wilderness = Location(
            location_id="wilderness",
            name="The Wilderness",
            overview_description=(
                "The gravel drive narrows between pine and birch. The road is already out of sight."
            ),
        )

        cabin_grounds = Location(
            location_id="cabin_grounds",
            name="The Cabin Grounds",
            overview_description=(
                "The clearing opens around the cabin, snow worn thin on the old paths."
            ),
        )

        cabin_interior = Location(
            location_id="cabin_interior",
            name="The Cabin",
            overview_description=(
                "Inside, dry pine boards and the old smoke caught in them."
            ),
        )

        # Rooms
        start_room = Room(
            name="Wilderness",
            description=(
                "The gravel drive leaves the road and narrows between the trees. Behind you, the rented car clicks as it cools. "
                "Four hours north, straight through Korpikylä. Ahead, pine and birch close over the track. "
                "The cabin stands somewhere beyond the bend, yours on paper and nowhere else. Seven days ago the northern camera caught three seconds of grey at the treeline and went dark. "
                "The other feeds kept showing frost and stillness. Your phone hunts for reception in your pocket."
            ),
            room_id="wilderness_start",
            items=[self.items["stick"], self.items["stone"]],  # Add some items to wilderness
        )

        clearing = Room(
            name="The Clearing",
            description=(
                "The forest gives up the cabin late: a low roof and dark walls against the trees. "
                "One small window holds what is left of the light. The key is under the north log, "
                "wrapped in its square of black plastic. Your fingers know where to reach."
            ),
            room_id="cabin_clearing",
            items=[self.items["rope"]],  # Add rope to clearing
            wrong_description=(
                "The clearing, wrong. No driveway. No car. The trees are too old and dark, "
                "grown too close, their branches interlocked overhead. The ground is a deep "
                "matt black, as if burnt. The sky is a flat "
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
                "The square table stands in the middle of the room. The enamel sink catches a little light; its hairline crack is still there. "
                "By the stove, the hook for the blue mug is empty. The porch cupboard is just inside the outer door, the snow shovel propped against it.\n\n"
                "The konttori is through the north door. The bedroom opens off the main room, and the cabin grounds lie outside."
            ),
            room_id="cabin_main",
            items=[
                self.items["matches"],
                self.items["circuit_breaker"],
                self.items["light switch"],
                self.items["fireplace"],
                self.items["phone"],
                self.items["window"],
                self.items["mug"],
                self.items["nika"],
                self.items["mattress"],
                self.items["tins"],
            ],
            is_indoors=True,
            description_fn=self._cabin_description,
            wrong_description=(
                "The door swings shut behind you. The fire is burning, low and steady, tended. "
                "The cabin is warm. The square table, the enamel sink, the small window. "
                "Every detail correct. A towel warms by the stove. A mug waits on the table, "
                "made exactly how you take it. The fire keeps the room ready for you.\n\n"
                "Nika is there. Sitting at the table, leafing through the old paperback from the shelf. "
                "She looks up and takes you in, bloody nose and torn jacket and wild face. "
                "The place is not merely familiar. Someone has prepared it for you, down to the coffee "
                "cooling in the mug."
            ),
            wrong_description_fn=self._wrong_cabin_description,
            wrong_exits={
                # No konttori, no bedroom in the wrong layer. Only "out"; that exit
                # leads into the wrong clearing, not the real one.
                "out": ("cabin_grounds", "cabin_clearing"),
            },
            # "out" has its own denial (the patient door, Nika's hand). Every
            # other direction lands here, so the room has to hold on its own:
            # the enclosure is the whole point of the scene.
            wrong_denial_text=(
                "You turn that way and stop. The room does not continue. "
                "Fire, table, door. It does not need more than that to keep you."
            ),
        )

        konttori = Room(
            name="Konttori",
            description=(
                "The konttori is scarcely a room: a desk under the low ceiling, invoices and camera manuals in uneven stacks.\n"
                "On the desk, three camera feeds hold their grey pictures. The northern one is black."
            ),
            room_id="konttori",
            items=[self.items["camera feed"]],
            is_indoors=True,
        )

        bedroom = Room(
            name="Bedroom",
            description=(
                "A low ceiling, one small window, the old bed made up under heavy covers. "
                "The room smells of dry wood and the cold shut in here all year."
            ),
            room_id="bedroom",
            items=[self.items["bed"]],
            is_indoors=True,
        )

        cabin_grounds_room = Room(
            name="Cabin Grounds",
            description=(
                "Snow lies thin around the cabin, worn through where the old paths run.\n"
                "The woodshed door stands ajar. Beyond it, the sauna sits among the trees above the lake."
            ),
            room_id="cabin_grounds_main",
            items=[self.items["firewood"]],  # Move firewood to cabin grounds
            description_fn=self._grounds_description,
        )

        sauna = Room(
            name="Sauna",
            description=(
                "The sauna is low and dark. Through the small window the lake shows between the trunks, "
                "a black plate under dusk. Stones are piled on the iron stove in the corner."
            ),
            room_id="sauna",
            items=[self.items["sauna stove"]],
            is_indoors=True,
        )

        lakeside = Room(
            name="Lakeside",
            description=(
                "The childhood path reaches the lake between scrub willow and frost-stiff grass. "
                "The water has frozen early: smooth black ice without snow, crack, or pressure line.\n"
                "The bank bends east. North, reeds close around a narrow inlet."
            ),
            room_id="lakeside",
            items=[],  # Remove firewood from lakeside
        )

        frozen_inlet = Room(
            name="Frozen Inlet",
            description=(
                "The inlet pinches shut between reeds, every stem frozen at the same angle in the black ice. "
                "After a few paces there is no bank left to follow. Your own marks lead back south."
            ),
            room_id="frozen_inlet",
            items=[],
        )

        shoreline_bend = Room(
            name="Shoreline Bend",
            description=(
                "The path follows the bank east, then leaves the water at a break in the young spruce. "
                "The cabin is out of sight behind the bend. Ahead, frost holds each needle exact, and nothing moves."
            ),
            room_id="shoreline_bend",
            items=[],
        )

        wood_track = Room(
            name="Wood Track",
            description=(
                "The track narrows to the width of one boot between young birch. North, a break in the brush "
                "closes again almost at once. West, older pines shut over the ground."
            ),
            room_id="wood_track",
            items=[],
            description_fn=self._wood_track_description,
            wrong_description=(
                "Your head torch finds one trunk and then the next. Beyond each is more "
                "black ground, more bark. The compass on your jacket holds south."
            ),
            wrong_exits={
                # The walk out continues south. Back is the black clearing.
                "south": ("cabin_grounds", "cabin_grounds_main"),
                "back": ("cabin_grounds", "cabin_clearing"),
            },
        )

        deer_path = Room(
            name="Birch Thicket",
            description=(
                "You push into the break in the birch. It closes inside twenty paces. "
                "Old stems cross at chest height, rooted where a path would have to be."
            ),
            room_id="deer_path",
            items=[],
        )

        old_woods = Room(
            name="Old Woods",
            description=(
                "The canopy has knitted shut. The trunks are spruce and pine, but grown so old they no longer "
                "look like either. Moss and rot lie heavy in the air; beneath them, split stone and old smoke."
            ),
            room_id="old_woods",
            items=[],
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
            "south": ("cabin_interior", "cabin_main"),
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
            "birch": ("cabin_grounds", "deer_path"),
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

    def _at_false_cabin_door(self, direction: str) -> bool:
        """Whether `direction` is the false cabin's one door, from inside it."""
        return (
            self.current_room_id == "cabin_main"
            and self.world_state.is_wrong_layer()
            and direction == "out"
        )

    def false_cabin_holds_door(self, direction: str) -> bool:
        """Whether the false cabin refuses this exit without moving Elli.

        True across the reunion (Nika's hand on her arm), the night, and the
        dawn offer. False for the one opening in that span, the consent beat
        at stage "complete", where the door opens and she chooses to let it
        close; and False once an ending has landed and the walk out begins.
        `move` narrates the refusal; overlays such as help consult this so
        they never advertise a route the story has closed.
        """
        if not self._at_false_cabin_door(direction):
            return False
        ws = self.world_state
        if not ws.reunion_complete():
            return True
        if ws.ending != "none":
            return False
        return not (ws.reunion_stage == "complete" and not ws.consent_given)

    def move(self, direction: str, player=None) -> MoveOutcome:
        """Attempt to move in a direction and classify authored story beats.

        - Checks room-level `exit_criteria` in order.
        - Performs cross-location transition when target location differs.
        - Returns diegetic denial text on failure.
        - Intercepts the Act II Lyer encounter when the threshold is met.
        """
        room = self.current_room
        exits = room.effective_exits(self.world_state)
        if direction not in exits:
            return MoveOutcome(False, room.movement_denial(self.world_state))

        # Check room exit criteria (if any)
        for requirement in room.exit_criteria:
            if not requirement.is_met(player, self.world_state):
                return MoveOutcome(False, requirement.denial_text(player, self.world_state))

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

        # The false cabin's door. Held across the reunion and the night;
        # opened once, for the consent beat; then held again until dawn is
        # answered. `false_cabin_holds_door` is the shared gate, so help and
        # any other overlay describing the ways out agree with the move.
        if self.false_cabin_holds_door(direction):
            # Act III: in the wrong cabin, the copy won't let Elli leave until
            # the reunion has landed. She has just crashed through the door,
            # bloody, terrified. The lie works precisely by keeping her inside it.
            if not self.world_state.reunion_complete():
                return MoveOutcome.story(False, (
                    "You put a hand on the latch. Nika catches your arm. \"Sit down. Drink. "
                    "Not back out there like this.\" Her grip is solid through the torn sleeve. "
                    "The door remains closed behind you."
                ))
            # After the consent beat the night holds her. The way out of this
            # room is the choice at dawn, not the door.
            if self.world_state.reunion_stage == "dawn":
                return MoveOutcome.story(False, (
                    "It stands between you and the door, one arm level, the mug still "
                    "held out. The coffee gives off the same thin thread of steam."
                ))
            return MoveOutcome.story(False, (
                "You look at the door. First light, together, on the compass. "
                "The dark outside is total, and your ribs agree with it. You let the door be."
            ))

        # Act III: the consent beat. First time Elli opens the door after the
        # reunion lands, she sees the wrong outside, hears the right thing
        # said in the right voice, and chooses the warm room. The door does
        # not stop her. She lets it close. Pinned to stage "complete" exactly
        # so a malformed save further into the night can never regress to it.
        if (
            self._at_false_cabin_door(direction)
            and self.world_state.ending == "none"
            and self.world_state.reunion_stage == "complete"
            and not self.world_state.consent_given
        ):
            narration = self._consent_door_beat(player)
            self.world_state.consent_given = True
            self.world_state.transition_reunion_to("consented")
            fear.shift(player, fear.CONSENT_DOOR)
            return MoveOutcome.story(False, narration)

        # After the refusal, the walk out is one-way. Backtracking would replay
        # the authored movement beats and make the indifferent woods behave like
        # a corridor the player can pace.
        if self.world_state.is_wrong_layer() and self.world_state.ending == "escaped":
            if self.current_room_id == "cabin_clearing" and direction == "cabin":
                return MoveOutcome.story(False, (
                    "The cabin stands behind you with its lit window. You keep the "
                    "compass south and do not turn back."
                ))
            if self.current_room_id == "wood_track" and direction == "back":
                return MoveOutcome.story(False, (
                    "The black clearing is behind you. The compass still says south. "
                    "You follow it."
                ))

        target_location_id, target_room_id = exits[direction]
        target_was_visited = target_room_id in self.visited_rooms

        # Act V: the walk out. After the refusal the woods let her pass, and
        # that is the worst part. The final southward step exits the layer.
        walkout_beat = ""
        story_beat = False
        if self.world_state.is_wrong_layer() and self.world_state.ending == "escaped":
            if self.current_room_id == "cabin_main" and target_room_id == "cabin_clearing":
                walkout_beat = self._walkout_threshold_beat()
                story_beat = True
                fear.shift(player, fear.WALKOUT_THRESHOLD)
            elif self.current_room_id == "cabin_clearing" and target_room_id == "wood_track":
                walkout_beat = self._walkout_woods_beat()
                story_beat = True
                fear.shift(player, fear.WALKOUT_WOODS)
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

        return MoveOutcome(True, walkout_beat, story_beat=story_beat)

    # --- Act II scripted content ---------------------------------------------

    def _trigger_lyer_encounter(self, player) -> MoveOutcome:
        """The Act II climax. Flips into the wrong layer and drops Elli at the Wrong Cabin.

        Returns no prose. The flight lives in `game/story/cutscenes/lyer-encounter.txt`
        and plays through the cutscene channel, keyed on this exact
        `old_woods -> cabin_main` transition.

        It used to be returned from here as the move's feedback, and both
        surfaces render feedback *after* the destination room, so the player
        was set down in the warm room, greeted by Nika mid-sentence, and only
        then told about the treeline and the run that got her there. The scene
        arrived as a status report about itself, and it put "What happened to
        you?" before anything had happened to her.
        """
        self.world_state.lyer_encountered = True

        # Bleed some fear and health from the tree collision. Clamp short of
        # the death thresholds so this story beat can't end the run mid-scene.
        fear.shift(player, fear.CLIMAX_FLIGHT)
        if player is not None:
            try:
                player.health = max(1, getattr(player, "health", 100) - CLIMAX_INJURY_HEALTH)
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

        return MoveOutcome.story(True, "")

    # --- Act III: the consent-door beat ---------------------------------------

    def _consent_door_beat(self, player=None) -> str:
        """Elli opens the door to look for the cars, and the lie goes spatial.

        Fires once. Sets `consent_given` and advances the stage to
        "consented" at the call site. The horror is that she chooses the
        warm room, and the choosing is hers.
        """
        evening = observe_remaining_evening_tells(self.world_state, player)
        doorway = (
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
            "shoulder, warm and certain. \"Come inside. I'm here now.\"\n\n"
            "It is what the real Nika would say: fear reduced to a task with a time "
            "attached. The black ground waits, and you are injured, exhausted, twenty years starved of "
            "this voice saying exactly these things.\n"
            "You step back from the doorway. You let the door close. You choose the warm room."
        )
        return evening + ("\n\n" if evening else "") + doorway

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
            "next. Nothing arranges itself and nothing follows. This is the worst hour, "
            "worse than the running: moving through a forest that has finished with you, "
            "mattering to nothing, a small warm error the woods are done with, south on "
            "the little compass clipped to your jacket.\n"
            "Twice you go down. Once on ice hidden under the crust. Once because your "
            "legs simply stop, and you lie against the frozen ground until your ribs "
            "agree to lift you again."
        )

    def _arrive_home(self, player) -> MoveOutcome:
        """The final southward step. The layer releases; the coda begins."""
        self.world_state.exit_wrong_layer()
        self.world_state.transition_coda_to("home")
        self.current_location_id = "cabin_grounds"
        self.current_room_id = "cabin_grounds_main"
        self.current_room_been_here_before = True
        self.visited_rooms.add("cabin_grounds_main")
        self.current_room.on_enter(player, self.world_state)
        fear.shift(player, fear.ARRIVE_HOME)
        return MoveOutcome.story(True, (
            "Somewhere off to your left a mass of snow slides from a branch and lands, "
            "a soft ordinary crash, the first sound the world has made in hours. You stand still with "
            "your eyes shut and listen to the last of it like music.\n"
            "The light comes up while you walk, real light with a direction to it. You "
            "cross your own boot prints from the morning before, a night's new crystal "
            "grown over them, and come out of the trees fifty metres from the wood store.\n"
            "Beyond them, low roof, dark wall, dead windows, no smoke, stands the cabin."
        ))

    # --- Act II anomalies: description + wrongness logging --------------------

    @staticmethod
    def _grounds_description(player, world_state, base: str) -> str:
        if world_state.ending == "escaped" and world_state.coda_stage == "home":
            return (
                "Frost lies patchy and real under the head torch. The pines have thinned "
                "into birch. Somewhere ahead, beyond the wood store, is the cabin."
            )
        if not world_state.first_morning:
            return base
        return (
            base
            + "\n\nBeyond the wood store, one line of prints crosses the open frost and stops short "
            "of the northern camera."
        )

    @staticmethod
    def _wood_track_description(player, world_state, base: str) -> str:
        if not world_state.first_morning:
            return base
        return (
            base
            + "\n\nThe forked birch grows from unbroken ground. Moss has banked around the root flare; "
            "frost lies in the bark seams. It has stood here fifty years. Five weeks ago it stood somewhere else. "
            "When you look back, the cabin is gone. Two hundred metres of young spruce should not have closed "
            "behind you like that.\n\n"
            "Past the last birch, pine needles lie grey instead of brown. A hare sits in the open track."
        )

    @staticmethod
    def _old_woods_description(player, world_state, base: str) -> str:
        if not world_state.first_morning:
            return base
        return (
            base
            + "\n\nThe ground is hard with frost, but the cold rises through your boot soles. "
            "You stop where the deer path should be."
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
                    text, _ = observe_night_seam(
                        ws, AnomalyID.BREATHING_TIDE, player
                    )
                    return text
                if mode == "look":
                    text, _ = observe_night_seam(ws, AnomalyID.BLACK_BOARDS, player)
                    return text
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
                log_tell(self.world_state, AnomalyID.FOX_TRACKS, player)
                return (
                    "Past the wood store, a fox has trotted forty metres across the open frost. "
                    "The last print is perfect: four toes, heel pad, the scrape of a back foot lifting. "
                    "Beyond it the ground is clean. No turn. No leap mark. No landing. You crouch there "
                    "with your forearms on your knees.\n\n"
                    "Six weeks ago Nika sent you a photograph of tracks like these. \"Your fox learnt to fly,\" "
                    "she wrote. You read it in a taxi, put the phone away, and answered an email. Now you are "
                    "standing where she stood, and the message arrives six weeks late.\n\n"
                    "The tracks are not a job. The camera is. You fetch the split log, the screwdriver, the "
                    "meter and the spare batteries. Its casing is undamaged. The battery sits properly and "
                    "reads full, but the camera is dead. The casing is colder than the air. You feel it through "
                    "your gloves. With a new battery, the green light comes on at once.\n\n"
                    "On your phone, you set the live feed beside saved frame one. The bracken matches. The fallen "
                    "trunk matches. The forked birch does not. It stood at the right edge. Now it stands left of "
                    "centre, and nearer. You flick between the pictures until your thumb aches. No camera fault "
                    "walks a birch thirty metres sideways.\n\n"
                    "You know the sensible things: photograph everything, drive south until the phone works, call "
                    "Nika. You only want to see the ground at the tree. It is two hundred metres north. You have a "
                    "head torch in your pocket, a compass clipped to your jacket, and half a day of light."
                )

            if self.current_room_id == "wood_track":
                log_tell(self.world_state, AnomalyID.HARE, player)
                return (
                    "The deterioration has come on by degrees: grey needles, branches dead right through, whole "
                    "trees standing with their bark on and nothing feeding on them. In the open track, a hare sits "
                    "with its forepaws together and ears upright, composed, facing you. It should have run. Frost "
                    "lies unmelted in its fur. Its chest does not flutter; there is no heartbeat shimmer, no "
                    "breath. It looks at you the way you look at someone you have been waiting for. You pass it "
                    "slowly. You do not look back."
                )

            if self.current_room_id == "old_woods":
                log_tell(self.world_state, AnomalyID.STONE_FORMATIONS, player)
                return (
                    "The deer path is not there. No droppings, no browse line, no break in the moss. "
                    "The route behind you has the same closed look as everything else. The forest has been emptied. "
                    "Every animal instinct you have says the same word: back."
                )

        if mode == "listen" and self.current_room_id == "wood_track":
            log_tell(self.world_state, AnomalyID.HARE, player)
            return (
                "A winter forest should hold wings somewhere, snow slipping from a branch, claws in frost. "
                "You listen for the panicked drag of a living thing. Nothing. Even the hare does not breathe."
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
                "The door gives under your weight and you fall into warmth. It swings "
                "shut behind you, and the cold is gone. The fire is burning low and steady. Not "
                "freshly lit. The logs have collapsed inward and glow along their "
                "centres, hours old, tended. The square table. The enamel sink with its "
                "crack. The same scorch mark on the hearth stone. A towel hangs warming "
                "over the rail by the stove, and on the table, waiting, stands a mug.\n\n"
                "None of it is strange to you yet. Inside, says your whole body.\n\n"
                "Nika is at the table, the old green book open under one hand. She is on "
                "her feet before she has finished speaking, a chair scraping back, three "
                "steps.\n"
                "\"Christ. What happened to you?\""
            )

        if stage == "tended":
            return (
                "Your face has been cleaned, chin steadied between finger and thumb, "
                "short businesslike strokes that hurt exactly as much as they had to "
                "and no more. Nika looks into one eye and then the other, holding up "
                "a finger. Follow it. Look at me. How many. She is deciding things "
                "about you, and she has not finished deciding. The kettle hisses on."
            )

        if stage == "seated":
            return (
                "The chair is close enough to the fire that heat has reached your torn "
                "sleeve. The mug in front of you is steaming, not yet tasted.\n"
                "Nika watches from the other side of the table, wearing the scowl she "
                "uses when worry has become a job."
            )

        if stage == "complete":
            additions = []
            if world_state.wrongness.has(AnomalyID.FROST_WOOD_GRAIN.value):
                additions.append(
                    "At the window, frost branches from a centre in the grain of split wood."
                )
            if world_state.wrongness.has(AnomalyID.KNUCKLES_BIRCH.value):
                additions.append(
                    "Nika reaches for a plate. The white scar at her thumb is only a scar."
                )
            if world_state.wrongness.has(AnomalyID.DELAYED_SMILE.value):
                additions.append(
                    "When Nika smiles, the mouth moves a half-beat before the eyes."
                )

            seated = (
                "The blue mug is warm in your hands. Nika puts a pan on the stove and "
                "talks in short runs with work in them. You let the evening stay easy."
            )
            if not additions:
                return seated
            return seated + "\n\n" + "\n".join(additions)

        if stage == "consented":
            return (
                "The door is closed. You chose the warm room.\n"
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
                    "Below you, the breathing keeps its identical measure."
                )
            if world_state.wrongness.has(AnomalyID.BLACK_BOARDS.value):
                lines.append(
                    "Along the floor, where the light is lowest, the boards hold their black."
                )
            if world_state.wrongness.has(AnomalyID.PHONE_DARK.value):
                lines.append("Your phone lies where you left it. Dark all through.")
            if world_state.wrongness.has(AnomalyID.WRONG_TINS.value):
                lines.append(
                    "The tins stand by the stove. Your wine is in the cabin you left."
                )
            if stage == "night":
                lines.append(
                    "The knowing is finished. You lie awake in the warmth and wait for grey."
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
            render_line((26, "Birch Thicket", visited("deer_path"))),
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
                (15, "||", connected("cabin_grounds_main", "cabin_main")),
            ),
            render_line(
                (0, "Konttori", visited("konttori")),
                (8, " - ", connected("konttori", "cabin_main")),
                (11, "The Cabin", visited("cabin_main")),
                (20, " - ", connected("cabin_main", "bedroom")),
                (23, "Bedroom", visited("bedroom")),
            ),
            render_line((15, "|", connected("cabin_main", "cabin_clearing"))),
            render_line((10, "The Clearing", visited("cabin_clearing"))),
            render_line((15, "|", connected("cabin_clearing", "wilderness_start"))),
            render_line((10, "The Wilderness", visited("wilderness_start"))),
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
            additions.append("Firelight moves over the log walls. The room gives back a little heat.")
        else:
            additions.append("The hearth is cold. Your breath shows in the room.")
        if world_state.get("has_power", False):
            additions.append("The ceiling bulb burns weak and yellow.")
        else:
            additions.append("The ceiling bulb stays dark.")
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
