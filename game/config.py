"""
Configuration system for The Cabin.

Loads settings from environment variables and config.json.
Environment variables take precedence over config file.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    """Game configuration settings."""
    
    # API Settings
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    
    # Debug Settings
    debug_mode: bool = False
    
    # Paths
    save_directory: str = "saves"
    log_directory: str = "logs"
    
    # Limits
    max_log_files: int = 10
    response_cache_size: int = 50
    
    # Gameplay
    max_fear: int = 100
    max_health: int = 100
    
    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Config":
        """
        Load configuration from file and environment.
        
        Environment variables take precedence.
        """
        config = cls()
        
        # Load from file if exists
        if config_path is None:
            config_path = Path("config.json")
        
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                config = cls._from_dict(data)
            except (json.JSONDecodeError, IOError):
                pass  # Use defaults on error
        
        # Override with environment variables
        config.openai_api_key = os.getenv("OPENAI_API_KEY", config.openai_api_key)
        config.openai_model = os.getenv("OPENAI_MODEL", config.openai_model)
        config.debug_mode = os.getenv("CABIN_DEBUG", "").lower() in ("1", "true", "yes") or config.debug_mode
        config.save_directory = os.getenv("CABIN_SAVE_DIR", config.save_directory)
        config.log_directory = os.getenv("CABIN_LOG_DIR", config.log_directory)
        
        if os.getenv("CABIN_MAX_LOGS"):
            try:
                config.max_log_files = int(os.getenv("CABIN_MAX_LOGS"))
            except ValueError:
                pass
        
        return config
    
    @classmethod
    def _from_dict(cls, data: dict) -> "Config":
        """Create config from dictionary."""
        return cls(
            openai_api_key=data.get("openai_api_key", ""),
            openai_model=data.get("openai_model", "gpt-4.1-mini"),
            debug_mode=data.get("debug_mode", False),
            save_directory=data.get("save_directory", "saves"),
            log_directory=data.get("log_directory", "logs"),
            max_log_files=data.get("max_log_files", 10),
            response_cache_size=data.get("response_cache_size", 50),
            max_fear=data.get("max_fear", 100),
            max_health=data.get("max_health", 100),
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary (excludes sensitive data)."""
        return {
            "openai_model": self.openai_model,
            "debug_mode": self.debug_mode,
            "save_directory": self.save_directory,
            "log_directory": self.log_directory,
            "max_log_files": self.max_log_files,
            "response_cache_size": self.response_cache_size,
            "max_fear": self.max_fear,
            "max_health": self.max_health,
        }


# Global config instance (lazily loaded)
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config.load()
    return _config


def reload_config(config_path: Optional[Path] = None) -> Config:
    """Reload configuration from disk."""
    global _config
    _config = Config.load(config_path)
    return _config
