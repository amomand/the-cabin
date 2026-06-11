/*
  The Cabin: First Night — authored scene graph.

  Voice: third person, present tense, terse, sensory, bleak. Sentences land
  short. Elli is named; the player guides her, but is not her. The Lyer is
  never named, never explained — only presence, attention, and wrongness.

  Structure: braided, not branching. Choices fork into one- or two-beat
  reactions, then rejoin. Attention chooses the ending; fear, anchor, and
  flags colour atmosphere, sound, and variant lines. None are shown to the
  player as meters.

  Scene shape:
    bg      — { type, image? }  (or a function of state). `image` is an
              optional file in assets/ that replaces the procedural plate.
    text    — array of paragraphs (or a function of state). <em>…</em> ok.
    next    — scene id to advance to on a tap (a paced "continue" beat)
    choices — [{ label, effects?, set?, goto, show? }]
    atmosphere — scene baseline visual mood: { cold?, warm?, fog? } 0..1
    sound   — optional authored sound cue id
    kind    — "title" | "ending" for the framed cards
*/

const ATMOSPHERE = {
  driveDusk: { cold: 0.26, fog: 0.45 },
  interiorDark: { cold: 0.5, fog: 0.22 },
  interiorStove: { warm: 0.44, fog: 0.18 },
  windowNight: { cold: 0.58, fog: 0.34 },
  quietMorning: { cold: 0.32, fog: 0.2 },
  wrong: { cold: 0.68, fog: 0.42 },
};

const ENDING_ATTENTION = 30;
const artBg = (type) => ({ type, image: `assets/${type}.webp` });
const cabinBg = (s) => artBg(s.flags.stove_lit ? "cabin_interior_stove" : "cabin_interior_dark");
const cabinAtmosphere = (s) => (s.flags.stove_lit ? ATMOSPHERE.interiorStove : ATMOSPHERE.interiorDark);
const noticed = (s) => s.attention >= ENDING_ATTENTION;

function arrivalDoorLine(s) {
  if (s.flags.looked_in) {
    return "When Elli looks back to the path, the cabin has found its place ahead of her: a darker shape against darker trees.";
  }
  if (s.flags.eyes_down) {
    return "Elli keeps her eyes on the path until the path becomes steps, and the steps become the door.";
  }
  return "The forest swallows the drive whole before the cabin finally shows itself: a darker shape against darker trees.";
}

function disturbanceOpening(s) {
  if (s.flags.denied) {
    return "She tries to lay the old answer over it: trees, ice, settling wood. The answer will not lie flat.";
  }
  if (s.flags.remembered) {
    return "She lets the memory stand. The room grows smaller around it.";
  }
  return "The room grows smaller around the thing she has not named.";
}

function quietEndingText(s) {
  const opening = s.flags.locked
    ? "The bolt stays in its socket until morning. Elli sits with her back to the door, knees drawn up, listening to the wood remember the scrape."
    : s.flags.pretended
      ? "Elli sits very still and gives the voice no answer. The room seems to accept this, for now."
      : "She sits with her back to the cold stove, knees drawn up, watching the black window until the black goes grey.";

  const denial = s.flags.denied
    ? "By dawn the old explanation has returned: trees, ice, settling wood. It fits badly, but she carries it anyway."
    : "Morning comes the way it always does here: without warning, without warmth.";

  const anchor = s.anchor < 92
    ? "At the threshold she has to make herself name the ordinary things: latch, hinge, road, car."
    : "She tells herself she imagined it. By the time she reaches the car, she has almost succeeded.";

  return [
    opening,
    `${denial} The forest stands exactly where it stood. The scraping does not come again.`,
    anchor,
    "Behind her, the cabin keeps very still. It can wait. It is good at waiting.",
  ];
}

function noticedEndingText(s) {
  const opening = s.flags.looked_window
    ? "The window gives her the truth in pieces. No drive. No car. Only trees, pressed close enough to breathe on the glass."
    : s.flags.called
      ? "Something outside answers without a sound. The drive is gone. The car is gone. The trees have come close while Elli was speaking."
      : "Outside the window the drive is gone. The car is gone. There are only trees, closer than they were, leaning the way they lean in the part of the forest she was told never to walk into.";

  const memory = s.flags.denied
    ? "The thing she refused to remember has remembered her instead."
    : "This is not where she drove to. It has not been, for some time.";

  const ending = s.flags.called
    ? "It has her voice now, small and familiar in the dark. Elli does not answer again."
    : "The cabin, at last, has her full attention. She has its.";

  return [
    opening,
    memory,
    "The scraping starts again, behind her now, unhurried. It has all night. It has had every night.",
    ending,
  ];
}

const STORY = {
  start: "title",
  endingAttention: ENDING_ATTENTION,
  scenes: {

    // ---- Title --------------------------------------------------------
    title: {
      kind: "title",
      bg: artBg("drive_dusk"),
      atmosphere: ATMOSPHERE.driveDusk,
      titleText: "The Cabin",
      subtitle: "First Night",
      blurb: "One arrival. One cabin.\nSeveral ways to be noticed.",
      begin: "arrival_1",
    },

    // ---- Scene 1: Arrival --------------------------------------------
    arrival_1: {
      bg: artBg("drive_dusk"),
      atmosphere: ATMOSPHERE.driveDusk,
      text: [
        "The gravel drive narrows as it leaves the road. The tyres go quiet under the trees, and Elli cuts the engine.",
        "The car ticks as it cools. Outside, the air is cold and unmoving. Frost glazes the ground in brittle patches, catching what little light is left.",
      ],
      next: "arrival_attention",
    },

    arrival_attention: {
      bg: artBg("drive_dusk"),
      atmosphere: ATMOSPHERE.driveDusk,
      text: [
        "She keeps her hands on the wheel. Somewhere past the bend, the cabin waits. Hers now, on paper at least, though it never quite felt that way.",
        "She had not planned to come back this year. But the northern camera blurred, and then went dark, and then so did the others. Nothing since.",
      ],
      choices: [
        { label: "Elli sits a moment longer.", effects: { anchor: +8, fear: -4 }, goto: "arrival_react_sit" },
        { label: "Elli checks the phone for a signal.", effects: { fear: +4 }, set: { no_signal: true }, goto: "arrival_react_phone" },
        { label: "Elli steps out into the cold.", goto: "arrival_react_step" },
      ],
    },

    arrival_react_sit: {
      bg: artBg("drive_dusk"),
      atmosphere: ATMOSPHERE.driveDusk,
      text: [
        "For a moment she just breathes. The forest holds still around the car, patient — the way a held breath is patient.",
      ],
      next: "arrival_walk",
    },
    arrival_react_phone: {
      bg: artBg("drive_dusk"),
      atmosphere: ATMOSPHERE.driveDusk,
      text: [
        "The phone hunts for reception and finds none. The little bars stay empty. She pockets it and tells herself it does not matter.",
      ],
      next: "arrival_walk",
    },
    arrival_react_step: {
      bg: artBg("drive_dusk"),
      atmosphere: ATMOSPHERE.driveDusk,
      text: [
        "She steps out and pulls her jacket tight. The cold takes the warmth from her hands almost at once.",
      ],
      next: "arrival_walk",
    },

    arrival_walk: {
      bg: artBg("drive_dusk"),
      atmosphere: ATMOSPHERE.driveDusk,
      text: [
        "The driveway curves away from the car and into the forest, between pine and birch. The trees lean inward, the way they always have.",
        "Their branches vanish upward into the dark. Beyond them the forest thickens into something she cannot see into at all.",
      ],
      choices: [
        { label: "Elli keeps her eyes on the path.", effects: { fear: -2, attention: -4 }, set: { eyes_down: true }, goto: "arrival_door" },
        { label: "Elli looks into the trees.", effects: { fear: +10, attention: +12 }, set: { looked_in: true }, goto: "arrival_look" },
      ],
    },

    arrival_look: {
      bg: artBg("drive_dusk"),
      atmosphere: ATMOSPHERE.driveDusk,
      text: [
        "She looks. Black trunks, pale birch, the spaces between them deeper than they ought to be.",
        "Nothing moves. Nothing needs to. The looking is enough — and she feels, for no reason she could name, that the looking goes both ways.",
      ],
      next: "arrival_door",
    },

    arrival_door: {
      bg: artBg("drive_dusk"),
      atmosphere: ATMOSPHERE.driveDusk,
      text: (s) => [
        arrivalDoorLine(s),
        "Elli climbs the last stretch, her breath faint in the air, and reaches the door. It groans as it opens. The same low, drawn-out sound it always made.",
      ],
      next: "inside_1",
    },

    // ---- Scene 2: Inside ---------------------------------------------
    inside_1: {
      bg: artBg("cabin_interior_dark"),
      atmosphere: ATMOSPHERE.interiorDark,
      text: (s) => [
        "Inside, the smell arrives first. Dry wood. Dust. Damp pine needles. Beneath it, softer and older, is smoke — not the clean scent of a hearth, but something sunk deep in the grain of the walls.",
        s.flags.no_signal
          ? "The phone is a black weight in her pocket. The floorboards creak too loudly in the small space. The table stands where it always stood."
          : "The floorboards creak too loudly in the small space. The table stands where it always stood. The enamel sink catches a sliver of weak light from the little window.",
      ],
      next: "inside_switch",
    },

    inside_switch: {
      bg: artBg("cabin_interior_dark"),
      atmosphere: ATMOSPHERE.interiorDark,
      text: [
        "She reaches out without looking and flicks the light switch. She knows exactly where it is.",
        "Nothing. No hum, no glow. Just the dark, and the cold coming up through the floor.",
      ],
      choices: [
        { label: "Elli lights the stove.", effects: { fear: -4, attention: +8 }, set: { stove_lit: true }, goto: "inside_stove" },
        { label: "Elli leaves it dark and stays small.", effects: { fear: +6, attention: -4 }, set: { stayed_dark: true }, goto: "inside_dark" },
      ],
    },

    inside_stove: {
      bg: artBg("cabin_interior_stove"),
      atmosphere: ATMOSPHERE.interiorStove,
      text: [
        "She feeds the stove and strikes a match. The fire catches low and orange, and the room leans into the light.",
        "Warmth, at last. But the glow throws her shadow long across the wall, and the windows turn to black mirrors that anything outside could read like a page.",
      ],
      next: "inside_memory",
    },
    inside_dark: {
      bg: artBg("cabin_interior_dark"),
      atmosphere: ATMOSPHERE.interiorDark,
      text: [
        "She leaves the stove cold. Better to stay small in the dark than to light a beacon in a black window.",
        "The chill settles into her hands and her knees. She waits for her eyes to find the shapes of the room, and slowly they do.",
      ],
      next: "inside_memory",
    },

    inside_memory: {
      bg: cabinBg,
      atmosphere: cabinAtmosphere,
      text: [
        "Standing there, she remembers being nine, maybe ten. Winter. Waking in the dark to a sound she could not place — scraping, rhythmic, like something dragged slowly across the floor.",
        "Her parents said it was the trees. The ice settling. She accepted it, because the other thing was unthinkable. But it had been inside. She never told them.",
        "Her grandmother's voice comes back, casual over the table: <em>Of course, it wasn't this cabin back then. My grandparents had the old one, near the slope — before the forest moved.</em>",
      ],
      next: "inside_memory_choice",
    },

    inside_memory_choice: {
      bg: cabinBg,
      atmosphere: cabinAtmosphere,
      text: [
        "Before the forest moved. The light at the window seems dimmer now. The smell of smoke, stronger and closer.",
      ],
      choices: [
        { label: "Elli tells herself it was the trees.", effects: { fear: -8, anchor: -8 }, set: { denied: true }, goto: "disturbance_1" },
        { label: "Elli lets herself remember.", effects: { fear: +10, attention: +6, anchor: +4 }, set: { remembered: true }, goto: "disturbance_1" },
      ],
    },

    // ---- Scene 3: Disturbance ----------------------------------------
    disturbance_1: {
      bg: cabinBg,
      atmosphere: cabinAtmosphere,
      sound: "scrape",
      text: (s) => [
        disturbanceOpening(s),
        "Then — from the floor, or under it — the sound. Scraping. Rhythmic. Slow. The exact sound, dragged across the boards, the way it was when she was nine.",
        s.flags.stayed_dark
          ? "The dark gives the sound no shape. That is worse. It could be anywhere."
          : s.flags.stove_lit
          ? "The firelight shivers. Her shadow on the wall does not shiver with it."
          : "In the dark she cannot tell how close it is. Only that it is closer than the door.",
      ],
      next: "disturbance_choice",
    },

    disturbance_choice: {
      bg: cabinBg,
      atmosphere: cabinAtmosphere,
      text: [
        "It stops. The silence after is worse — too clean, too deliberate, as if the room is listening for what she will do.",
        "And then, low, from the direction of the window, something says her name. Once. In a voice she almost knows.",
      ],
      choices: [
        { label: "Elli pretends she did not hear her name.", effects: { fear: +8, anchor: -8, attention: -6 }, set: { pretended: true }, goto: "disturbance_react_pretend" },
        { label: "Elli locks the door and waits.", effects: { fear: +6, attention: -2, anchor: +4 }, set: { locked: true }, goto: "disturbance_react_lock" },
        { label: "Elli calls out into the dark.", effects: { fear: +12, attention: +34 }, set: { called: true }, goto: "disturbance_react_call" },
        { label: "Elli goes to the window and looks.", effects: { fear: +14, attention: +36 }, set: { looked_window: true }, goto: "disturbance_react_window" },
      ],
    },

    disturbance_react_pretend: {
      bg: cabinBg,
      atmosphere: cabinAtmosphere,
      text: [
        "Elli keeps her breath shallow. The name fades into the window glass, but the shape of it stays in the room.",
        "Not answering is still an answer. She feels the room understand that.",
      ],
      next: "consequence",
    },

    disturbance_react_lock: {
      bg: cabinBg,
      atmosphere: cabinAtmosphere,
      text: [
        "The bolt slides home with a hard little click. It sounds too small for the night outside.",
        "Elli keeps one hand on the door until the wood stops trembling. Then she realises the door was not trembling.",
      ],
      next: "consequence",
    },

    disturbance_react_call: {
      bg: cabinBg,
      atmosphere: cabinAtmosphere,
      text: [
        "Elli says, \"Nika?\"",
        "Her voice enters the dark and does not come back. The window holds the shape of her reflection a second too long.",
      ],
      next: "consequence",
    },

    disturbance_react_window: {
      bg: artBg("window_night"),
      atmosphere: ATMOSPHERE.windowNight,
      text: [
        "Elli crosses the room without feeling the boards under her feet.",
        "At the window she waits. Breath gathers on the glass. The forest waits with her.",
      ],
      next: "disturbance_window_last",
    },

    disturbance_window_last: {
      bg: artBg("window_night"),
      atmosphere: ATMOSPHERE.windowNight,
      text: [
        "There is no car.",
      ],
      next: "consequence",
    },

    // ---- Scene 4: Consequence (ending) -------------------------------
    consequence: {
      kind: "ending",
      bg: (s) => artBg(noticed(s) ? "consequence_wrong" : "consequence_quiet"),
      atmosphere: (s) => (noticed(s) ? ATMOSPHERE.wrong : ATMOSPHERE.quietMorning),
      title: (s) => (noticed(s) ? "Noticed" : "The Long Quiet"),
      text: (s) => (noticed(s) ? noticedEndingText(s) : quietEndingText(s)),
    },
  },
};
