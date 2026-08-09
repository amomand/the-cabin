"""Player-facing quest text stays plain on both render surfaces."""

from game.quest import QuestStatus
from game.quests import create_warm_up_quest


def test_active_quest_display_contains_no_markdown_markers() -> None:
    quest = create_warm_up_quest()
    quest.status = QuestStatus.ACTIVE
    quest.add_update("power_restored", "The bulb gives a weak tremor.", 0.0)

    text = quest.get_display_text()

    assert text.startswith("Warm Up\n-------\n")
    assert "\n\nUpdates:\n" in text
    assert "**" not in text
