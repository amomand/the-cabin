"""Tests for AI-call logging opt-in behaviour."""

import logging

import pytest

import game.config as config_module
import game.logger as logger_module
from game.logger import log_ai_call


@pytest.fixture
def clean_logging_state():
    """Isolate the config and logger singletons around each test."""
    config_module._config = None
    logger_module._game_logger = None
    yield
    named_logger = logging.getLogger("the_cabin")
    for handler in list(named_logger.handlers):
        named_logger.removeHandler(handler)
        handler.close()
    logger_module._game_logger = None
    config_module._config = None


class TestAiCallLoggingOptIn:
    def test_disabled_by_default_writes_nothing(self, tmp_path, monkeypatch, clean_logging_state):
        monkeypatch.delenv("CABIN_AI_LOG", raising=False)
        monkeypatch.setenv("CABIN_LOG_DIR", str(tmp_path / "logs"))
        monkeypatch.chdir(tmp_path)

        log_ai_call("open the door", {"room_name": "cabin"}, {"action": "none"})

        assert not (tmp_path / "logs").exists()

    def test_enabled_via_env_records_call(self, tmp_path, monkeypatch, clean_logging_state):
        monkeypatch.setenv("CABIN_AI_LOG", "1")
        monkeypatch.setenv("CABIN_LOG_DIR", str(tmp_path / "logs"))
        monkeypatch.chdir(tmp_path)

        log_ai_call("open the door", {"room_name": "cabin"}, {"action": "none"})

        log_files = list((tmp_path / "logs").glob("the_cabin_*.log"))
        assert log_files
        contents = "".join(p.read_text() for p in log_files)
        assert "open the door" in contents

    def test_enabled_via_config_file(self, tmp_path, monkeypatch, clean_logging_state):
        monkeypatch.delenv("CABIN_AI_LOG", raising=False)
        monkeypatch.setenv("CABIN_LOG_DIR", str(tmp_path / "logs"))
        monkeypatch.chdir(tmp_path)
        (tmp_path / "config.json").write_text('{"ai_log_enabled": true}')

        log_ai_call("light the fire", {"room_name": "cabin"}, {"action": "light"})

        log_files = list((tmp_path / "logs").glob("the_cabin_*.log"))
        assert log_files
