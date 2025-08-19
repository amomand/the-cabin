from typing import List, Optional
from game.item import Item


class Player:
    def __init__(self):
        self.running = True
        self.name = "Eli"
        self.health = 100
        self.fear = 0
        self.inventory: List[Item] = []
    
    def add_item(self, item: Item) -> None:
        """Add an item to the player's inventory."""
        self.inventory.append(item)
    
    def remove_item(self, item_name: str) -> Optional[Item]:
        """Remove an item from inventory by name. Returns the item if found."""
        clean_name = self._clean_item_name(item_name)
        for i, item in enumerate(self.inventory):
            if item.name.lower() == clean_name:
                return self.inventory.pop(i)
        return None
    
    def get_item(self, item_name: str) -> Optional[Item]:
        """Get an item from inventory by name without removing it."""
        clean_name = self._clean_item_name(item_name)
        for item in self.inventory:
            if item.name.lower() == clean_name:
                return item
        return None
    
    def has_item(self, item_name: str) -> bool:
        """Check if the player has an item with the given name."""
        clean_name = self._clean_item_name(item_name)
        return any(item.name.lower() == clean_name for item in self.inventory)
    
    def _clean_item_name(self, item_name: str) -> str:
        """Clean item name by removing articles and normalizing."""
        # Remove common articles
        articles = {"a", "an", "the"}
        words = item_name.lower().split()
        words = [word for word in words if word not in articles]
        return " ".join(words)
    
    def get_inventory_names(self) -> List[str]:
        """Get a list of item names in the inventory."""
        return [item.name for item in self.inventory]
