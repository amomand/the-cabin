# Quest Template

## Title
<Insert quest title here>

## Trigger Conditions
<Describe what action(s) or location(s) trigger this quest.>

## Opening Text
<What the player sees when the quest first begins. Presented as a held thought, not a menu: no labels, no prompts, no checklists.>

## Objective
<Clear summary of what the player must achieve. This maps to `Quest.objective`, which is AI-interpreter context only — it is *not* shown in the `q`/`quest` view. Player-facing text belongs in the held-thought text below.>

## Held-Thought Text (`quest_screen_text`)
<In-world goal text, with any relevant updates as bare prose. No title,
underline, Updates heading or checklist. Runtime story guidance takes priority
under [the quest contract](../quest-mechanic.md); this stored text is not a second
source of the current story objective.>

## Update Events
- **Event Name**: <e.g. Found Firewood>
  - **Trigger**: <What causes this update?>
  - **Text**: <Displayed when this update happens.>

(Repeat above block for each update)

## Completion Condition
<Describe what conditions must be met for the quest to complete.>

## Completion Text
<Displayed when the quest is finished.>

## Notes
<Optional extra context or notes for implementation.>
