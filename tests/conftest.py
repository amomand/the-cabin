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
def hermetic_model_settings(monkeypatch):
    """Keep tests on the shipped defaults and the deterministic rule-based path.

    A developer's shell or `.env` may carry keys, a provider, a model or the
    iOS transport setting; none of it may leak into a test, and a test that
    sets one of these must not leave it in the cached config for the next.
    """
    import game.config
    from game.env import MODEL_API_KEY_VARS

    for name in MODEL_API_KEY_VARS + (
        "CABIN_MODEL_PROVIDER",
        "CABIN_MODEL_TRANSPORT",
        "ANTHROPIC_MODEL",
        "ANTHROPIC_THINKING",
        "OPENAI_MODEL",
        "OPENAI_REASONING_EFFORT",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(game.config, "_config", None)


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
