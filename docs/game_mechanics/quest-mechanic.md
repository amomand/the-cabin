# Quest Mechanic

The Cabin now supports a **Quest Mechanic** to drive narrative progression and player goals.

## Overview

Quests are triggered at specific moments in the game—either by entering certain rooms or by performing specific actions. When triggered:

- The screen is cleared.
- A quest screen appears, displaying the name of the quest, the objective, and any relevant narrative context.
- The player must press any key to continue.
- Once dismissed, the normal game resumes with either the current room description (if triggered by an action) or the room the player has entered (if triggered by movement).

## Trigger Types

- **Location-based**: Entering specific rooms can trigger quests.
- **Action-based**: Specific player actions or item uses can trigger quests.

## Quest Display

- A quest screen replaces the normal view when triggered.
- The player presses any key to dismiss it and return to the game.
- If a quest triggers during a room transition, the quest is shown *before* the room description.

## Viewing Active Quests

- At any time, the player can type `q` or `quest` as a command.
- If a quest is active, the quest screen appears again, summarising the current objective and context.
- If no quest is active, the game will display a placeholder like:  
  `"You have no active quest. When a quest appears, it'll be shown here."`

## Quest Updates

- If the player performs an action or encounters something that relates to an ongoing quest, the system may display a **Quest Update**.
- This is shown in-line with normal game responses as:  
  `Quest Update: (summary of what changed)`
- All updates should also be appended to the quest screen. When the player types `q`, they will see all relevant updates in context.

## Narrative Integration

Quests are designed to:
- Reinforce a sense of purpose.
- Add structure to the free-form exploration.
- Enhance atmosphere through focused objectives.
- Gate certain parts of the story or world behind key progress moments.

## Example

A quest might appear as:

---

**Quest: Restore Power**  
The lights are out. The cabin is freezing. You need to get the generator running again.  
Check the shed, the cellar, or maybe the back of the cabin.  
Something is out there.

---

Later, after examining the shed:
> Quest Update: You found the fuel canister, but it's empty.

This update would be shown immediately in the game feed and also added to the quest summary.

---

This mechanic adds narrative momentum while keeping players grounded in the eerie atmosphere of The Cabin.