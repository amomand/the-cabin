# Quest Mechanic

The Cabin now supports a **Quest Mechanic** to drive narrative progression and player goals.

## Overview

Quests are triggered at specific moments in the game—either by entering certain rooms or by performing specific actions. When triggered:

- The terminal clears and the quest is framed as a held thought, wrapped in the lines `*You take a breath and focus...*` and `*Hold the thought.*`
- There is no instruction addressed to the player. Any keypress lets the thought go (in non-interactive terminals the raw-key read falls back to `input()`, i.e. Enter), and the game resumes with either the current room description (if triggered by an action) or the room the player has entered (if triggered by movement).

## Trigger Types

- **Location-based**: Entering specific rooms can trigger quests.
- **Action-based**: Specific player actions or item uses can trigger quests.

## Quest Display

- The held-thought view replaces the normal output while it is up; on dismissal the room re-renders.
- If a quest triggers during a room transition, the quest is shown *before* the room description.
- The view shows the quest title, the quest's `quest_screen_text`, and any updates gathered so far under an `**Updates:**` heading (see `Quest.get_display_text()`). Nothing in it instructs the player: no key prompts, no progress checklists.

## Viewing Active Quests

- At any time, the player can type `q` or `quest`.
- If a quest is active, the held-thought view opens again, showing the quest's `quest_screen_text` and any updates so far. (The `objective` field is AI-interpreter context, not player-facing display.)
- If no quest is active, the view reads:  
  `"Nothing pulls at you just now. Only the cold, and the quiet, and the work your hands already know."`

## Quest Updates

- If the player performs an action or encounters something that relates to an ongoing quest, the system may display a quest update.
- Updates render **bare**, integrated with the normal game-feedback voice — no `Quest Update:` label, no system prefix. The text is the update.
- All updates are also appended to the quest screen. When the player types `q`, they will see all relevant updates in context.

The label-free rendering is deliberate: a system prefix on every quest update is a fourth-wall break that competes with the in-world voice. Write update text so it lands as observation or consequence, not announcement.

## Narrative Integration

Quests are designed to:
- Reinforce a sense of purpose.
- Add structure to the free-form exploration.
- Enhance atmosphere through focused objectives.
- Gate certain parts of the story or world behind key progress moments.

## Example

With the Warm Up quest active, typing `q` shows:

---

*You take a breath and focus...*

**Warm Up**  
The cold won't keep. Power first, then warmth.  
The breaker is in the konttori. There's wood down by the lakeside. The hearth is laid and waiting.

Your hands know the order of it.

*Hold the thought.*

---

Later, after the breaker is flipped:
> Power hums through the cabin. The lights should work now.

This update is shown immediately in the game feed — bare, no label — and appended to the quest view.

---

This mechanic adds narrative momentum while keeping players grounded in the eerie atmosphere of The Cabin.