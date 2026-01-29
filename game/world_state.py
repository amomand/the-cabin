"""
Typed world state for The Cabin.

This replaces the untyped Dict[str, object] with a proper dataclass
that provides type safety, validation, and IDE autocomplete.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional


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
        result = {}
        # Add explicit fields (excluding private ones)
        for key, value in asdict(self).items():
            if key == '_custom_flags':
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
        known_fields = {'has_power', 'fire_lit'}
        
        explicit = {}
        custom = {}
        
        for key, value in data.items():
            if key in known_fields:
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
