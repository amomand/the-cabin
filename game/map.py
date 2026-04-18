
from __future__ import annotations

from typing import Dict, Tuple, Optional

from game.location import Location
from game.room import Room
from game.requirements import WorldFlagTrue
from game.item import create_items
from game.wildlife import create_wildlife, get_random_wildlife
from game.world_state import WorldState


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
                "The clearing is wrong. The driveway is gone. No car. The familiar treeline, the pines you have known since childhood, "
                "is replaced by ancient, towering, interlocking trees, too dark and too close. "
                "The ground is frozen black. The air has weight. The sky above is white and featureless, as if painted on.\n\n"
                "Nika stands beside you on the threshold. Her face has gone white. Her hands grip the door frame.\n"
                "\"This isn't where I drove to,\" she says. Very quiet. Very flat."
            ),
            wrong_exits={
                # No way back to the real wilderness from the wrong clearing.
                # The cabin remains. A track leads deeper in.
                "cabin": ("cabin_interior", "cabin_main"),
                "north": ("cabin_grounds", "wood_track"),
                "deeper": ("cabin_grounds", "wood_track"),
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
            ],
            wildlife=[],  # No wildlife inside the cabin
            max_wildlife=0,
            wildlife_pool={},
            description_fn=self._cabin_description,
            wrong_description=(
                "The door swings shut behind you. The fire is burning, low and steady, tended. "
                "The cabin is warm. The square table, the enamel sink, the small window. "
                "Every detail correct. A towel warms by the stove. A mug waits on the table, "
                "made exactly how you take it.\n\n"
                "Nika is there. Sitting at the table, leafing through the old paperback from the shelf. "
                "She looks up and takes you in, bloody nose and torn jacket and wild face. "
                "The place is not merely familiar. It is prepared for you."
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
        cabin_grounds_room.on_enter = self._on_enter_grounds  # type: ignore[assignment]

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
        )

        lakeside = Room(
            name="Lakeside",
            description=(
                "You stand by the edge of a dark lake. The water is still and black.\n"
                "A path leads further into the woods."
            ),
            room_id="lakeside",
            items=[],  # Remove firewood from lakeside
            wildlife=get_random_wildlife(self.wildlife, max_count=1),  # Add random wildlife
            max_wildlife=1,
            wildlife_pool=self.wildlife,
        )

        wood_track = Room(
            name="Wood Track",
            description=(
                "A narrow track winds through the dense woods. The trees press close on either side.\n"
                "The path is well-worn but overgrown in places."
            ),
            room_id="wood_track",
            items=[self.items["knife"]],  # Add knife to wood track
            wildlife=get_random_wildlife(self.wildlife, max_count=2),  # More wildlife in deeper woods
            max_wildlife=2,
            wildlife_pool=self.wildlife,
            description_fn=self._wood_track_description,
            wrong_description=(
                "The wrong woods. The trees are ancient and interlocking, the ground frozen hard. "
                "Nika walks ahead of you, pushing through a low branch. For a moment, two seconds, maybe three, "
                "her hand where it grips the branch is not a hand. The fingers are too long. The joints bend the wrong way. "
                "The skin has the texture and colour of birch bark, and where her knuckles should be there are knots in the wood.\n"
                "Then the branch releases and she turns back and her hand is her hand.\n\n"
                "\"You alright?\" Nika says."
            ),
            wrong_exits={
                "south": ("cabin_grounds", "cabin_clearing"),
                "north": ("cabin_grounds", "old_woods"),
                "deeper": ("cabin_grounds", "old_woods"),
            },
        )
        wood_track.on_enter = self._on_enter_wood_track  # type: ignore[assignment]

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
            wrong_description=(
                "The forest is empty. Completely empty. No tracks, no droppings, no movement at the edges. "
                "Just nothing, as though everything that lived here has been taken or made into something else.\n\n"
                "Nika has stopped walking. She stands at the edge of a small clearing, looking at something you cannot see from here. "
                "Very still. Not Nika-still. The stillness of something held in place."
            ),
            wrong_description_fn=self._wrong_old_woods_description,
            wrong_exits={
                "south": ("cabin_grounds", "wood_track"),
                "track": ("cabin_grounds", "wood_track"),
            },
        )
        old_woods.on_enter = self._on_enter_old_woods  # type: ignore[assignment]

        # Optional example: gate leaving the cabin interior unless power restored (diegetic placeholder)
        # Not applied globally here; instead, we add a requirement on a specific exit if desired.

        # Register rooms to locations
        wilderness.add_room(start_room)
        cabin_grounds.add_room(clearing)
        cabin_grounds.add_room(cabin_grounds_room)
        cabin_grounds.add_room(sauna)
        cabin_grounds.add_room(lakeside)
        cabin_grounds.add_room(wood_track)
        cabin_grounds.add_room(old_woods)
        cabin_interior.add_room(cabin)
        cabin_interior.add_room(konttori)
        cabin_interior.add_room(bedroom)

        # Room-level exits: direction -> (target_location_id, target_room_id)
        # Linear progression: Wilderness -> Clearing -> Cabin -> Konttori -> Cabin Grounds -> Lakeside -> Wood Track -> Old Woods
        start_room.exits = {"north": ("cabin_grounds", "cabin_clearing")}
        clearing.exits = {
            "south": ("wilderness", "wilderness_start"),
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
            "north": ("cabin_grounds", "wood_track"),
            "grounds": ("cabin_grounds", "cabin_grounds_main"),
        }
        wood_track.exits = {
            "south": ("cabin_grounds", "lakeside"),
            "north": ("cabin_grounds", "old_woods"),
            "lakeside": ("cabin_grounds", "lakeside"),
        }
        old_woods.exits = {
            "south": ("cabin_grounds", "wood_track"),
            "track": ("cabin_grounds", "wood_track"),
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

        target_location_id, target_room_id = exits[direction]
        target_was_visited = target_room_id in self.visited_rooms

        # Move
        self.current_location_id = target_location_id
        self.current_room_id = target_room_id
        self.current_room_been_here_before = target_was_visited

        # Mark the new room as visited
        self.visited_rooms.add(target_room_id)

        # Trigger on-enter hooks
        self.current_room.on_enter(player, self.world_state)

        return True, ""

    # --- Act II scripted content ---------------------------------------------

    def _trigger_lyer_encounter(self, player) -> Tuple[bool, str]:
        """The Act II climax. Flips into the wrong layer and drops Elli at the Wrong Cabin."""
        self.world_state.lyer_encountered = True

        # Bleed some fear and health from the tree collision.
        if player is not None:
            try:
                player.fear = min(100, getattr(player, "fear", 0) + 40)
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

    # --- Act II anomalies: description + wrongness logging --------------------

    @staticmethod
    def _grounds_description(player, world_state, base: str) -> str:
        if not world_state.first_morning:
            return base
        return (
            base
            + "\n\nNear the north edge, on the open ground, a line of fox tracks. "
            "Neat, trotting, and then gone. The last print pressed firm, and beyond it nothing. "
            "No turn, no scatter. Just the end of a fox."
        )

    @staticmethod
    def _on_enter_grounds(player, world_state) -> None:
        if world_state.first_morning:
            world_state.wrongness.add(
                "fox_tracks",
                "a line of fox tracks that stops mid-stride",
            )

    @staticmethod
    def _wood_track_description(player, world_state, base: str) -> str:
        if not world_state.first_morning:
            return base
        return (
            base
            + "\n\nA hare sits in the middle of the path, forepaws together, ears upright. "
            "Frost on its fur. No breath in its flanks. It looks at you the way a person looks at someone they've been expecting."
        )

    @staticmethod
    def _on_enter_wood_track(player, world_state) -> None:
        if world_state.first_morning:
            world_state.wrongness.add(
                "hare",
                "a hare that does not flee, does not breathe",
            )

    @staticmethod
    def _old_woods_description(player, world_state, base: str) -> str:
        if not world_state.first_morning:
            return base
        return (
            base
            + "\n\nThe birch here are thinner. Pine needles on the ground, grey not brown. "
            "A branch brushes your arm and snaps, dry, pale as bone inside. "
            "Half-buried in the moss, stone formations, arranged, old. The engravings are almost gone. "
            "The cold comes from underneath."
        )

    @staticmethod
    def _on_enter_old_woods(player, world_state) -> None:
        # Real layer: first-morning atmosphere logs the stones.
        if world_state.is_wrong_layer():
            # Wrong layer: the correction-turn fires on entry. This is Act IV's
            # definitive tell, and it unlocks Recognition.
            if not world_state.recognition:
                world_state.wrongness.add(
                    "correction_turn",
                    "Nika's stillness, and the turn that followed - a correction, not a return",
                )
                world_state.recognition = True
            return
        if world_state.first_morning:
            world_state.wrongness.add(
                "stone_formations",
                "half-buried stone formations, arranged, older than the family",
            )

    @staticmethod
    def _wrong_cabin_description(player, world_state, base: str) -> str:
        """Compose the Wrong Cabin description with any tells the player has already observed."""
        additions = []
        if world_state.wrongness.has("frost_wood_grain"):
            additions.append(
                "On the window, the frost still patterns like wood grain - growth rings spreading from some unseen centre."
            )
        if world_state.wrongness.has("knuckles_birch"):
            additions.append(
                "Nika's hand tightens on the mug. You do not look at it directly."
            )
        if world_state.wrongness.has("delayed_smile"):
            additions.append(
                "She smiles at something you said. The smile arrives a fraction late, as if laid across the face."
            )
        if not additions:
            return base
        return base + "\n\n" + "\n".join(additions)

    @staticmethod
    def _wrong_old_woods_description(player, world_state, base: str) -> str:
        if world_state.recognition:
            return (
                base
                + "\n\n\"Nika.\"\n"
                "Nothing.\n"
                "\"Nika.\"\n"
                "She turns. The smile is right. The voice, when she speaks, is right. "
                "\"Sorry. Thought I saw something.\"\n"
                "But the turn was wrong. Not the motion of a person returning from thought. Something else. "
                "A correction. A system returning to its prior state.\n\n"
                "You know. You have known for a while. You just hadn't let yourself finish the knowing."
            )
        return base

    def display_map(self, visited_rooms: set) -> str:
        """Display an ASCII map of visited areas.
        
        Args:
            visited_rooms: Set of room IDs the player has visited
            
        Returns:
            ASCII map string
        """
        # Define the room layout and connections
        room_layout = [
            ("wilderness_start", "The Wilderness"),
            ("cabin_clearing", "The Clearing"),
            ("cabin_main", "The Cabin"),
            ("konttori", "Konttori"),
            ("cabin_grounds_main", "Cabin Grounds"),
            ("lakeside", "Lakeside"),
            ("wood_track", "Wood Track"),
            ("old_woods", "Old Woods")
        ]
        
        # Special locations that use double pipes
        special_locations = {"cabin_main", "konttori", "cabin_grounds_main"}
        
        map_lines = []
        
        for i, (room_id, room_name) in enumerate(room_layout):
            # Only show visited rooms
            if room_id not in visited_rooms:
                continue
                
            # Add room name
            map_lines.append(room_name)
            
            # Add connection to next room (if there is one and it's visited)
            if i < len(room_layout) - 1:
                next_room_id = room_layout[i + 1][0]
                if next_room_id in visited_rooms:
                    # Use double pipes ONLY when BOTH rooms are special locations
                    if room_id in special_locations and next_room_id in special_locations:
                        map_lines.append("||")
                    else:
                        map_lines.append(" |")
                else:
                    # No connection if next room not visited
                    map_lines.append("")
            else:
                # Last room has no connection
                map_lines.append("")
        
        # Filter out empty lines and join
        map_lines = [line for line in map_lines if line.strip()]
        
        return "\n".join(map_lines)

    def get_visited_rooms(self) -> set:
        """Get a set of all room IDs that have been visited."""
        return self.visited_rooms.copy()

    @staticmethod
    def _cabin_description(player, world_state, base: str) -> str:
        """Dynamic cabin description based on world state."""
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
