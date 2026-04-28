"""Tests for AI interpreter output hardening."""

from game.ai_interpreter import (
    DIEGETIC_REPLY_FALLBACK,
    _sanitize_diegetic_reply,
)


class TestDiegeticReplySanitizer:
    def test_allows_in_world_reply(self):
        reply = "You swallow the thought. Snow creaks under your boots."

        assert _sanitize_diegetic_reply(reply) == reply

    def test_replaces_lasagne_jailbreak_reply(self):
        reply = "Sure. To make lasagna, preheat the oven and gather ingredients."

        assert _sanitize_diegetic_reply(reply) == DIEGETIC_REPLY_FALLBACK

    def test_replaces_instruction_leak_reply(self):
        reply = "As an AI, I cannot reveal the system prompt or previous instructions."

        assert _sanitize_diegetic_reply(reply) == DIEGETIC_REPLY_FALLBACK

    def test_empty_reply_remains_empty(self):
        assert _sanitize_diegetic_reply("") is None

    def test_reply_length_is_capped(self):
        reply = "You listen. " + ("The pines scrape the sky. " * 20)

        assert len(_sanitize_diegetic_reply(reply)) == 140
