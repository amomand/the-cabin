# Recognition, refusal and return

After [the reunion](reunion-mechanic.md), attention earns the knowing and the
knowing makes the dawn choice possible. This page owns the night and ending
gates, including the playable return. The [plotline](../lore/plotline.md) owns
why the estranged register spoils the lie; the [bible](../lore/playable-story.md)
owns physical truth and disclosure order.

## Night and dawn

At `bedded`/`night`, the six night seams are the spoken memory, unvarying
breathing, dark phone, wrong tins/missing wine, black boards and impossible mug.
The bed supplies `MEMORY_ALOUD`. Deliberate `listen`, `look`, phone, tins and mug
attention supply the others through their authored handlers. Each logs once;
repeats use callbacks rather than replaying the discovery.

[game/story/night.py](../../game/story/night.py) defines the set and threshold:
four seams including `BREATHING_TIDE` are required before recognition. When an
observation crosses that gate, `maybe_finish_the_knowing()` narrates and logs
any unseen canonical seams in story order, then `NO_CALL` and the knowing. It
sets `recognition` and advances to `night` in the same scene. Attention must earn
it, but an exhaustive hidden checklist must not be required. Already-recognised
older saves retain the count-only gate rather than losing their earned dawn.

The phone is retrieved from the jacket on the peg, tried, returned to that
pocket and left there when Elli goes back to bed. Requests for saved frames use
the same stage-aware phone response. After refusal it travels in the worn
jacket. The false lamp/fire remain independent of real power and heating.

`wait` after recognition carries Elli's accounting and brings the dawn coffee
offer, advancing to `dawn`. [game/story/dawn.py](../../game/story/dawn.py) owns
two predicates: `can_advance_to_dawn()` for the completed night and
`is_dawn_offer_active()` for the offered mug. Both require the wrong layer,
`cabin_main`, no ending, recognition and the night threshold; their stages
are `night` and `dawn` respectively. Actions and interpreter context consume
these predicates rather than reconstructing them.

Both recognition and gathered seams are required so a malformed save or seed
cannot grant an unearned choice. The offer is located in this room at this
stage. Unavailable actions return authored responses about the current moment.

## The endings

Refusal is the canonical escape: the register change, estrangement spoken,
Nika's grief answered back, voicemail completed and attention withdrawn.
`RefuseAction` sets `ending = escaped`; the player then leaves on foot.
Declining the offered mug in words routes through the same action.

Accepting the coffee is the game's deliberately off-canon stayed ending.
`use mug` at dawn routes through `AcceptAction`, which sets `ending = stayed`
and closes the run. The room remains warm; the ending is consent, not punishment.
Neither ending names or explains the Lyer. [game/ending.py](../../game/ending.py)
owns the closing lines shared by the surfaces.

## Walk out and coda

The escape is `out`, `south`, `south`: threshold, indifferent woods, arrival at
the real grounds. The route is one-way so neither its fear steps nor its scenes
can replay. Help names only forward destinations. The head torch is on for the
walk and turned off at real daylight. [World layers](world-layers-mechanic.md)
owns the final transition and reset semantics; recognition and the ending persist.

Coda stages advance through `transition_coda_to()`:

| Stage reached | Trigger and consequence |
| --- | --- |
| `home` | Final southward step. Grounds and clearing lead home without restarting tracks or camera discoveries. Cabin entry pockets the key and holds Elli at the empty hook. |
| `called` | Phone/window in the real main room makes the call. This cannot replay the voicemail or frames. |
| `scraping` | `wait` or `pack` continues packing and starts the scraping. |
| `end` | Next `wait` seats Elli in the chair and closes the run. |

`Map.story_route_denial()` holds every outdoor coda route except the way home,
including the first grounds/clearing arrival. Old disk saves on an outdoor
detour may retreat, but cannot go farther into the forest or restart an outing.
Inside, the outer door refuses according to the call/packing/scraping stage;
ordinary play cannot return to replay homecoming. Bedroom and konttori remain
accessible. Listening there during the scraping retains its sound through the
doorway. Their fixtures do not reopen morning work.

The real cabin preserves power and fire history, including a fire lit after
cold sleep. The unpowered breaker is left alone, and the hearth cannot restart
evening chores. Outdoor fire attempts cannot describe an indoor hearth. The
bible's open bed, corked bottle, empty glass and empty hook remain present;
[perception](perception-and-room-description.md) decides what each observation
mentions. Return guidance takes priority over any unfinished warming quest.

State changes and their feedback stay together. Production calls to the knowing
and tell helpers pass `player` so the [authored fear step](fear-curve.md) lands;
the optional argument exists for state-building tools, not a cost-free runtime route.
The [save/load reference](save-load-mechanic.md) owns migration, while
[return tests](../../tests/test_return_story.py) and both-ending
[playtest routes](../architecture/playtesting.md) exercise the reachable boundaries.
