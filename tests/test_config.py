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


def test_to_dict_describes_the_provider_without_keys(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "secret")
    config = Config.load(tmp_path / "missing.json")

    exported = config.to_dict()

    assert exported["model_provider"] == "anthropic"
    assert exported["anthropic_model"] == "claude-sonnet-5-5"
    assert "secret" not in str(exported)


def test_blank_provider_variable_means_not_set(monkeypatch, tmp_path):
    # A blank .env line or a compose file passing an unset value through
    # must not turn into "no provider".
    (tmp_path / "config.json").write_text('{"model_provider": "openai"}')
    monkeypatch.setenv("CABIN_MODEL_PROVIDER", "")

    config = Config.load(tmp_path / "config.json")

    assert config.model_provider == "openai"


def test_null_provider_in_config_file_falls_back_to_default(tmp_path):
    (tmp_path / "config.json").write_text('{"model_provider": null, "anthropic_thinking": null}')

    config = Config.load(tmp_path / "config.json")

    assert config.model_provider == "anthropic"
    assert config.anthropic_thinking == "off"


def test_thinking_setting_is_normalised(monkeypatch, tmp_path):
    for raw in (" OFF ", "disabled", "none"):
        monkeypatch.setenv("ANTHROPIC_THINKING", raw)
        assert Config.load(tmp_path / "missing.json").anthropic_thinking == "off"
    monkeypatch.setenv("ANTHROPIC_THINKING", " Low")
    assert Config.load(tmp_path / "missing.json").anthropic_thinking == "low"


def test_live_label_names_an_unknown_provider(tmp_path):
    (tmp_path / "config.json").write_text('{"model_provider": "gemini"}')

    assert Config.load(tmp_path / "config.json").live_model_label == "unknown-provider:gemini"


def test_whitespace_only_variables_mean_not_set(monkeypatch, tmp_path):
    (tmp_path / "config.json").write_text('{"model_provider": "openai", "anthropic_thinking": "low", "openai_model": "gpt-6-luna"}')
    monkeypatch.setenv("CABIN_MODEL_PROVIDER", "   ")
    monkeypatch.setenv("ANTHROPIC_THINKING", " ")
    monkeypatch.setenv("OPENAI_MODEL", "")

    config = Config.load(tmp_path / "config.json")

    assert config.model_provider == "openai"
    assert config.anthropic_thinking == "low"
    assert config.openai_model == "gpt-6-luna"


def test_a_developers_config_file_does_not_reach_the_suite():
    # The autouse fixture points the default path away from the working
    # directory; a stray config.json beside pytest must not change a test.
    from game.config import get_config

    assert get_config().model_provider == "anthropic"
