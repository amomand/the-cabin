import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from game.config import get_config


def _cleanup_old_logs(log_dir: Path, max_files: int) -> None:
    """Remove old log files, keeping only the most recent max_files."""
    log_files = sorted(log_dir.glob("the_cabin_*.log"), key=lambda p: p.stat().st_mtime)
    
    # Remove oldest files if we have too many
    while len(log_files) > max_files:
        oldest = log_files.pop(0)
        try:
            oldest.unlink()
        except OSError:
            pass


class GameLogger:
    """Comprehensive logging system for The Cabin game."""
    
    def __init__(self, log_file: Optional[str] = None):
        self.logger = logging.getLogger('the_cabin')
        self.logger.setLevel(logging.DEBUG)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler (only for INFO and above, and only if CABIN_DEBUG=1)
        config = get_config()
        if config.debug_mode:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # File handler (always active for debugging)
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        
        # Prevent duplicate logs
        self.logger.propagate = False
    
    def debug(self, message: str) -> None:
        """Log debug message."""
        self.logger.debug(message)
    
    def info(self, message: str) -> None:
        """Log info message."""
        self.logger.info(message)
    
    def warning(self, message: str) -> None:
        """Log warning message."""
        self.logger.warning(message)
    
    def error(self, message: str) -> None:
        """Log error message."""
        self.logger.error(message)
    
    def critical(self, message: str) -> None:
        """Log critical message."""
        self.logger.critical(message)

# Global logger instance
_game_logger: Optional[GameLogger] = None

def get_logger() -> GameLogger:
    """Get the global logger instance."""
    global _game_logger
    if _game_logger is None:
        config = get_config()
        log_dir = Path(config.log_directory)
        
        # Create logs directory if it doesn't exist
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Clean up old log files
        _cleanup_old_logs(log_dir, config.max_log_files)
        
        # Create log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"the_cabin_{timestamp}.log"
        
        _game_logger = GameLogger(str(log_file))
        _game_logger.info("Game logger initialized")
    
    return _game_logger
    
    return _game_logger

def log_ai_call(user_input: str, context: dict, response: dict, error: Optional[str] = None) -> None:
    """Log AI interpreter calls for debugging."""
    logger = get_logger()
    
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "user_input": user_input,
        "context": {
            "room_name": context.get("room_name"),
            "exits": context.get("exits"),
            "room_items": context.get("room_items"),
            "inventory": context.get("inventory"),
            "world_flags": context.get("world_flags")
        },
        "response": response,
        "error": error
    }
    
    if error:
        logger.error(f"AI call failed: {log_data}")
    else:
        logger.info(f"AI call successful: {log_data}")

def log_quest_event(event_type: str, event_data: dict) -> None:
    """Log quest-related events."""
    logger = get_logger()
    logger.info(f"Quest event - {event_type}: {event_data}")

def log_game_action(action: str, args: dict, result: str) -> None:
    """Log game actions and their results."""
    logger = get_logger()
    logger.info(f"Game action - {action}: {args} -> {result}")
