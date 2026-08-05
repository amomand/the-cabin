import contextlib
import io
from pathlib import Path
from unittest.mock import patch

from game.cutscene import Cutscene, CutsceneManager

import pytest

from tools.playtest_runner import (
    DEFAULT_FORBIDDEN_PHRASES,
    Scenario,
    TerminalScenarioDriver,
    TranscriptEntry,
    WebScenarioDriver,
    _normalise_surface_output,
    load_scenario,
    run_scenario,
    write_report,
)


def test_load_scenario_reads_yaml_subset(tmp_path):
    path = tmp_path / "scenario.yaml"
    path.write_text(
        "\n".join(
            [
                "name: sample",
                "surface: web",
                "description: A tiny scenario.",
                "offline_ai: true",
                "commands:",
                "  - look",
                "  - north",
                "required_phrases:",
                "  - Health:",
            ]
        ),
        encoding="utf-8",
    )

    scenario = load_scenario(path)

    assert scenario.name == "sample"
    assert scenario.surface == "web"
    assert scenario.commands == ("look", "north")
    assert scenario.required_phrases == ("Health:",)
    assert scenario.forbidden_phrases == DEFAULT_FORBIDDEN_PHRASES


def test_load_scenario_allows_empty_description_scalar(tmp_path):
    path = tmp_path / "scenario.yaml"
    path.write_text(
        "\n".join(
            [
                "name: sample",
                "surface: web",
                "description:",
                "commands:",
                "  - look",
            ]
        ),
        encoding="utf-8",
    )

    scenario = load_scenario(path)

    assert scenario.description == ""


def test_load_scenario_rejects_quoted_boolean(tmp_path):
    path = tmp_path / "scenario.yaml"
    path.write_text(
        "\n".join(
            [
                "name: sample",
                "surface: web",
                'offline_ai: "false"',
                "commands:",
                "  - look",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="offline_ai must be true or false"):
        load_scenario(path)


def test_load_scenario_comment_stripping_handles_contractions(tmp_path):
    path = tmp_path / "scenario.yaml"
    path.write_text(
        "\n".join(
            [
                "name: sample",
                "surface: web",
                "description: It's cold # stripped",
                "commands:",
                '  - "look # not stripped"',
            ]
        ),
        encoding="utf-8",
    )

    scenario = load_scenario(path)

    assert scenario.description == "It's cold"
    assert scenario.commands == ("look # not stripped",)


def test_load_scenario_reads_expected_state(tmp_path):
    path = tmp_path / "scenario.yaml"
    path.write_text(
        "\n".join(
            [
                "name: sample",
                "surface: web",
                "commands:",
                "  - look",
                "expected_state:",
                "  - world_layer=real",
                "  - ending=none",
            ]
        ),
        encoding="utf-8",
    )

    scenario = load_scenario(path)

    assert scenario.expected_state == ("world_layer=real", "ending=none")


def test_load_scenario_rejects_malformed_expected_state(tmp_path):
    path = tmp_path / "scenario.yaml"
    path.write_text(
        "\n".join(
            [
                "name: sample",
                "surface: web",
                "commands:",
                "  - look",
                "expected_state:",
                "  - world_layer real",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="expected_state entries must be 'key=value'"):
        load_scenario(path)


def test_web_scenario_records_visible_output(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    scenario = Scenario(
        name="web-smoke",
        surface="web",
        commands=("look", "north"),
        required_phrases=("The Clearing", "Health:"),
    )

    result = run_scenario(scenario)

    assert result.passed
    assert any("The Clearing" in "\n".join(entry.lines) for entry in result.entries)


def test_web_driver_removes_default_session_save_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    driver = WebScenarioDriver()
    try:
        assert not list((tmp_path / "saves" / "web").glob("*"))
        assert driver.session.save_manager.save_dir.parent == Path(driver._tempdir.name)
    finally:
        driver.close()


def test_terminal_scenario_records_visible_output(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    scenario = Scenario(
        name="terminal-smoke",
        surface="terminal",
        commands=("look", "north"),
        required_phrases=("The Clearing", "Health:"),
    )

    result = run_scenario(scenario)

    assert result.passed
    assert any("What would you like to do?" in "\n".join(entry.lines) for entry in result.entries)


def test_forbidden_phrase_becomes_finding(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    scenario = Scenario(
        name="forbidden",
        surface="web",
        commands=("look",),
        forbidden_phrases=("Wilderness",),
    )

    result = run_scenario(scenario)

    assert not result.passed
    assert "forbidden phrase found: 'Wilderness'" in result.findings


def test_write_report_includes_findings_and_transcript(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    scenario = Scenario(name="../report path", surface="web", commands=("look",))
    result = run_scenario(scenario)

    report = write_report(result, tmp_path)

    assert Path(report).parent == tmp_path
    assert Path(report).name == "report_path.txt"
    text = Path(report).read_text(encoding="utf-8")
    assert "Playtest Report: ../report path" in text
    assert "## Findings" in text
    assert "## Transcript" in text


def test_scenario_captures_story_state(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    scenario = Scenario(name="state", surface="web", commands=("look",))

    result = run_scenario(scenario)

    assert result.state["world_layer"] == "real"
    assert result.state["reunion_stage"] == "none"
    assert result.state["ending"] == "none"
    assert result.state["ended"] == "false"
    assert result.state["wrongness_count"] == "0"
    assert result.state["wrongness"] == "none"


def test_terminal_scenario_captures_story_state(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    scenario = Scenario(name="state", surface="terminal", commands=("look",))

    result = run_scenario(scenario)

    assert result.state["world_layer"] == "real"
    assert result.state["ended"] == "false"


def test_expected_state_match_passes(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    scenario = Scenario(
        name="state-match",
        surface="web",
        commands=("look",),
        expected_state=("world_layer=real", "ending=none"),
    )

    result = run_scenario(scenario)

    assert result.passed


def test_expected_state_mismatch_becomes_finding(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    scenario = Scenario(
        name="state-mismatch",
        surface="web",
        commands=("look",),
        expected_state=("world_layer=wrong", "no_such_key=1"),
    )

    result = run_scenario(scenario)

    assert not result.passed
    assert (
        "state mismatch: world_layer is 'real', expected 'wrong'" in result.findings
    )
    assert "expected state key not captured: 'no_such_key'" in result.findings


def test_write_report_includes_story_state_block(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    scenario = Scenario(name="state-report", surface="web", commands=("look",))
    result = run_scenario(scenario)

    report = write_report(result, tmp_path)

    text = Path(report).read_text(encoding="utf-8")
    assert "## Story state at close" in text
    assert "world_layer: real" in text
    assert text.index("## Story state at close") < text.index("## Transcript")


class TestDifferentialSurface:
    """`surface: both` plays one script through both surfaces and fails if they
    disagree about anything the player can see (issue #179)."""

    def test_load_scenario_accepts_both(self, tmp_path):
        path = tmp_path / "scenario.yaml"
        path.write_text(
            "\n".join(
                [
                    "name: differential",
                    "surface: both",
                    "commands:",
                    "  - look",
                ]
            ),
            encoding="utf-8",
        )

        assert load_scenario(path).surface == "both"

    def test_load_scenario_still_rejects_an_unknown_surface(self, tmp_path):
        path = tmp_path / "scenario.yaml"
        path.write_text(
            "\n".join(
                [
                    "name: nonsense",
                    "surface: telepathy",
                    "commands:",
                    "  - look",
                ]
            ),
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="surface must be one of"):
            load_scenario(path)

    def test_matching_surfaces_pass(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        scenario = Scenario(
            name="differential-smoke",
            surface="both",
            commands=("look", "north", "south", "inventory"),
            required_phrases=("The Clearing", "Health:"),
        )

        result = run_scenario(scenario)

        assert result.findings == []

    def test_rendering_drift_is_a_finding(self, monkeypatch):
        """The point of the mode: a surface that renders differently fails."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        original = WebScenarioDriver.send

        def drifting_send(self, command):
            entries = original(self, command)
            return [
                TranscriptEntry(entry.label, entry.lines + ("a wall of cold",))
                for entry in entries
            ]

        monkeypatch.setattr(WebScenarioDriver, "send", drifting_send)
        scenario = Scenario(name="drift", surface="both", commands=("look",))

        result = run_scenario(scenario)

        assert any("rendered" in finding for finding in result.findings)

    def test_story_state_drift_is_a_finding(self, monkeypatch):
        """Text can match while the two surfaces have decided different things."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        def drifting_state(self):
            return {"room": "somewhere else", "fear": "99"}

        monkeypatch.setattr(WebScenarioDriver, "state_summary", drifting_state)
        scenario = Scenario(name="state-drift", surface="both", commands=("look",))

        result = run_scenario(scenario)

        assert any("story state" in finding for finding in result.findings)

    def test_the_terminal_driver_sandboxes_its_saves(self, tmp_path, monkeypatch):
        """Both surfaces must save into a tempdir, or a differential scenario
        with a `save` command writes into the repo on one side only."""
        monkeypatch.chdir(tmp_path)

        driver = TerminalScenarioDriver()
        try:
            assert driver.engine.save_manager.save_dir.parent == Path(driver._tempdir.name)
        finally:
            driver.close()

        assert not (tmp_path / "saves").exists()


class TestSurfaceOutputNormalisation:
    """What the differential comparison deliberately ignores, and what it does
    not. Everything that survives normalisation is something a player would
    notice, which is the contract the mode enforces."""

    def _entry(self, *lines):
        return [TranscriptEntry("## > look", tuple(lines))]

    def test_hard_wrapping_is_ignored(self):
        wrapped = self._entry("The door groans the same way", "it always has.")
        joined = self._entry("The door groans the same way it always has.")

        assert _normalise_surface_output(wrapped) == _normalise_surface_output(joined)

    def test_entry_cardinality_is_ignored(self):
        one_entry = self._entry("You run.", "A tree full on.")
        two_entries = [
            TranscriptEntry("## > look", ("You run.",)),
            TranscriptEntry("## Auto-dismiss overlay 1", ("A tree full on.",)),
        ]

        assert _normalise_surface_output(one_entry) == _normalise_surface_output(two_entries)

    def test_the_terminal_only_prompt_is_ignored_on_the_terminal_side(self):
        with_prompt = self._entry("Health: 100    Fear: 0", "What would you like to do?")
        without = self._entry("Health: 100    Fear: 0")

        assert _normalise_surface_output(
            with_prompt, drop_prompt=True
        ) == _normalise_surface_output(without)

    def test_the_web_gaining_the_prompt_is_not_ignored(self):
        """The filter is one-sided on purpose. The terminal prints the prompt
        and the web carries it in `RenderFrame.prompt`, so masking it on both
        sides would hide the web growing one."""
        with_prompt = self._entry("Health: 100    Fear: 0", "What would you like to do?")
        without = self._entry("Health: 100    Fear: 0")

        assert _normalise_surface_output(with_prompt) != _normalise_surface_output(without)

    def test_overlay_cue_emphasis_is_ignored(self):
        emphasised = self._entry("*Pull yourself back.*")
        bare = self._entry("Pull yourself back.")

        assert _normalise_surface_output(emphasised) == _normalise_surface_output(bare)

    def test_emphasis_on_ordinary_prose_is_not_ignored(self):
        """Only known cues lose their asterisks. Stripping every line would
        make emphasis drift invisible anywhere else, and asterisks are the
        web's only emphasis channel."""
        emphasised = self._entry("*The hearth is cold.*")
        plain = self._entry("The hearth is cold.")

        assert _normalise_surface_output(emphasised) != _normalise_surface_output(plain)

    def test_save_timestamps_are_ignored_but_slot_names_are_not(self):
        first = self._entry("probe (2026-08-05T21:43:26.781813)")
        second = self._entry("probe (2026-08-05T21:43:26.781986)")
        renamed = self._entry("other (2026-08-05T21:43:26.781813)")

        assert _normalise_surface_output(first) == _normalise_surface_output(second)
        assert _normalise_surface_output(first) != _normalise_surface_output(renamed)

    def test_a_missing_line_is_not_ignored(self):
        """The bug this mode found first: a quest update swallowed on one
        surface and printed on the other."""
        full = self._entry("Konttori", "Power hums through the cabin.", "Health: 100")
        missing = self._entry("Konttori", "Health: 100")

        assert _normalise_surface_output(full) != _normalise_surface_output(missing)


class TestTerminalCutsceneStubIsFaithful:
    """In a `surface: both` scenario the runner's cutscene stub *is* the
    terminal surface as far as the comparison is concerned. Anything it prints
    differently from the real `Cutscene.play` is a divergence the differential
    mode would certify as parity — worse than no coverage, because it looks
    like coverage.
    """

    def _stub_output(self, cutscene):
        stub = TerminalScenarioDriver._cutscene_play_once(cutscene)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            stub()
        return buffer.getvalue()

    def _real_output(self, cutscene):
        """The real `play()` with only the terminal clears and the blocking
        keypress stubbed out — everything it prints is kept."""
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer), \
                patch.object(Cutscene, "_clear_terminal", lambda self: None), \
                patch.object(Cutscene, "_wait_for_key", lambda self: None):
            cutscene.play()
        return buffer.getvalue()

    def test_the_stub_prints_what_the_real_play_prints(self):
        manager = CutsceneManager()
        assert manager.cutscenes, "expected at least one authored cutscene"

        for authored in manager.cutscenes:
            stub = self._stub_output(authored)
            authored.has_played = False
            real = self._real_output(authored)

            # Name the scene by its first line of prose. `Cutscene` has no id
            # field, and referring to one only shows up as an AttributeError
            # in place of the message, on the one run where the message matters.
            opening = next(
                (line for line in authored.text.splitlines() if line.strip("─ ")),
                "<unnamed>",
            )
            assert stub == real, f"stub diverges from play() for {opening[:40]!r}"
