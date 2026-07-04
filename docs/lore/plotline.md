# The Cabin: Main Story Plotline

> Status: canon snapshot, taken 2026-07-03.
>
> This file mirrors the maintainer's living plotline in Obsidian
> (`Fiction Writing/The Cabin/The Cabin - Plotline.md`), which is the source
> of truth. If this file disagrees with a newer canon decision, the snapshot
> is stale and needs refreshing, not defending.
>
> The playable game realises this canon only partly. Act I and the Act II
> encounter (the turn, the run, the collision) match. From Act III onwards,
> v1 implements an earlier iteration of the story: the reunion treats Nika
> as real, and the game ends in the accept/refuse choice at the wrong-cabin
> threshold rather than The Escape. `README.md` and `docs/game_mechanics/`
> describe implemented behaviour; this document describes where the story is
> going.
>
> Some beats below are deliberately undecided: who or what says the word
> "Lyer" first, the exact shape of Act V, and the coda. Do not resolve them
> in game prose or docs without the maintainer.
>
> One deviation from the Obsidian text: the Background voicemail quote
> includes the "Don't go up on your own. Wait." line from the _No Further_
> ending, restored to this doc by PR #121 and currently missing from the
> Obsidian copy. The complete voicemail, opener included, lives in
> `game/actions/use.py` and `docs/game_mechanics/voicemail_miniquest.md`.

## Premise

Elli returns to her family cabin in the Finnish wilderness after the security cameras detect strange movement and then go dark. What begins as a quiet resettling into cabin life leads her into the old woods, into an encounter with the Lyer, and into the discovery that the boundaries between places, between safety and something ancient, are not what she thought.

---

## Background (established lore, not narrated directly)

The Lyer is ancient. It does not belong to any mythology. It lies in wait, and it lies. It does not chase. It seeps. It corrupts. Its presence brings unnatural cold, stillness, and a wrongness that accumulates rather than announces itself. Why it exists is unknown. It simply is, and the less understood about it, the worse it becomes. Its deepest weapon is not terror but intimacy: it does not invent fears, it finds yours and speaks them back to you. It offers comfort, warmth, safety. And all of it is a lie.

The cabin has been in Elli's family for generations. Her grandmother once mentioned, offhand, that her grandparents had "the old one, near the slope before the forest moved." The forest has moved before. The cabin was built at what was once a greater distance from the old woods. That distance has been shrinking for as long as anyone can remember.

The stone formations in the old woods are ancient, far older than the cabin, older than any recorded settlement in the area. Smoothed by centuries of weather, their engravings are almost gone, but they were deliberate. Arranged. No one knows who placed them or why. They are simply there, and they are old.

Elli's family have maintained the cabin for generations, though no one could say exactly why. What remains is habit: the cabin passed down, the instruction not to go too far, a vague obligation that none of them could name. Elli's grandmother was the last to have any real sense of it. She said nothing directly. She passed down the cabin and the instruction and the tone, and said nothing else.

Elli's childhood holds a buried memory: a scraping sound inside the cabin at night, something her parents explained away. She never told them she knew it was inside.

Elli lives in New York. Has for years. She works in publishing, or something adjacent to it, something that justifies the distance without quite explaining it. She left Finland after university, first to London, then further, then further again. Not running. Just not stopping. She is good at distance. Good at the practical management of a life lived far from the place that made her. She pays the cabin electricity remotely. She arranges maintenance through Nika. She comes back every few years, stays a week, does the things the cabin needs, and leaves before the quiet gets inside her.

She is competent, observant, private. She thinks before she speaks, often long enough that the moment has moved on. She is not cold. She is careful. There is a difference, though not everyone sees it.

Elli and Nika were inseparable as children. Not just close. The kind of childhood friendship that feels like a permanent fact, like family, like something that will simply always be there because it always has been. Summers at the cabin, swimming in the lake, barefoot in the woods, sleeping in the same room, the whole world reduced to the two of them and the forest and the water. Nika was the brave one. Elli was the one who noticed things. Together they were complete in the way only children can be, before they learn that completeness doesn't last.

Then Elli left. Not dramatically. She went to university, and then she didn't come back, and then another year passed, and then another. The friendship didn't break. It thinned. Texts instead of visits. Practical arrangements instead of conversation. The cabin as the only remaining thread between them, maintained out of obligation neither of them examined. Nika felt every millimetre of the distance. Elli told herself it was natural, that people grow apart, that this is what happens. She is still telling herself that.

Nika, Elli's childhood friend, still lives near Korpikylä. She works at the hardware store. She is direct, unsentimental, tough. She has already been to the cabin alone (the events of _No Further_) and knows something is deeply wrong. She left a voicemail for Elli: "Something's wrong with the cabin. I don't know what. Don't go up on your own. Wait. It's lying out there. Waiting." Nika did not name the thing. The local vocabulary in Korpikylä had been tried — at the bar one Friday someone offered "hiisi" and Matti said no — and had not reached it. The naming has been left for The Cabin to do, where the word will arrive through someone or something that has more reason to know it than Nika did. She does not come to the cabin again. The Lyer, however, spent time with her. It knows her. The shape of her, the sound of her, the weight of her grip. It also knows, from Nika, the shape of the person Nika misses. The outline of Elli is already in the Lyer's possession before Elli arrives.

---

## Act I: The Quiet Return

Elli arrives at the cabin. The driveway narrows, the trees lean in. She finds the cabin dark, cold, and the northern camera dead. She restores power at the fusebox, brings in wood, lights the fire, and begins the small practical rituals of reopening the place. She knows every step. Her hands know where things are before she looks. But she does it all with the slight formality of someone performing a remembered self, a woman reopening a place she has been leaving for twenty years. The entering-cabin scene plays, her childhood memory of the scraping, her grandmother's remark about the forest moving.

But this time the opening breathes. Elli settles in properly. She checks the actual bedroom, shakes out old bedding, fills the water buckets, and walks over to the separate sauna building as dusk comes down through the trees. She lights the stove, waits for the stones to heat, and sits alone in the steam while the little room glows around her. The lake is a dark plate between the trunks. For the first time since arriving, the place belongs to the part of her that loved it. The part she keeps at a distance.

Back in the main cabin, she makes a simple dinner, opens a bottle of wine, and lets herself enjoy the place. The wine is a New York habit, not a cabin one. This is the point of it, or used to be. The stillness outside reads, for a while, as peace rather than warning.

Only after that does the first thread catch.

**Beat: The voicemail.** In the warm after-dinner quiet, Elli checks her phone. There's a voicemail from Nika. It's terse, strained, unlike Nika. "Something's wrong with the cabin. I don't know what." Elli replays it. The word "waiting" hangs in the room. She and Nika haven't spoken properly in months. Their communication has been reduced to maintenance texts, brief and practical, the way a friendship sounds when neither person will say what happened to it. This voicemail is different. Nika sounds the way she sounded when they were young and something was actually wrong. That is what frightens Elli more than the words.

**Beat: The cameras.** She checks the stored camera footage. Three cameras are working. The northern one is dead. She reviews the last captured sequence. Five frames. A shape at the treeline. Tall, narrow, too close by the fourth image. In that fourth frame, the trees behind it have changed position. The fifth frame is black. The feed died.

**Beat: The bedroom.** Elli goes to bed in the real bedroom, under the heavy old covers, with wine warmth still in her and the smell of dry wood in the boards. She lies awake longer than she expected. The isolation feels complete now. Not hostile. Simply absolute. In the dark, she remembers the childhood scraping sound and the way her parents explained it away. She tells herself she'll check the northern edge in daylight, then decide what to do.

---

## Act II: Into the Woods

### The first morning
After the first proper night, Elli wakes to silence so complete she thinks for a second she's gone deaf. Then a log shifts in the hearth and sound returns, muffled. She steps outside. The forest is motionless. Not a branch, not a needle. The stillness has weight.

She walks the perimeter to check the northern side and finds tracks. Small, neat, trotting. Fox. They cross the open ground in a clean line and then stop. Mid-stride. Sharp and clear, the last print pressed firm into frozen ground, and beyond it nothing. No turn, no scatter. Just the end of a fox. She stares at them for a long time. Nika's text comes back to her, from weeks ago: *Your fox learned to fly.* She hadn't known what to make of it then. She doesn't know what to make of it now.

She could leave it alone. She doesn't. Nika's voicemail, the dead camera, and the old family instruction not to go too far have started to lean together into the same shape.

### The wood track and the dying forest
The path takes her past the lakeside and onto the wood track. The forest here is different. Not immediately. It's a slow deterioration. The birch are thinner. The pine needles on the ground are grey, not brown. A branch she brushes against snaps too easily, dry and brittle, the inside pale as bone.

There is nothing in the forest. That is what unsettles her first. No movement, no birdsong, no rustle in the undergrowth. Finnish forest is quiet, always has been, but it is populated quiet. Things move at the edges. Wings shift. Something bolts before you see it. Here there is nothing. The forest is still the way a room is still after everyone has left.

Then she sees the hare.

It is sitting on the path ahead of her. Not at the edge, not half-hidden in scrub. On the path, in the open, close enough that she should have startled it twenty paces ago. It is looking at her. Not with fear. Not with the coiled readiness of a hare about to run. Just looking, the way a person looks at someone they've been expecting.

She stops. It doesn't move. She takes a step. Nothing. Another. It sits there, forepaws together, ears upright, perfectly composed, and she is close enough now to see the frost on its fur and the stillness of its flanks. No breath. No twitch. The small, rapid heartbeat that should be visible in a hare's chest, the flutter that never stops, is not there.

She walks past it. She does not look back.

### The old woods
She reaches the old woods. The trees here are ancient, their branches interlocking overhead into a dark canopy. The air is thick with the scent of moss and decay, but also something sharp and mineral, the same smell Nika found under the cabin. Stone split open. The ground is frozen hard, but not with seasonal frost. This cold comes from underneath.

At one point she notices stone formations, half-buried in snow and moss. Not natural. Arranged, though not in any pattern she can read. Old. Older than the cabin. Older than the family. She crouches briefly. The engravings are almost gone, just the ghost of pattern under centuries of weathering. Something built by people who are gone, for reasons that went with them. Her grandmother mentioned stones once, she thinks. Or maybe not. The memory won't settle.

She stands and moves on. The wrongness in the air is thickening and she doesn't want to stay still.

### The Lyer encounter: too close
Elli turns to go back. The wrongness has accumulated past her threshold and every instinct says: leave, go south, get back to the cabin.

It is at this moment that the presence arrives.

Not all at once. The temperature drops. Not gradually but all at once, a wall of cold that hits her face. The silence becomes absolute. Not quiet. Absolute. The kind of silence that has mass.

Something is behind her. She knows this the way you know a hand is near your face in the dark. Not sight, not sound. Proximity. Presence.

She begins not to turn. Then does.

It is there. Close.

Not across the clearing or half-seen between trunks. Close enough that if she lifted a hand she could have touched something. She never later finds a description that holds. Only fragments: height, a leaning-forward patience, a suggestion of a face where her eyes cannot make a face settle. The smell of split stone and old smoke. Cold so deep it feels laid against the roots of her teeth.

What undoes her is not its shape but its attention. It is looking at her the way a person looks at someone they have been expecting.

The fear that hits her is not quite hers. It is too large, too sudden, flooding into her from somewhere outside. Not panic. Something older. The body's oldest instruction: run. Her heartbeat doubles. Her shoulders pull up. Every nerve in her is screaming south, south, go south.

She runs.

Not carefully. Not with any thought for the path or the ground or the branches. She runs with everything she has, crashing through the undergrowth, the cold behind her pressing close, the presence not chasing but simply _there_, intimate and enormous, like a wall of weather at her back.

She hits the tree full on. Shoulder and cheekbone and the flat of her forearm all at once, the impact so sudden and so total that her legs are gone before she knows she's falling. The ground meets her sideways. Pine needles against her face. A high, clean tone in her left ear that isn't a sound, just damage.

Everything stops.

She is on the ground. She knows this. She cannot feel the ground. She can see bark, very close, and a thin line of blood running into the frost, and beyond that, the blurred dark of the forest floor. Her breath won't come. Her chest is locked, the muscles around her ribs clenched tight and refusing, and for several seconds the only thing that exists is the effort to pull air into a body that has forgotten how.

Then the breath comes, shallow and wrong, and with it: pain. Her cheekbone. Her shoulder. A deep, sick ache in her ribs where she landed. Blood from her nose, warm against her upper lip, cooling fast.

She can't move. Not won't. Can't. Her arms are somewhere nearby but the connection between wanting to move and moving has been cut. She lies there and the cold presses in from all sides and the silence fills the space her thoughts should occupy.

The stillness changes.

Not a sound. Not movement. A thickening in the air beside her, as though something very large and very patient has settled close to the ground to look at what has fallen. The cold deepens. The silence tightens. She can feel attention on her the way skin feels the sun, a pressure with no visible source.

Something in her body, deeper than thought, deeper than the pain and the fog and the ringing in her ear, refuses. Not bravely. Not with any clarity or decision. The way a hand pulls back from a flame before the mind has even registered heat. Reflex. The animal at the bottom of her, the thing that lived before language, before fear had a name, before she was anyone at all, will not lie still while something leans over it.

She moves. One arm, then the other. The ground tilts. Her ribs scream. She gets a knee under her, then a foot, and she is standing, barely, swaying, blood on her chin, and she does not look at what is beside her. She does not look.

She ran. Bleeding, winded, half-blind. South. Always south. The trees blurred on either side and she didn't count them and she didn't mark the path and she didn't wonder why the forest felt like it was tilting around her. She ran because the terror was bigger than she was and south was the only direction she had.

The trees thinned. A clearing opened. She burst into it without slowing, without looking up.

She looked up.

And there it is, maybe fifty metres away.

The cabin.

She didn't stop to question it. She crossed the clearing at a stumble and threw herself at the door.

---

## Act III: The Wrong Cabin

### Discovery
The door swings open under her weight and she falls into warmth.

She's across the threshold before she's thought about it, the fear still driving her forward even as the cabin closes around her. The door swings shut behind her. She stands there, chest heaving, blood on her lip, hands braced on her knees.

The fire is burning. Low, steady, tended. The cabin is warm. The square table, the enamel sink, the small window. Every detail correct. The same scorch mark on the hearth stone. The same crack in the enamel sink.

There is a towel warming by the stove. A mug already on the table. The place is not merely familiar. It is prepared for her.

She doesn't register any wrongness yet. She registers: safe. Inside. Not out there.

### Nika
When Elli looks up, Nika is there.

She's sitting at the table, a mug of coffee in front of her, leafing through the old paperback from the shelf. She looks up and takes in Elli's state, the bloody nose, the torn jacket, the wild look, and is on her feet before she's finished looking.

"Christ. What happened to you?"

Elli doesn't answer immediately. She's breathing too hard. The warmth of the cabin is pressing in from all sides and some part of her wants to simply collapse into it and stop. But Nika is crossing to her, real and present, grip on her arm solid and too firm to be anything but actual.

"You called me," Nika says. "I drove up. Door was open. I've been here twenty minutes. Where have you been?" Her eyes move over the blood, the state of Elli's clothes. "What did you hit?"

"A tree."

"Running from what?"

Elli looks at her. There's the real question.

She got the message, then. Drove up from Korpikylä the way Nika does everything, without drama, without delay. Walked in through the door she's walked through a hundred times. Lit the stove. Made coffee. Sat down. The most normal thing in the world.

Elli lets herself be settled into a chair. Lets the coffee be pressed into her hands. It is made exactly how she takes it. The first mouthful nearly makes her cry, and not because of the coffee. Because this is how it used to be. Nika in the cabin, taking charge, knowing what Elli needs before Elli does. The old closeness, the one she walked away from and never replaced, is suddenly here in the room as though no time has passed at all. No distance. No years of thinning. Just Nika, solid and warm and slightly annoyed in the way that means she's frightened. Everything is fine. Everything is built to feel fine.

Almost.

### The first wrongness
Small things. Easy to explain away.

Looking out the window, Elli notices a pattern in the frost on the glass, branching, intricate, the way frost always patterns. Except it looks like wood grain. Like the interior of a split branch. The lines follow the same logic as growth rings, spreading from some unseen centre. She blinks and it's just frost.

Later: Nika's hand around the coffee mug. The knuckles look wrong for a moment, too prominent, too dark, the skin pulling oddly. Like roots under bark. Then Nika shifts her grip and it's just a hand.

Later still: Nika smiles at something Elli says, and for a beat the smile seems to arrive a fraction late, as if laid across the face after the fact.

Elli says nothing. Her head hit a tree. She's bleeding. The wrongness she saw in the forest is still close to the surface of everything, leaching colour into things that don't deserve it. She is not going to become someone who sees monsters in frost patterns.

She tucks it away. All of it.

### The wrong outside
It is Nika who suggests they look outside.

The clearing is wrong. The driveway is gone. Nika's car is gone. The familiar treeline, the pines she's known since childhood, is replaced by ancient, towering, interlocking trees that are too dark, too dense, too close. The ground is frozen black. The air is still with the kind of stillness that has weight. The sky above is white and featureless, as if painted on.

Nika steps out onto the threshold. She stops.

She doesn't speak for a long time. Elli watches her face change. Nika, who walked naked into snow without flinching, who gutted elk at sixteen, who slept alone in the woods. Nika's face goes white. Her hands grip the door frame.

"This isn't where I drove to," Nika says. Very quiet. Very flat.

"No."

"Where are we?"

"I don't know. I was in the old woods. I walked south. Or I thought I did. I found this."

Nika looks back into the cabin. The fire crackles. The warmth reaches for them.

"I don't know what this is," Nika says. "But I know we can't just stay in there."

It's the first time either of them has said _it._

---

## Act IV: The Unmasking

### Understanding, and the shape of the lie
They piece it together outside in the cold, away from the warmth that reaches for them. Nika tells Elli about _No Further_, the chairs, the ash, the fire that lit itself, the warmth that felt like an invitation. The moment she said no and felt the cold truth bleed through. She tells Elli that the word for it almost arrived in her kitchen afterwards, and that she stopped it from finishing. The naming is what this conversation is for. Where exactly the word comes from in the scene — Nika finally letting it through, Elli surfacing it from her grandmother, an old phrase neither of them knew they remembered — is a decision for the prose draft of The Cabin. The voicemail was the call. The naming is here.

The shape assembles between them, not a full picture, but the outline of one. The cabin as something inherited without explanation. The old woods as a place people stayed away from without knowing why. And the Lyer, which did not simply frighten Elli but met her close enough to make terror intimate and then turned her fear into movement.

"It wanted me running," Elli says. "Not just frightened. Running. South. To this."

Nika is quiet for a moment.

_[Note for prose: The reader who has read No Further will feel the wrongness here before Elli does. The real Nika said no to this place and left. She did not come back. This Nika is calm, steady, present. She has none of the damage she should have. She is too willing to be here.]_

### The second wrongness
They are moving through the wrong woods when it happens again.

This time Elli sees it clearly.

Nika is walking ahead of her, pushing through a low branch, and for just a moment, two seconds, maybe three, her hand where it grips the branch is not a hand. The fingers are too long. The joints bend the wrong way. The skin has the texture and colour of birch bark, pale and dry, and where her knuckles should be there are knots in the wood. Then the branch releases and she turns back and her hand is her hand.

"You alright?" Nika says.

"Yes," Elli says.

She is not alright. She is running the inventory now. Every small wrongness, every moment she tucked away. The frost on the glass. The knuckles around the mug. The delayed smile. The way Nika pushed them outside to look. The way she keeps moving them deeper, further north, with a certainty that feels like it comes from somewhere other than Nika.

She doesn't say any of this. She walks. She thinks.

### The third wrongness, and the knowing
The forest is empty. Completely empty. No tracks, no droppings, no movement at the edges. Not even the wrong stillness of the hare on the path. Just nothing. As though everything that lived here has gone, or been taken, or been made into something else.

And then Nika stops walking.

She is standing at the edge of a small clearing, looking at something Elli can't see from here. She is very still. Not Nika-still, not the stillness of someone who has paused to think. The stillness of something held in place.

Elli stops.

"Nika."

Nothing.

"Nika."

Nika turns. And the smile is right. The voice, when she speaks, is right. "Sorry. Thought I saw something."

But the turn was wrong. Not the motion of a person returning from thought. Something else. A correction. A system returning to its prior state.

Elli knows. She has known for a while. She just hadn't let herself finish the knowing.

The Lyer spent time with the real Nika during _No Further._ It learned her. The directness, the toughness, the way she goes still when she's frightened, the way she moves, the specific warmth of her grip. It built something from that. A very good something. But it built the wrong Nika. It built the close one, the childhood one, the one with no distance between them. The one who grabs Elli's arm without hesitating, who makes coffee exactly right, who is simply *there* the way she was when they were young. The real Nika would have come. But there would have been a pause in the doorway. A beat of awkwardness. Twenty years of silence in the air between them. This Nika had none of that. And Elli, bleeding and terrified and desperate for exactly the thing she'd spent years refusing to miss, walked right into it.

The real Nika is two hours south. The real Nika said no to this place and didn't come back.

This is not Nika.

---

## Act V: The Escape

_[Framework only. Ending still developing.]_

Elli now knows she is alone. Completely alone, in the wrong woods, with a thing that is wearing her friend's face. She doesn't know what it wants from her. She only knows the lie, and that is enough to stop cooperating with it.

The important structural shift is this: escape cannot simply be running south harder. Running is still movement inside the Lyer's arrangement. Direction is not agency here.

Her way out has to begin with recognition. She has to stop cooperating with the offered story, with the warmth, with the face wearing her friend. She may need to say it aloud. She may need to look directly at the thing and name what is absent rather than what is present.

For working purposes, the Lyer's behaviour follows a private logic even if the reader never receives it outright: it wants willing participation. It wants Elli to stay inside the lie long enough to be learned properly. The false cabin and the false Nika are not bait in the simple sense. They are an invitation to consent.

The escape is not a fight and not a triumph. It is Elli, alone, finding some thread of clarity in the cold specific knowledge of what she has to do. The Lyer pushes back with everything, the cold, the weight, the accumulated wrongness, the fear that isn't quite hers. The thing wearing Nika's face may drop its pretence entirely at some point, and what is underneath is a question the story doesn't need to fully answer.

She does not defeat the Lyer. She gets out. There is a difference.

The real cabin. The real driveway. Her car where she left it.

The Lyer is still in those woods. The forest is still moving south. She is the only one who knows, and the knowing is not a comfort.

---

## Coda

_[To be developed. Key principles below.]_

Elli is back. Alive. Alone in the real cabin.

She tries to call Nika. Whether she gets through is undecided, but the real Nika is her own story, and her fate and whereabouts belong as much to _No Further_ as to this one. What happened during her visit. Why she left the voicemail and then didn't come. What she knows that she hasn't said. These are left as open wounds rather than answered questions.

The scraping sound returns. The same sound from the opening, from her childhood, from the night her parents told her it was nothing. She understands it now, or understands it better than she did.

She sits at the table and listens to it until it stops.

It stops.

She waits.

---

_Note: Ending is deliberately unfinished, left to develop. Key principles: the Lyer is not defeated and nothing is resolved. Elli escapes but changes nothing. The fake-Nika deception is the central horror of the second half. Readers of No Further will recognise the wrongness before Elli does, making them helpless witnesses to her being deceived by something wearing a face they already know. The real Nika's fate is an open wound. The Lyer is still out there. The forest is still moving south._
