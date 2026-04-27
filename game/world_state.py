"""
Typed world state for The Cabin.

This replaces the untyped Dict[str, object] with a proper dataclass
that provides type safety, validation, and IDE autocomplete.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Literal, Optional


WorldLayer = Literal["real", "wrong"]

# Stages of the Act III reunion with the false Nika, in the Wrong Cabin.
# "none"     - not in the wrong cabin yet, or already refused out of it.
# "arrival"  - just fallen through the door, Nika is on her feet, assessing.
# "seated"   - settled into a chair, coffee in front of her, not yet tasted.
# "complete" - first mouthful has landed. The reunion lie is inside her now,
#              and the sensory tells (frost, knuckles, smile) become noticeable.
ReunionStage = Literal["none", "arrival", "seated", "complete"]
EndingState = Literal["none", "accepted", "refused"]


@dataclass
class WrongnessEntry:
    """A single observed anomaly in the world.

    - `anomaly_id` is stable and unique per anomaly kind so the same wrongness
      is not double-counted if the player re-observes it.
    - `description` is a short in-world label ("fox tracks end mid-stride").
    - `acknowledged` is True if the player commented on it or acted on it,
      False if Elli tucked it away.
    - `seen_at` is the insertion index (0-based) for stable ordering.
    """

    anomaly_id: str
    description: str = ""
    acknowledged: bool = False
    seen_at: int = 0


@dataclass
class WrongnessLog:
    """Ordered log of anomalies observed in the world.

    Supports threshold checks used by the Unmasking recognition gate.
    """

    entries: List[WrongnessEntry] = field(default_factory=list)

    def add(self, anomaly_id: str, description: str = "") -> bool:
        """Record a new anomaly. Returns True if newly added, False if already present."""
        if self.has(anomaly_id):
            return False
        self.entries.append(
            WrongnessEntry(
                anomaly_id=anomaly_id,
                description=description,
                acknowledged=False,
                seen_at=len(self.entries),
            )
        )
        return True

    def has(self, anomaly_id: str) -> bool:
        return any(e.anomaly_id == anomaly_id for e in self.entries)

    def acknowledge(self, anomaly_id: str) -> bool:
        """Mark an anomaly as acknowledged. Returns True if found and updated."""
        for entry in self.entries:
            if entry.anomaly_id == anomaly_id:
                entry.acknowledged = True
                return True
        return False

    def count(self) -> int:
        return len(self.entries)

    def acknowledged_count(self) -> int:
        return sum(1 for e in self.entries if e.acknowledged)

    def threshold_met(self, n: int = 3) -> bool:
        """True once at least `n` anomalies have been logged."""
        return self.count() >= n

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entries": [
                {
                    "anomaly_id": e.anomaly_id,
                    "description": e.description,
                    "acknowledged": e.acknowledged,
                    "seen_at": e.seen_at,
                }
                for e in self.entries
            ],
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "WrongnessLog":
        if not data:
            return cls()
        entries = [
            WrongnessEntry(
                anomaly_id=e.get("anomaly_id", ""),
                description=e.get("description", ""),
                acknowledged=bool(e.get("acknowledged", False)),
                seen_at=int(e.get("seen_at", 0)),
            )
            for e in data.get("entries", [])
            if e.get("anomaly_id")
        ]
        return cls(entries=entries)


@dataclass
class WorldState:
    """
    Centralized game world state with type safety and validation.
    
    All boolean flags that affect game logic should be defined here
    as explicit fields rather than arbitrary dict keys.
    """
    
    # Environment state
    has_power: bool = False
    fire_lit: bool = False

    # Act I beats
    voicemail_heard: bool = False
    footage_reviewed: bool = False
    sauna_used: bool = False
    first_morning: bool = False

    # Act II climax
    lyer_encountered: bool = False

    # Act IV: Recognition unlocks the refusal. Set when the correction-turn fires.
    recognition: bool = False

    # Which layer of reality the player is currently in.
    # "real" is the ordinary cabin. "wrong" is the Lyer's arrangement,
    # entered after the forced southbound flight in Act II.
    world_layer: WorldLayer = "real"

    # Act III reunion progression. See ReunionStage above. The sensory tells
    # in the wrong cabin only fire once reunion_stage == "complete".
    reunion_stage: ReunionStage = "none"

    # Act III pivot: the first time Elli and Nika step onto the threshold
    # and see the driveway gone. The beat fires once; subsequent transitions
    # back into the wrong clearing show the post-pivot description.
    wrong_outside_seen: bool = False

    # Act V: the final choice once the Lyer's offer is understood.
    ending: EndingState = "none"

    # Accumulating observed anomalies. Drives Act IV recognition.
    wrongness: WrongnessLog = field(default_factory=WrongnessLog)

    # Custom flags for dynamic/quest-specific state
    # Use sparingly - prefer adding explicit fields for common flags
    _custom_flags: Dict[str, Any] = field(default_factory=dict)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Dict-style access for backward compatibility.
        
        Checks explicit fields first, then custom flags.
        """
        # Check if it's a known field
        if hasattr(self, key) and not key.startswith('_'):
            return getattr(self, key)
        # Fall back to custom flags
        return self._custom_flags.get(key, default)
    
    def __getitem__(self, key: str) -> Any:
        """Dict-style bracket access for backward compatibility."""
        if hasattr(self, key) and not key.startswith('_'):
            return getattr(self, key)
        if key in self._custom_flags:
            return self._custom_flags[key]
        raise KeyError(key)
    
    def __setitem__(self, key: str, value: Any) -> None:
        """Dict-style bracket assignment for backward compatibility."""
        if hasattr(self, key) and not key.startswith('_'):
            setattr(self, key, value)
        else:
            self._custom_flags[key] = value
    
    def __contains__(self, key: str) -> bool:
        """Support 'in' operator for backward compatibility."""
        if hasattr(self, key) and not key.startswith('_'):
            return True
        return key in self._custom_flags
    
    def set_flag(self, key: str, value: Any) -> None:
        """Set a custom flag for dynamic/quest content."""
        self._custom_flags[key] = value
    
    def get_flag(self, key: str, default: Any = None) -> Any:
        """Get a custom flag."""
        return self._custom_flags.get(key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.
        
        Merges explicit fields with custom flags.
        """
        result: Dict[str, Any] = {}
        # Add explicit fields (excluding private ones)
        for key, value in asdict(self).items():
            if key == '_custom_flags':
                continue
            if key == 'wrongness':
                # asdict has already flattened to a plain dict; keep it.
                result[key] = value
                continue
            result[key] = value
        # Add custom flags
        result.update(self._custom_flags)
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WorldState:
        """
        Create from dictionary for deserialization.
        
        Known fields are set directly, unknown keys go to custom_flags.
        """
        known_fields = {
            'has_power',
            'fire_lit',
            'voicemail_heard',
            'footage_reviewed',
            'sauna_used',
            'first_morning',
            'lyer_encountered',
            'recognition',
            'world_layer',
            'reunion_stage',
            'wrong_outside_seen',
            'ending',
            'wrongness',
        }

        explicit: Dict[str, Any] = {}
        custom: Dict[str, Any] = {}

        for key, value in data.items():
            if key == 'wrongness':
                explicit['wrongness'] = WrongnessLog.from_dict(value)
            elif key == 'world_layer':
                # Coerce legacy values; default to "real" on anything odd.
                explicit['world_layer'] = value if value in ("real", "wrong") else "real"
            elif key == 'reunion_stage':
                explicit['reunion_stage'] = (
                    value if value in ("none", "arrival", "seated", "complete") else "none"
                )
            elif key == 'ending':
                explicit['ending'] = value if value in ("none", "accepted", "refused") else "none"
            elif key in known_fields:
                explicit[key] = value
            elif not key.startswith('_'):
                custom[key] = value

        state = cls(**explicit)
        state._custom_flags = custom
        return state
    
    def validate(self) -> None:
        """
        Validate state consistency.
        
        Raises ValueError if state is invalid.
        """
        # Add validation rules as needed
        if not isinstance(self.has_power, bool):
            raise ValueError(f"has_power must be bool, got {type(self.has_power)}")
        if not isinstance(self.fire_lit, bool):
            raise ValueError(f"fire_lit must be bool, got {type(self.fire_lit)}")
        if self.world_layer not in ("real", "wrong"):
            raise ValueError(f"world_layer must be 'real' or 'wrong', got {self.world_layer!r}")
        if not isinstance(self.wrongness, WrongnessLog):
            raise ValueError(f"wrongness must be WrongnessLog, got {type(self.wrongness)}")

    # --- World layer helpers -------------------------------------------------

    def enter_wrong_layer(self) -> None:
        """Flip into the Lyer's arrangement. Used by the Act II encounter."""
        self.world_layer = "wrong"
        # Starting the reunion implicitly: Nika is on her feet in the cabin
        # the moment Elli crashes through the door.
        if self.reunion_stage == "none":
            self.reunion_stage = "arrival"

    def exit_wrong_layer(self) -> None:
        """Return to the real world. Used by the Act V refusal."""
        self.world_layer = "real"
        # The refusal dissolves the reunion along with the wrong cabin.
        self.reunion_stage = "none"
        self.wrong_outside_seen = False

    def is_wrong_layer(self) -> bool:
        return self.world_layer == "wrong"

    def reunion_complete(self) -> bool:
        return self.reunion_stage == "complete"
