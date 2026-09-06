# Quests and held thoughts

`q` or `quest` opens a held thought about what currently occupies Elli. It has
no quest title, underline, Updates heading or stage counter. Dismissing it
returns to the room; an automatically opened quest follows any cutscene and
precedes the destination description. [AGENTS.md](../../AGENTS.md) and the
[bible](../lore/playable-story.md) own the diegetic and presentation rules.

## Runtime priority

[QuestManager.get_active_quest_display()](../../game/quest.py) chooses escape
and coda guidance first, then the live false-cabin invitation, then the real
evening/morning thought. Those state-derived objectives take priority over a
registered quest. They restate what the story has shown, not hidden requirements.

Callers without a story objective can receive an active quest's display text
and recorded updates, or the authored no-objective response. `Quest.objective`
is interpreter context, not the player-facing display. The generic quest class
retains a titled display for other callers; the current game uses its held-thought
path. Do not copy that generic format into runtime guidance.

The [Warm Up quest](quests/warm-up.md) records practical progress for saves but
cannot reinstate an obsolete chore checklist after refusal or block sleep.
[Reopening and morning](first_morning_miniquest.md) owns its separate discoveries.

## Events and authoring

Quest triggers, updates and completion respond to registered location/action
events. Updates are bare prose without a system prefix. Stored updates remain
serialised; they are not the live objective when story guidance takes priority.
Non-empty authored action feedback survives quest callbacks under the
[effects ordering contract](../architecture/effects.md#turn-order), so bookkeeping
cannot erase a narrated discovery.

Use [the quest template](quests/template-quest.md) when a new quest is actually
needed. Define trigger, completion and in-world text together; do not add a
second state machine for a story stage already owned by a handler. Existing
implementation is in [quests.py](../../game/quests.py) and the
[quest listener](../../game/events/listeners/quest_listener.py); save restoration
is covered by [save/load](save-load-mechanic.md).
