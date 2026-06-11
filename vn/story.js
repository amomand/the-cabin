/*
  The Cabin: First Night — authored scene graph.

  Voice: third person, present tense, terse, sensory, bleak. Sentences land
  short. Elli is named; the player guides her, but is not her. The Lyer is
  never named, never explained — only presence, attention, and wrongness.

  Structure: braided, not branching. Choices fork into one- or two-beat
  reactions, then rejoin. Hidden state (fear / attention / anchor) decides
  the ending; it is never shown to the player.

  Scene shape:
    bg      — { type, image? }  (or a function of state). `image` is an
              optional file in assets/ that replaces the procedural plate.
    text    — array of paragraphs (or a function of state). <em>…</em> ok.
    next    — scene id to advance to on a tap (a paced "continue" beat)
    choices — [{ label, effects?, set?, goto, show? }]
    atmosphere — scene baseline visual mood: { cold?, warm?, fog? } 0..1
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

const STORY = {
  start: "title",
  scenes: {

    // ---- Title --------------------------------------------------------
    title: {
      kind: "title",
      bg: { type: "drive_dusk" },
      atmosphere: ATMOSPHERE.driveDusk,
      titleText: "The Cabin",
      subtitle: "First Night",
      blurb: "One arrival. One cabin.\nSeveral ways to be noticed.",
      begin: "arrival_1",
    },

    // ---- Scene 1: Arrival --------------------------------------------
    arrival_1: {
      bg: { type: "drive_dusk" },
      atmosphere: ATMOSPHERE.driveDusk,
      text: [
        "The gravel drive narrows as it leaves the road. The tyres go quiet under the trees, and Elli cuts the engine.",
        "The car ticks as it cools. Outside, the air is cold and unmoving. Frost glazes the ground in brittle patches, catching what little light is left.",
      ],
      next: "arrival_attention",
    },

    arrival_attention: {
      bg: { type: "drive_dusk" },
      atmosphere: ATMOSPHERE.driveDusk,
      text: [
        "She keeps her hands on the wheel. Somewhere past the bend, the cabin waits. Hers now, on paper at least, though it never quite felt that way.",
        "She had not planned to come back this year. But the northern camera blurred, and then went dark, and then so did the others. Nothing since.",
      ],
      choices: [
        { label: "Sit a moment longer.", effects: { anchor: +8, fear: -4 }, goto: "arrival_react_sit" },
        { label: "Check the phone for a signal.", effects: { fear: +4 }, set: { no_signal: true }, goto: "arrival_react_phone" },
        { label: "Step out into the cold.", goto: "arrival_react_step" },
      ],
    },

    arrival_react_sit: {
      bg: { type: "drive_dusk" },
      atmosphere: ATMOSPHERE.driveDusk,
      text: [
        "For a moment she just breathes. The forest holds still around the car, patient — the way a held breath is patient.",
      ],
      next: "arrival_walk",
    },
    arrival_react_phone: {
      bg: { type: "drive_dusk" },
      atmosphere: ATMOSPHERE.driveDusk,
      text: [
        "The phone hunts for reception and finds none. The little bars stay empty. She pockets it and tells herself it does not matter.",
      ],
      next: "arrival_walk",
    },
    arrival_react_step: {
      bg: { type: "drive_dusk" },
      atmosphere: ATMOSPHERE.driveDusk,
      text: [
        "She steps out and pulls her jacket tight. The cold takes the warmth from her hands almost at once.",
      ],
      next: "arrival_walk",
    },

    arrival_walk: {
      bg: { type: "drive_dusk" },
      atmosphere: ATMOSPHERE.driveDusk,
      text: [
        "The driveway curves away from the car and into the forest, between pine and birch. The trees lean inward, the way they always have.",
        "Their branches vanish upward into the dark. Beyond them the forest thickens into something she cannot see into at all.",
      ],
      choices: [
        { label: "Keep your eyes on the path.", effects: { fear: -2, attention: -4 }, set: { eyes_down: true }, goto: "arrival_door" },
        { label: "Look into the trees.", effects: { fear: +10, attention: +12 }, set: { looked_in: true }, goto: "arrival_look" },
      ],
    },

    arrival_look: {
      bg: { type: "drive_dusk" },
      atmosphere: ATMOSPHERE.driveDusk,
      text: [
        "She looks. Black trunks, pale birch, the spaces between them deeper than they ought to be.",
        "Nothing moves. Nothing needs to. The looking is enough — and she feels, for no reason she could name, that the looking goes both ways.",
      ],
      next: "arrival_door",
    },

    arrival_door: {
      bg: { type: "drive_dusk" },
      atmosphere: ATMOSPHERE.driveDusk,
      text: [
        "The forest swallows the drive whole before the cabin finally shows itself — a darker shape against darker trees.",
        "Elli climbs the last stretch, her breath faint in the air, and reaches the door. It groans as it opens. The same low, drawn-out sound it always made.",
      ],
      next: "inside_1",
    },

    // ---- Scene 2: Inside ---------------------------------------------
    inside_1: {
      bg: { type: "cabin_interior_dark" },
      atmosphere: ATMOSPHERE.interiorDark,
      text: [
        "Inside, the smell arrives first. Dry wood. Dust. Damp pine needles. Beneath it, softer and older, is smoke — not the clean scent of a hearth, but something sunk deep in the grain of the walls.",
        "The floorboards creak too loudly in the small space. The table stands where it always stood. The enamel sink catches a sliver of weak light from the little window.",
      ],
      next: "inside_switch",
    },

    inside_switch: {
      bg: { type: "cabin_interior_dark" },
      atmosphere: ATMOSPHERE.interiorDark,
      text: [
        "She reaches out without looking and flicks the light switch. She knows exactly where it is.",
        "Nothing. No hum, no glow. Just the dark, and the cold coming up through the floor.",
      ],
      choices: [
        { label: "Light the stove.", effects: { health: +10, fear: -4, attention: +8 }, set: { stove_lit: true }, goto: "inside_stove" },
        { label: "Leave it dark and stay small.", effects: { fear: +6, attention: -4 }, set: { stayed_dark: true }, goto: "inside_dark" },
      ],
    },

    inside_stove: {
      bg: { type: "cabin_interior_stove" },
      atmosphere: ATMOSPHERE.interiorStove,
      text: [
        "She feeds the stove and strikes a match. The fire catches low and orange, and the room leans into the light.",
        "Warmth, at last. But the glow throws her shadow long across the wall, and the windows turn to black mirrors that anything outside could read like a page.",
      ],
      next: "inside_memory",
    },
    inside_dark: {
      bg: { type: "cabin_interior_dark" },
      atmosphere: ATMOSPHERE.interiorDark,
      text: [
        "She leaves the stove cold. Better to stay small in the dark than to light a beacon in a black window.",
        "The chill settles into her hands and her knees. She waits for her eyes to find the shapes of the room, and slowly they do.",
      ],
      next: "inside_memory",
    },

    inside_memory: {
      bg: (s) => ({ type: s.flags.stove_lit ? "cabin_interior_stove" : "cabin_interior_dark" }),
      atmosphere: (s) => (s.flags.stove_lit ? ATMOSPHERE.interiorStove : ATMOSPHERE.interiorDark),
      text: [
        "Standing there, she remembers being nine, maybe ten. Winter. Waking in the dark to a sound she could not place — scraping, rhythmic, like something dragged slowly across the floor.",
        "Her parents said it was the trees. The ice settling. She accepted it, because the other thing was unthinkable. But it had been inside. She never told them.",
        "Her grandmother's voice comes back, casual over the table: <em>Of course, it wasn't this cabin back then. My grandparents had the old one, near the slope — before the forest moved.</em>",
      ],
      next: "inside_memory_choice",
    },

    inside_memory_choice: {
      bg: (s) => ({ type: s.flags.stove_lit ? "cabin_interior_stove" : "cabin_interior_dark" }),
      atmosphere: (s) => (s.flags.stove_lit ? ATMOSPHERE.interiorStove : ATMOSPHERE.interiorDark),
      text: [
        "Before the forest moved. The light at the window seems dimmer now. The smell of smoke, stronger and closer.",
      ],
      choices: [
        { label: "Tell yourself it was the trees.", effects: { fear: -8, anchor: -8 }, set: { denied: true }, goto: "disturbance_1" },
        { label: "Let yourself remember.", effects: { fear: +10, attention: +6, anchor: +4 }, set: { remembered: true }, goto: "disturbance_1" },
      ],
    },

    // ---- Scene 3: Disturbance ----------------------------------------
    disturbance_1: {
      bg: (s) => ({ type: s.flags.stove_lit ? "cabin_interior_stove" : "cabin_interior_dark" }),
      atmosphere: (s) => (s.flags.stove_lit ? ATMOSPHERE.interiorStove : ATMOSPHERE.interiorDark),
      text: (s) => [
        "She shakes her head, and the present snaps back. The cabin is just a cabin. Cold timber. Her own breath.",
        "Then — from the floor, or under it — the sound. Scraping. Rhythmic. Slow. The exact sound, dragged across the boards, the way it was when she was nine.",
        s.flags.stove_lit
          ? "The firelight shivers. Her shadow on the wall does not shiver with it."
          : "In the dark she cannot tell how close it is. Only that it is closer than the door.",
      ],
      next: "disturbance_choice",
    },

    disturbance_choice: {
      bg: (s) => ({ type: s.flags.stove_lit ? "cabin_interior_stove" : "cabin_interior_dark" }),
      atmosphere: (s) => (s.flags.stove_lit ? ATMOSPHERE.interiorStove : ATMOSPHERE.interiorDark),
      text: [
        "It stops. The silence after is worse — too clean, too deliberate, as if the room is listening for what she will do.",
        "And then, low, from the direction of the window, something says her name. Once. In a voice she almost knows.",
      ],
      choices: [
        { label: "Pretend you did not hear your name.", effects: { fear: +8, anchor: -8, attention: -6 }, set: { pretended: true }, goto: "consequence" },
        { label: "Lock the door and wait.", effects: { fear: +6, attention: -2, anchor: +4 }, set: { locked: true }, goto: "consequence" },
        { label: "Call out into the dark.", effects: { fear: +12, attention: +25 }, set: { called: true }, goto: "consequence" },
        { label: "Go to the window and look.", effects: { fear: +14, attention: +15 }, set: { looked_window: true }, goto: "consequence" },
      ],
    },

    // ---- Scene 4: Consequence (ending) -------------------------------
    consequence: {
      kind: "ending",
      bg: (s) => ({ type: s.attention >= 30 ? "consequence_wrong" : "consequence_quiet" }),
      atmosphere: (s) => (s.attention >= 30 ? ATMOSPHERE.wrong : ATMOSPHERE.quietMorning),
      title: (s) => (s.attention >= 30 ? "Noticed" : "The Long Quiet"),
      text: (s) =>
        s.attention >= 30
          ? [
              "Outside the window the drive is gone. The car is gone. There are only trees, closer than they were, leaning the way they lean in the part of the forest she was told never to walk into.",
              "This is not where she drove to. It has not been, for some time.",
              "The scraping starts again, behind her now, unhurried. It has all night. It has had every night. Elli does not turn around.",
              "The cabin, at last, has her full attention. She has its.",
            ]
          : [
              "She locks the door and sits with her back to the cold stove, knees drawn up, watching the black window until the black goes grey.",
              "Morning comes the way it always does here — without warning, without warmth. The forest stands exactly where it stood. The scraping does not come again.",
              "She tells herself she imagined it. By the time she reaches the car, she has almost succeeded.",
              "Behind her, the cabin keeps very still. It can wait. It is good at waiting.",
            ],
    },
  },
};
