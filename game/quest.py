from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from game.story.guidance import false_cabin_objective

if TYPE_CHECKING:
    from game.world_state import WorldState


class QuestStatus(Enum):
    """Status of a quest."""
    INACTIVE = "inactive"
    ACTIVE = "active"
    COMPLETED = "completed"


@dataclass
class QuestUpdate:
    """Represents an update to a quest."""
    event_name: str
    text: str
    timestamp: float


class Quest:
    """Represents a quest in the game."""
    
    def __init__(
        self,
        quest_id: str,
        title: str,
        opening_text: str,
        objective: str,
        trigger_conditions: List[Dict[str, Any]],
        update_events: Dict[str, Dict[str, Any]],
        completion_condition: Callable[[Any, WorldState], bool],
        completion_text: str,
        quest_screen_text: str,
        inactive_text: str = "Nothing calls to you yet."
    ):
        self.quest_id = quest_id
        self.title = title
        self.opening_text = opening_text
        self.objective = objective
        self.trigger_conditions = trigger_conditions
        self.update_events = update_events
        self.completion_condition = completion_condition
        self.completion_text = completion_text
        self.quest_screen_text = quest_screen_text
        self.inactive_text = inactive_text
        
        self.status = QuestStatus.INACTIVE
        self.updates: List[QuestUpdate] = []
        self.completed_at: Optional[float] = None
    
    def check_trigger(self, trigger_type: str, trigger_data: Dict[str, Any], player: Any, world_state: WorldState) -> bool:
        """Check if this quest should be triggered based on the given trigger."""
        # Don't trigger if quest is already active or completed
        if self.status != QuestStatus.INACTIVE:
            return False
            
        for condition in self.trigger_conditions:
            if condition.get("type") == trigger_type:
                # Check if the condition matches
                if trigger_type == "location":
                    if condition.get("room_id") == trigger_data.get("room_id"):
                        return True
                elif trigger_type == "action":
                    if condition.get("action") == trigger_data.get("action"):
                        return True
        return False
    
    def check_update(self, event_name: str, event_data: Dict[str, Any], player: Any, world_state: WorldState) -> Optional[str]:
        """Check if an event should trigger a quest update. Returns update text if applicable."""
        if self.status != QuestStatus.ACTIVE:
            return None
            
        if event_name in self.update_events:
            event_config = self.update_events[event_name]
            trigger_condition = event_config.get("trigger")
            
            # Check if the trigger condition is met
            if trigger_condition and trigger_condition(event_data, player, world_state):
                update_text = event_config.get("text", "")
                if update_text:
                    return update_text
        return None
    
    def check_completion(self, player: Any, world_state: WorldState) -> bool:
        """Check if the quest completion condition is met."""
        if self.status == QuestStatus.ACTIVE:
            return self.completion_condition(player, world_state)
        return False
    
    def add_update(self, event_name: str, text: str, timestamp: float) -> None:
        """Add an update to the quest."""
        update = QuestUpdate(event_name=event_name, text=text, timestamp=timestamp)
        self.updates.append(update)
    
    def get_display_text(self) -> str:
        """Get the text to display for this quest."""
        if self.status == QuestStatus.INACTIVE:
            return self.inactive_text
        
        if self.quest_id == "warm_up":
            return "\n\n".join([self.quest_screen_text, *(update.text for update in self.updates)])
        text = f"{self.title}\n{'-' * len(self.title)}\n{self.quest_screen_text}"
        
        if self.updates:
            text += "\n\nUpdates:"
            for update in self.updates:
                text += f"\n{update.text}"
        
        return text


class QuestManager:
    """Manages all quests in the game."""
    
    def __init__(self):
        self.quests: Dict[str, Quest] = {}
        self.active_quest: Optional[Quest] = None
        self.completed_quests: List[str] = []
    
    def register_quest(self, quest: Quest) -> None:
        """Register a quest with the manager."""
        self.quests[quest.quest_id] = quest
    
    def check_triggers(self, trigger_type: str, trigger_data: Dict[str, Any], player: Any, world_state: WorldState) -> Optional[Quest]:
        """Check if any quest should be triggered. Returns the triggered quest if any."""
        for quest in self.quests.values():
            if quest.status == QuestStatus.INACTIVE and quest.check_trigger(trigger_type, trigger_data, player, world_state):
                return quest
        return None
    
    def activate_quest(self, quest: Quest) -> None:
        """Activate a quest."""
        quest.status = QuestStatus.ACTIVE
        self.active_quest = quest
    
    def check_updates(self, event_name: str, event_data: Dict[str, Any], player: Any, world_state: WorldState) -> Optional[str]:
        """Check if any active quest should be updated. Returns update text if applicable."""
        if self.active_quest:
            update_text = self.active_quest.check_update(event_name, event_data, player, world_state)
            if update_text:
                import time
                self.active_quest.add_update(event_name, update_text, time.time())
                return update_text
        return None
    
    def check_completion(self, player: Any, world_state: WorldState) -> Optional[str]:
        """Check if the active quest is completed. Returns completion text if applicable."""
        if self.active_quest and self.active_quest.check_completion(player, world_state):
            import time
            self.active_quest.status = QuestStatus.COMPLETED
            self.active_quest.completed_at = time.time()
            self.completed_quests.append(self.active_quest.quest_id)
            completion_text = self.active_quest.completion_text
            self.active_quest = None
            return completion_text
        return None
    
    def get_active_quest_display(
        self,
        world_state: Optional[WorldState] = None,
        room_id: Optional[str] = None,
    ) -> str:
        """Get the display text for the quest overlay.

        The false-cabin beats are story state, not quests, but they are the
        live objective while they hold Elli in the room, so they take the
        overlay ahead of any registered quest. Callers that pass no world
        state get the quest-only view.
        """
        if world_state is not None:
            if world_state.ending == "escaped":
                from game.story.guidance import escape_objective
                return escape_objective(world_state)
            objective = false_cabin_objective(world_state, room_id)
            if objective:
                return objective
            if not world_state.is_wrong_layer() and world_state.ending == "none":
                from game.story.arrival import evening_thought
                return evening_thought(world_state, room_id)
        if self.active_quest:
            return self.active_quest.get_display_text()
        return "Nothing pulls at you just now. Only the cold, and the quiet, and the work your hands already know."
    
    def has_active_quest(self) -> bool:
        """Check if there's an active quest."""
        return self.active_quest is not None
