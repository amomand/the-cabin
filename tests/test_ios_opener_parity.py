import re
from pathlib import Path

from game.intro import INTRO_LINES


def test_ios_legacy_opener_fallback_matches_canon() -> None:
    """The migration fallback must never become client-owned story truth."""
    source = (
        Path(__file__).parents[1]
        / "ios"
        / "TheCabin"
        / "Model"
        / "LaunchOpener.swift"
    ).read_text()
    match = re.search(
        r"legacyFallbackLines:\s*\[String\]\s*=\s*\[(.*?)\n\s*\]",
        source,
        re.DOTALL,
    )
    assert match is not None
    swift_lines = tuple(re.findall(r'^\s*"([^"]*)",$', match.group(1), re.MULTILINE))

    assert swift_lines == INTRO_LINES
