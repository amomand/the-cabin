from __future__ import annotations
from typing import Set, Optional, Dict, Any
from dataclasses import dataclass
import random


@dataclass
class Wildlife:
    """A wildlife entity that can appear in rooms."""
    
    name: str
    description: str
    traits: Set[str]  # docile, vicious, skittish, ambient, massive, elusive, etc.
    sound_description: str  # What it sounds like when heard
    visual_description: str  # What it looks like when seen
    has_attacked: bool = False  # Track if this animal has already attacked
    
    def __init__(
        self,
        name: str,
        description: str,
        traits: Set[str] = None,
        sound_description: Optional[str] = None,
        visual_description: Optional[str] = None
    ):
        self.name = name
        self.description = description
        self.traits = traits or set()
        self.sound_description = sound_description or f"You hear a {name} nearby."
        self.visual_description = visual_description or f"A {name} is visible in the area."
        self.has_attacked = False
    
    def has_trait(self, trait: str) -> bool:
        """Check if the wildlife has a specific trait."""
        return trait in self.traits
    
    def is_docile(self) -> bool:
        """Check if the wildlife is docile."""
        return "docile" in self.traits
    
    def is_vicious(self) -> bool:
        """Check if the wildlife is vicious."""
        return "vicious" in self.traits
    
    def is_skittish(self) -> bool:
        """Check if the wildlife is skittish."""
        return "skittish" in self.traits
    
    def is_ambient(self) -> bool:
        """Check if the wildlife is ambient."""
        return "ambient" in self.traits
    
    def is_elusive(self) -> bool:
        """Check if the wildlife is elusive (cannot be seen)."""
        return "elusive" in self.traits
    
    def is_massive(self) -> bool:
        """Check if the wildlife is massive."""
        return "massive" in self.traits
    
    def can_attack(self) -> bool:
        """Check if the wildlife can attack (vicious and hasn't attacked yet)."""
        return self.is_vicious() and not self.has_attacked
    
    def provoke(self) -> Dict[str, Any]:
        """Provoke the wildlife and return the result."""
        # Vicious animals attack when provoked, even if they're also skittish
        if self.can_attack():
            self.has_attacked = True
            return {
                "action": "attack",
                "message": f"The {self.name} snarls and lunges at you!",
                "health_damage": 15,
                "fear_increase": 10,
                "remove_from_room": False
            }
        elif self.is_skittish():
            return {
                "action": "flee",
                "message": f"The {self.name} startles and runs away into the darkness.",
                "remove_from_room": True
            }
        elif self.is_docile():
            return {
                "action": "wander",
                "message": f"The {self.name} looks at you curiously, then slowly wanders away.",
                "remove_from_room": True
            }
        else:
            return {
                "action": "ignore",
                "message": f"The {self.name} ignores your provocation.",
                "remove_from_room": False
            }
    
    def __str__(self) -> str:
        return self.name
    
    def __repr__(self) -> str:
        return f"Wildlife('{self.name}', traits={self.traits})"


# Predefined wildlife for the Finnish wilderness
def create_wildlife() -> Dict[str, Wildlife]:
    """Create a dictionary of predefined wildlife for The Cabin."""
    wildlife = {}
    
    # Docile animals
    wildlife["reindeer"] = Wildlife(
        name="reindeer",
        description="A large reindeer with impressive antlers, standing quietly in the snow.",
        traits={"docile", "massive"},
        sound_description="You hear the soft crunch of hooves on snow and a gentle snort.",
        visual_description="A reindeer stands motionless in the clearing, its breath visible in the cold air."
    )
    
    wildlife["fox"] = Wildlife(
        name="fox",
        description="A red fox with a bushy tail, watching you with intelligent eyes.",
        traits={"docile", "skittish", "curious"},
        sound_description="A soft rustling in the underbrush, followed by a quiet bark.",
        visual_description="A fox sits on a fallen log, its ears twitching as it watches you."
    )
    
    wildlife["mountain_hare"] = Wildlife(
        name="mountain hare",
        description="A white mountain hare, perfectly camouflaged against the snow.",
        traits={"docile", "fast", "skittish"},
        sound_description="A quick rustle of movement through the snow.",
        visual_description="A white hare sits motionless, its ears alert and twitching."
    )
    
    # Vicious animals
    wildlife["wolf"] = Wildlife(
        name="wolf",
        description="A gray wolf with yellow eyes, watching you with predatory intensity.",
        traits={"vicious", "skittish", "pack"},
        sound_description="A low, menacing growl echoes through the trees.",
        visual_description="A wolf stands in the shadows, its yellow eyes fixed on you."
    )
    
    wildlife["brown_bear"] = Wildlife(
        name="brown bear",
        description="A massive brown bear, its powerful frame dominating the clearing.",
        traits={"vicious", "massive", "solitary"},
        sound_description="A deep, rumbling growl that makes your bones vibrate.",
        visual_description="A brown bear stands on its hind legs, towering over you."
    )
    
    wildlife["wolverine"] = Wildlife(
        name="wolverine",
        description="A stocky wolverine with dark fur, its eyes gleaming with aggression.",
        traits={"vicious", "tough", "elusive"},
        sound_description="A harsh, guttural snarl from the underbrush.",
        visual_description="A wolverine emerges from the shadows, its teeth bared."
    )
    
    # Elusive animals
    wildlife["eurasian_lynx"] = Wildlife(
        name="eurasian lynx",
        description="A large lynx with tufted ears, moving silently through the trees.",
        traits={"elusive", "silent", "predatory"},
        sound_description="Complete silence, but you sense something watching.",
        visual_description="You catch only a glimpse of movement - something large and feline."
    )
    
    wildlife["pine_marten"] = Wildlife(
        name="pine marten",
        description="A small, agile pine marten darting through the branches above.",
        traits={"elusive", "arboreal", "thief"},
        sound_description="A soft rustling in the tree branches overhead.",
        visual_description="A flash of brown fur disappears into the canopy."
    )
    
    # Ambient animals
    wildlife["snowy_owl"] = Wildlife(
        name="snowy owl",
        description="A large snowy owl perched high in a tree, watching silently.",
        traits={"ambient", "watchful", "nocturnal"},
        sound_description="A soft hoot echoes through the night air.",
        visual_description="A snowy owl sits motionless in a tree, its yellow eyes fixed on you."
    )
    
    wildlife["eagle_owl"] = Wildlife(
        name="eagle owl",
        description="A massive eagle owl with dark plumage, its wingspan impressive.",
        traits={"ambient", "predatory", "massive", "nocturnal"},
        sound_description="A deep, resonant hoot that carries through the forest.",
        visual_description="An eagle owl spreads its massive wings, casting a shadow across the snow."
    )
    
    wildlife["raven"] = Wildlife(
        name="raven",
        description="A large raven with glossy black feathers, perched on a branch.",
        traits={"ambient", "watchful", "symbolic"},
        sound_description="A harsh caw echoes through the trees.",
        visual_description="A raven sits on a branch, its black eyes watching you intently."
    )
    
    wildlife["capercaillie"] = Wildlife(
        name="capercaillie",
        description="A large grouse-like bird with dark plumage, standing in the snow.",
        traits={"ambient", "startling", "vicious"},
        sound_description="A sudden burst of wingbeats and a startled call.",
        visual_description="A capercaillie stands motionless, its dark form blending with the shadows."
    )
    
    return wildlife


def get_random_wildlife(wildlife_pool: Dict[str, Wildlife], max_count: int = 2) -> list[Wildlife]:
    """Get a random selection of wildlife from the pool."""
    if not wildlife_pool:
        return []
    
    available = list(wildlife_pool.values())
    # Ensure we get at least 1 wildlife if max_count > 0, but respect max_count
    count = min(random.randint(1, max_count) if max_count > 0 else 0, len(available))
    
    if count == 0:
        return []
    
    return random.sample(available, count)
