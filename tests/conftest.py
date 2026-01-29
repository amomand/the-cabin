"""
Pytest configuration and fixtures for The Cabin tests.
"""
import sys
from pathlib import Path

import pytest

# Add project root to path so we can import game modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def sample_player():
    """Create a fresh Player instance for testing."""
    from game.player import Player
    return Player()


@pytest.fixture
def sample_items():
    """Create the game's item collection."""
    from game.item import create_items
    return create_items()


@pytest.fixture
def sample_wildlife():
    """Create the game's wildlife collection."""
    from game.wildlife import create_wildlife
    return create_wildlife()


@pytest.fixture
def sample_map():
    """Create a fresh Map instance for testing."""
    from game.map import Map
    return Map()
