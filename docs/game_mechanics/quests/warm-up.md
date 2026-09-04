# Warm Up

Entering the cabin activates the practical power-and-fire quest after the entry
cutscene. Its event-driven progress still completes when both `has_power` and
`fire_lit` are true, in either order. The machinery records progress for saves;
neither completion nor an active quest is required to sleep.

The quest no longer carries the buckets, bedding or missing-mug revelation.
Those belong to `story/arrival.py:reopen_cabin`, invoked by authored actions
independently of power and heat. Non-empty authored action feedback survives
quest callbacks in `turn.take_turn`; bookkeeping cannot replace a discovery
with a short progress line.

The `q` view asks what currently occupies Elli: first the message at the window,
then the saved frames, then bed, and in the morning the camera and then the birch. It has no title,
rule or Updates heading and does not display an obsolete evening checklist.
The false-cabin and coda objectives still take precedence through story-stage guidance, including the southward walk, call, packing and
chair. An unfinished warming quest cannot reappear after refusal.

The stored completion text is a short practical acknowledgement. Stored updates
remain serialised for compatibility. The standalone Warm Up display omits its
headings, but runtime `q` uses the current story state rather than old updates.

Code: `quests.py`, `quest.py`, `events/listeners/quest_listener.py`, `turn.py`,
`story/arrival.py`. Tests retain both completion orders and save/load coverage.
