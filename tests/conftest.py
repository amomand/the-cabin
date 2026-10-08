"""
Pytest configuration and fixtures for The Cabin tests.
"""
import os
import sys
from pathlib import Path

import pytest

# Add project root to path so we can import game modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(autouse=True)
def disable_model_keys_for_tests(monkeypatch):
    """Keep tests on the deterministic rule-based path, whichever provider is configured."""
    from game.env import MODEL_API_KEY_VARS

    for name in MODEL_API_KEY_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("CABIN_MODEL_PROVIDER", raising=False)


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
def sample_map():
    """Create a fresh Map instance for testing."""
    from game.map import Map
    return Map()
