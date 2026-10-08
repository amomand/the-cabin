"""Provider configuration: defaults, environment overrides, and the live label."""

from game.config import Config


def test_default_provider_is_anthropic_sonnet_with_thinking_off():
    config = Config()

    assert config.model_provider == "anthropic"
    assert config.anthropic_model == "claude-sonnet-5-5"
    assert config.anthropic_thinking == "off"
    assert config.live_model_label == "claude-sonnet-5-5:off"


def test_environment_overrides_provider_model_and_thinking(monkeypatch, tmp_path):
    monkeypatch.setenv("CABIN_MODEL_PROVIDER", " OpenAI ")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-haiku-5-5")
    monkeypatch.setenv("ANTHROPIC_THINKING", "low")

    config = Config.load(tmp_path / "missing.json")

    assert config.model_provider == "openai"
    assert config.anthropic_model == "claude-haiku-5-5"
    assert config.anthropic_thinking == "low"
    assert config.live_model_label == "gpt-5.6-terra:none"


def test_to_dict_describes_the_provider_without_keys(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "secret")
    config = Config.load()

    exported = config.to_dict()

    assert exported["model_provider"] == "anthropic"
    assert exported["anthropic_model"] == "claude-sonnet-5-5"
    assert "secret" not in str(exported)
