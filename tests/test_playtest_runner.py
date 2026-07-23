from pathlib import Path

import pytest

from tools.playtest_runner import (
    DEFAULT_FORBIDDEN_PHRASES,
    Scenario,
    WebScenarioDriver,
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
