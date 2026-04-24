from pathlib import Path

from game.config import Config


def test_config_defaults_to_gpt54_mini_non_reasoning():
    config = Config()

    assert config.openai_model == "gpt-5.4-mini"
    assert config.openai_reasoning_effort == "none"


def test_config_loads_reasoning_effort_from_file(tmp_path: Path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        '{"openai_model": "gpt-5-mini", "openai_reasoning_effort": "low"}',
        encoding="utf-8",
    )

    config = Config.load(config_path)

    assert config.openai_model == "gpt-5-mini"
    assert config.openai_reasoning_effort == "low"


def test_config_env_overrides_reasoning_effort(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5.5")
    monkeypatch.setenv("OPENAI_REASONING_EFFORT", "none")

    config = Config.load(Path("/missing/config.json"))

    assert config.openai_model == "gpt-5.5"
    assert config.openai_reasoning_effort == "none"
