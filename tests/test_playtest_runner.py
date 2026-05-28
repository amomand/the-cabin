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
