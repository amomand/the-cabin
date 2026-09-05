# The Playable Story

> Status: game-side bible for the #264 re-authoring, decided 2026-09-04.
>
> The story is the maintainer's plotline and prose in Obsidian
> (`Fiction Writing/The Cabin/The Cabin - Plotline.md`, `The Cabin.md`),
> snapshotted here as `plotline.md` and `stories/the-cabin.md`. This file
> adapts that story to play: it settles what the prose leaves loose (the site
> plan, the order things can happen in, what a room looks like at each hour)
> and it is the reference every room description, beat and gate is reviewed
> against. If it disagrees with the plotline, the plotline wins and this file
> needs a decision, not a patch.
>
> The direction note of 2026-08-27 (a second force, the wrong woods as
> geometry that stops adding up) is not canon yet and is not targeted here.
> The forest rooms are written so that progression can be added later as
> prose in the same rooms.

## 1. Decisions

1. The target is the current plotline and prose. Acts III to V keep their
   shape; the refusal is the escape.
2. The interior keeps its three rooms. The main room holds the narrow bed,
   the stove, the hook and the table; the false-cabin night happens there.
   The bedroom holds the heavy-covered bed Elli sleeps in on the first
   night. The konttori is a desk, the router and the monitor. The wood store
   stands at the top of the drive by the cabin's north-west corner, where
   the cars park, visible from the clearing and the grounds. The northern
   camera is on the north eave, aimed at the treeline. The forest is reached
   north from the camera; the lake path is the familiar diversion.
3. The five frames live on the phone and are rewatched at the window after
   the voicemail. The konttori has no camera beat. Its description states
   the monitor plainly: dark without power, three live feeds with it and the
   northern one black until repair; all four live after repair. Nothing fires there.
4. Act I gates. Power is optional and has consequences but no health cost.
   Sleeping without a fire costs 10 health once and changes the waking.
   The missing-mug discovery belongs to the shared reopening beat, independent
   of both chores. Fire-lighting, the first voicemail, using the real mug or
   eating can supply it once. The meal can happen at the table; sleep narrates
   it first if it has not happened. Without a fire she eats bread and butter.
   The sauna is optional. The voicemail and the frames are required before
   sleep and happen at the window in that order. The woods north of the
   camera do not open until the camera errand is done.
5. On the first evening the lake path and shoreline are open and ordinary.
   The treeline path and the old woods refuse until the errand.
6. The lake is ordinary at dusk and black ice on the second morning. It is
   not a logged tell.
7. The `q` overlay is a held thought in prose with no title, underline or
   updates heading. Each cutscene has its own dismissal line. The Health and
   Fear readout is the one documented mechanical exception to the
   no-fourth-wall rule.
8. After the walk out the cabin holds her. Leaving is refused in prose. The
   grounds and clearing carry their post-escape text on the arrival only.
   The woods, the sauna and the lake are not walkable again.

## 2. Day phases

Every description and default line branches on a phase derived from state,
not on a clock. `WorldState.story_phase()` returns the coarse phase (evening,
morning, wrong, coda, stayed) from the existing fields and is never stored.
Phase 2 carries `reopening_done`, `evening_meal`, `slept_cold` and
`morning_started`, set in the beats that narrate them. Leaving the bedroom
starts the grey morning; sleep itself ends at the black window at 08:10.
`fire_lit` records a real fire, even one lit after cold sleep. Phase 3 carries the camera errand as `camera_stage`: `untouched`, `tested`,
`powered`, then `compared`. The monitor reads repair from `powered` onwards;
both forest approaches require `compared`. The fox tell records only the tracks.

| Phase | Derived from | Light | The world |
| --- | --- | --- | --- |
| Evening | `first_morning` false | Dusk going to dark. November, forty minutes north of the last lit window. | Ordinary. The cabin is cold and dark until she makes it otherwise. The woods are quiet in the populated way. |
| Morning | `first_morning` true, errand not done | Black at ten past eight, then grey and directionless. | Complete silence on waking. Frost on every needle. The fox tracks are out there. |
| Woods | Errand done, `lyer_encountered` false | Grey day, half a day of it. In the old woods the light fails an hour early. | The forest empties by degrees north of the birch. |
| Wrong night | `world_layer` wrong, by `reunion_stage` | Firelight and the lamp. Outside, no stars and no cloud to blame. | The false cabin, exactly right. |
| Wrong dawn | `reunion_stage` dawn | The wrong grey, sourceless. | The mug held out. |
| Walk out | wrong layer, `ending` escaped | Dark of the morning under the head torch, then real light with a direction. | Nothing arranges itself. Nothing follows. |
| Coda | real layer, `ending` escaped, by `coda_stage` | First proper daylight. | The real cabin as she left it. |
| Stayed | `ending` stayed | The grey does not lift. | The run is over. |

Within the evening, the cabin also branches on `has_power` and `fire_lit`,
and the bed on whether the voicemail and frames have been heard and seen.
Breakfast uses the fire for the kettle; without one she eats bread and keeps
her hands in her sleeves. A later fire does not change `slept_cold`.

## 3. Site plan

The cabin sits at the end of a gravel drive off the lake road, forty
minutes north of Korpikylä, inside ten acres of quiet. The lake is below it
to the west, reached by the childhood path behind the cabin. The northern
treeline is young spruce, then birch, then pine growing older with depth.

```
                 old woods (the deer path that is not there)
                          |
                 dead pines, the hare
                          |
      lake            the treeline: the forked birch, 50 m in
    (inlet)               |          .
       |          open frost, the fox tracks stop here
    lakeside --- shoreline bend .. (the loop rejoins the treeline path)
       \                  |
   sauna \        [northern camera on the north eave]
          \   wood store   CABIN GROUNDS
           \  (cars park) +-----------+
            ------------- | konttori  | bedroom
                          | main room |
                          +---door----+
                          THE CLEARING (the drive arrives)
                                |
                          THE ROAD END (the rental)
```

Room ids stay as they are, because saves, the map and tests depend on them.
Display names, contents and exits change where the table says so. Phase 3 implements this layout in `game/map.py`: the direct northward forest
route, the optional shore loop, Dead Pines between the birch and Old Woods,
and the konttori's single main-room door. The lake is west of the grounds.

| Room id | Name | What it is | Exits |
| --- | --- | --- | --- |
| `wilderness_start` | The Road End | The rental at the end of the drive. | north to the clearing |
| `cabin_clearing` | The Clearing | Where the drive arrives at the cabin's south face: the door, the north log with the key, the wood store at the corner. | cabin, grounds, south to the road end |
| `cabin_main` | The Cabin | The one warm room: table, four chairs, sink with the crack, stove, the hook, the narrow bed with the blankets folded the way Nika stacks them, the shelf with the green book, the porch cupboard inside the outer door. | out to the clearing, grounds, konttori, bedroom |
| `konttori` | Konttori | A desk under the low ceiling, invoices and manuals, the router, the monitor. One door, to the main room. | the main room |
| `bedroom` | Bedroom | The heavy-covered bed, the chest with the spare mattress and bedding. | the main room |
| `cabin_grounds_main` | Cabin Grounds | The north side: the wood store, the split log by the wall, the northern camera on the eave, open frost to the treeline, the path down to the lake, the sauna among the trees. | cabin, clearing, sauna, down to the lake, north to the treeline |
| `sauna` | Sauna | Separate building down towards the lake. Wood-fired stove; the low electric lights follow cabin power. The lake is in the small window. | out to the grounds |
| `lakeside` | Lakeside | The childhood path reaches the water between scrub willow. | up to the grounds, north to the inlet, east along the shore |
| `frozen_inlet` | Frozen Inlet | Reeds close around the inlet. A dead end. | back to the lakeside |
| `shoreline_bend` | Shoreline Bend | The bank bends east and the loop climbs back to the treeline path. | west to the lakeside, up to the treeline |
| `wood_track` | The Treeline | The forked birch on unbroken ground, fifty metres past the camera. Looking back, the cabin is gone behind young spruce. | south to the grounds, east to the shoreline, north into the pines |
| `deer_path` | Dead Pines | The deterioration band: grey needles, trees dead with their bark on. The hare sits in the open track. | south to the treeline, north into the old woods |
| `old_woods` | Old Woods | Canopy knitted shut, cold rising through the boot soles, split stone and old smoke. The place where the deer path should be. | back the way she came |

Wrong-layer rooms: `cabin_main` is the false cabin, `cabin_clearing` is the
black clearing, `wood_track` is the indifferent woods on the walk out and is
named "The Woods" there, not "The Treeline". The walk out is south, three
moves, one way.

Closed routes and their refusals, in prose and in character (Elli answers
fear with tasks, and does not walk into trees without one):

- Evening: the treeline path and the shoreline's climb refuse. The light is
  going; the camera is a morning job.
- Morning before the errand: the treeline refuses. The camera first.
- Coda: the cabin's outer door refuses. The ribs, the call, the light.

## 4. Objects and their states

Objects in the story are not inventory. The phone, head torch, compass and
meter are in her pockets or pack from the road end; the key joins them at
the clearing. They are not movable inventory. The interpreter knows the phone
and its saved frames as carried equipment, separately from room objects. Inventory holds what the fiction
actually has her carry between rooms: firewood, and the matches if the
design keeps them as an object.

| Object | Evening | Morning and woods | False cabin | Coda |
| --- | --- | --- | --- | --- |
| Key | Under the north log in black plastic, found at the clearing on arrival; in her pocket after. The clearing never offers it again. | Pocket. | Pocket. | Lets herself in with it. |
| Phone | Pocket. One bar at the main-room window angled at the road, none anywhere else. Carries the voicemail and the five frames. | Pocket. The live feed uses a direct local connection to the battery camera, independent of the mains-powered router and cellular reception. | In her jacket on the peg. Will not wake: dark all through. | The call at the window, four rings. |
| Breaker | Tripped, OFF, in the porch cupboard behind the snow shovel. Reset or not. | As left. | Not mentioned. The false cabin is lit by the fire and the lamp whatever she did. | As left. |
| Ceiling bulb, fridge | Dark and silent without power; weak yellow and a shudder in the wall with it. | As left. | Not mentioned. | As left. |
| Fire | Cold hearth. Lit from the wood store's split pine, or not. | Banked overnight if lit; a log shifts and puts sound back in the room. If never lit, the silence holds until she moves. | Hours old, tended, collapsed inward. Burns down as belief withdraws. Grey after the refusal. | Yesterday's fire, or the hearth she never lit. |
| Wood store, split log | Split pine seasoned under the roof. The log beside the wall. | The step up to the camera. Fifty metres from where the tracks stop. | Absent. | Where she comes out of the trees. |
| Water, bedding | Two buckets from the pump; bedding from the chest hung near the hearth if lit, otherwise spread cold over the bed. Part of the reopening beat. | | | |
| The hook and the blue mug | The hook by the stove is empty. Discovered once, at the reopening beat, not stated before it. The cupboard above the sink: plates, old glasses, the coffee tin, no mug. She takes a white one from the cupboard. | Hook empty. | The blue mug whole, chip at the two o'clock of the handle, on the table waiting, rinsed by the sink later, held out at dawn. Never explained. | Hook empty. She stands in front of it. |
| Monitor (konttori) | Dark without power. With it, three feeds holding frost and stillness, the northern one black. No beat. | Dark without power; with power, all four feeds live after repair. | Absent. | Power and repair state preserved. |
| Northern camera | On the north eave, dead a third time seven days ago. | Battery reads full and is dead; casing colder than the air; new battery, green light at once. Live feed against frame one: the birch left of centre and nearer. | Absent. | Not mentioned. |
| The five frames | On the phone, known by heart. Rewatched at the window after the voicemail: frame four, the birch moved; frame five black. | | | |
| The voicemail | On the phone, eleven days old, eleven listens. Played at the window: "it's lying out there". Nika does not pause. | | | Completed aloud at the refusal. |
| Sauna stove | Cold. Fed for half an hour if she goes; stones give back heat that evening only. | Cold again. | The proposal of a sauna tonight need not depend on yesterday's visit. The tended fire and lamp are present whatever she did. Skipping the sauna does not imply she skipped the cabin fire. | Not walkable. |
| Wine | Airport bottle in her pack. One glass with dinner; bottle corked on the counter, the empty glass beside it. | Corked bottle and glass on the counter in every cabin description from the morning on. | Absent. A cupboard that holds no wine is a night seam. | Corked bottle and glass, unmoved. |
| Tins, bread, soup | Bought on the road so there would be no reason to stop in the village. Not from Rovaniemi or anywhere named. | | Tins she never bought, a dinner better than she would have made. A night seam. | |
| Towel | Carried down only if she visits the sauna. | | Warming on the rail by the stove. | |
| Green book | On the shelf, title gone pale. | | Open under the copy's hand at arrival. Never commented on. | On the shelf. |
| Spare mattress | In the chest in the bedroom. | | Laid by the narrow bed. "Like when we were kids." | |
| Jacket, compass, head torch | Worn or pocketed. The compass is clipped to the jacket from the errand on. | Named at the errand's close. | Jacket on the peg. The copy names the compass. | Worn out of the false cabin; the torch on for the walk. |
| The car | At the road end, ticking as it cools, on arrival only. | At the road end. | No drive, no car, hers or Nika's. | Mentioned only in the call: drive slow past the lake. |
| Injuries | None. | Cracked or bruised ribs, a concussion, a nosebleed, from the tree. | Face cleaned, pupils checked, ribs pressed. | One cheekbone swollen, one eye going black. |

## 5. What Elli knows, and when the player is told

Elli arrives knowing almost everything the first act reveals. The player
does not. Each fact has one authored discovery and must not be referred to before it.
A shared guarded beat can be reached through several sensible actions.

| Fact | Elli knows since | The player is told | Not before |
| --- | --- | --- | --- |
| The northern camera died a third time seven days ago; the others show frost and stillness. | Before the flight. | The road end. | |
| The scraping at nine; "before the forest moved". | Childhood. | The entry cutscene. | |
| The hook is empty; the blue mug is gone. | The reopening ritual. | The reopening beat. | The cabin description before that beat. |
| Nika's voicemail, word for word, and the pause. | Eleven days. | At the window, before the frames; heat is optional. | Any earlier line may say a message waits; none may quote it. |
| The five frames; the birch moved between frames one and four. | Five weeks. | At the window, after the voicemail. | The birch is not named in any room before this. |
| "Could be a deer." "Not a deer." Nika drove up. | Five weeks. | The frames beat. | |
| The dinner, the wine, the plan for the morning. | | Dinner at the table or before bed; the morning plan at bed. | |
| The fox photo, "Your fox learnt to fly", the email she answered instead. | Six weeks. | The tracks, on the second morning. | |
| The birch stands on unbroken ground and nearer than the camera says. | The errand. | The errand's live feed, then the treeline. | The treeline prose assumes the errand; the gate guarantees it. |
| The forest is empty; the hare does not breathe; the deer path is gone. | The woods. | The attention beats, each once, with callbacks. | |
| What it looks like. | Never, in fragments only. | The encounter cutscene, and three refused looks. | Never described further. |
| "You called me." | Arrival at the false cabin. | The tended beat. | Resolved as a lie only in the knowing. |
| The estrangement in detail: four years, the funeral, flowers from an app, the photograph by the till, fourteen years since she slept a night here. | Always. | The refusal, and the copy's answer. | Earlier prose may say twenty years and message by unsent message; nothing more specific. |
| The scraping is not something trying to get in. | The coda. | The scraping beat. | |

## 6. Room by room

First visit and revisit differ wherever a first-visit description narrates
an act. The clearing finds the key once. The road end hears the car cool
once. After that the rooms describe what is there.

| Room | Evening | Morning and woods | Wrong layer | Coda |
| --- | --- | --- | --- | --- |
| The Road End | The rental ticking (first visit). Dusk. The drive narrowing between pine and birch. | The rental under frost, unvisited since. Grey daylight. | Not present. | Not walkable. |
| The Clearing | The cabin given up late; one window holding what is left of the light; the key found (first visit) and the door. The wood store at the corner. | The same ground in daylight; the door she left. | The black clearing: no drive, no car, the wrong treeline, the flat black ceiling. "Nothing out here is looking at you." | Her tracks and the fox's under first daylight, on the arrival only. |
| The Cabin | Cold and dark on entry (cutscene). Then by state: hearth cold or lit, bulb dark or weak yellow, bedding warmed by a lit hearth or spread cold on the bed once the ritual is done, the white mug on the table after it, the corked bottle after dinner. Item lines follow: the hearth is bare or burning, the matches are on the shelf or in her hand. | Morning light in the window, the overnight fire banked, a new fire burning low, or the hearth dead, the bottle on the counter. Coffee if a fire exists; otherwise bread with the kettle cold. The morning beat looks north from the outer door. | The false cabin, by stage, as implemented. The lamp, not the bulb. The stopped room after the refusal. | Cold; bulb as left, ash of any real fire or the untouched hearth; the bed open through the bedroom door; the bottle and glass; the hook. Then the scraping, then the chair. Leaving refused. |
| Konttori | Desk, manuals, router. Monitor dark, or three grey feeds with the northern one black. No beat. | Dark without power; all four feeds live after repair if powered. | Absent. | As left; not worth a visit and not refused. |
| Bedroom | The bed made up under heavy covers, the chest. Refuses nothing: sleeping cold is allowed and costs her. | The bed open where she left it. | Absent. | The bed open, seen through the door. |
| Cabin Grounds | Thin snow, the wood store, the camera on the eave, the sauna among the trees, the path down to the lake. Ordinary. The treeline refuses (the light). | The tracks across the open frost (morning). The errand as its own beat, in stages, at the camera. After it, the treeline is open. | Not present as itself; the walk out lands here. | The arrival home, once. |
| Sauna | Low electric lights if powered; otherwise dark. The lake a dark plate in the window at dusk. Stones cold, then giving back heat. | Cold again, daylight in the window. | Absent. | Not walkable. |
| Lakeside | The childhood path; pewter water under a white sky, ice at the edges, a bird somewhere. Populated quiet. | Black ice, smooth, no snow, no crack, no pressure line. Nothing moving on it. Unlogged. | Absent. | Not walkable. |
| Frozen Inlet | Reeds and the end of the bank. | Every stem frozen at the same angle. | Absent. | Not walkable. |
| Shoreline Bend | The bank bending east; the climb back to the treeline refuses (the light). | Frost holding each needle exact; the climb open after the errand. | Absent. | Not walkable. |
| The Treeline | Refuses from the grounds. | The forked birch on unbroken ground, moss at the root flare; looking back, the cabin gone. Still. One attention beat, with a callback. | On the walk out, "The Woods": one trunk and the next, black ground, the compass holding south. | Not walkable. |
| Dead Pines | Refuses. | Grey needles, dead branches without spring, the hare composed in the open track, not breathing. Arrival beat with an attention fallback for loaded positions. Revisits recall passing it without another sighting. | Absent. | Not walkable. |
| Old Woods | Refuses. | The canopy shut, cold from below, split stone and old smoke, the deer path not there. Any valid move out after the comparison and the three specific forest tells is the encounter. | Absent. | Not walkable. |

## 7. Authoring rules against this document

- Descriptions branch on phase and on first visit versus revisit. A
  description never narrates an act on a revisit that it narrated on the
  first.
- A description never fires a beat. Beats are actions, they change state in
  the same result that narrates them, and each has one home.
- Every attention beat has a callback. Looking twice never replays the
  discovery.
- Nothing is on a table or a desk that the fiction has in her pocket.
- Default lines (`listen`, `throw`, `wait`, `help`, generic `use`) branch on
  phase. On a still morning there is no wind high in the trees.
- The Lyer is implied, never named, never described past fragments. The
  copy is Nika until the knowing finishes and "the thing that is not Nika"
  after; never anything more specific.
- Verify alleged inventions against the source. Rovaniemi and the generic
  "Home" reply are cut. Nika's Toyota and the sauna's electric lights are in
  the source and are retained; a deliberate adaptation must say what changes.
