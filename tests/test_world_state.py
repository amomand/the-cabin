"""
Tests for WorldState typed state management.
"""
import pytest
from game.story.anomalies import AnomalyID
from game.world_state import WorldState, WrongnessLog


class TestWorldState:
    """Tests for WorldState dataclass."""

    def test_default_values(self):
        """WorldState should have sensible defaults."""
        state = WorldState()
        assert state.has_power is False
        assert state.fire_lit is False
        assert state.ending == "none"

    def test_explicit_initialization(self):
        """WorldState can be initialized with explicit values."""
        state = WorldState(has_power=True, fire_lit=True)
        assert state.has_power is True
        assert state.fire_lit is True

    def test_dict_style_get(self):
        """WorldState supports dict-style get() for backward compatibility."""
        state = WorldState(has_power=True)
        assert state.get("has_power") is True
        assert state.get("fire_lit") is False
        assert state.get("nonexistent", "default") == "default"

    def test_dict_style_bracket_access(self):
        """WorldState supports bracket access for backward compatibility."""
        state = WorldState(has_power=True)
        assert state["has_power"] is True
        
        with pytest.raises(KeyError):
            _ = state["nonexistent"]

    def test_dict_style_bracket_assignment(self):
        """WorldState supports bracket assignment for backward compatibility."""
        state = WorldState()
        state["has_power"] = True
        assert state.has_power is True
        
        # Unknown keys go to custom flags
        state["custom_flag"] = "value"
        assert state.get("custom_flag") == "value"

    def test_contains(self):
        """WorldState supports 'in' operator."""
        state = WorldState()
        assert "has_power" in state
        assert "fire_lit" in state
        assert "nonexistent" not in state
        
        state.set_flag("custom", True)
        assert "custom" in state

    def test_custom_flags(self):
        """WorldState can store custom flags."""
        state = WorldState()
        state.set_flag("quest_started", True)
        state.set_flag("npc_talked_to", "eli")
        
        assert state.get_flag("quest_started") is True
        assert state.get_flag("npc_talked_to") == "eli"
        assert state.get_flag("nonexistent", "default") == "default"

    def test_to_dict(self):
        """WorldState can be converted to dict for serialization."""
        state = WorldState(has_power=True, fire_lit=False)
        state.set_flag("custom", "value")
        
        d = state.to_dict()
        
        assert d["has_power"] is True
        assert d["fire_lit"] is False
        assert d["custom"] == "value"

    def test_from_dict(self):
        """WorldState can be restored from dict."""
        data = {
            "has_power": True,
            "fire_lit": True,
            "ending": "accepted",
            "custom_flag": "custom_value",
        }
        
        state = WorldState.from_dict(data)
        
        assert state.has_power is True
        assert state.fire_lit is True
        assert state.ending == "accepted"
        assert state.get_flag("custom_flag") == "custom_value"

    def test_from_dict_round_trip(self):
        """WorldState survives serialization round-trip."""
        original = WorldState(has_power=True)
        original.ending = "refused"
        original.set_flag("quest_progress", 3)
        
        restored = WorldState.from_dict(original.to_dict())
        
        assert restored.has_power == original.has_power
        assert restored.fire_lit == original.fire_lit
        assert restored.ending == original.ending
        assert restored.get_flag("quest_progress") == 3

    def test_validate_success(self):
        """validate() passes for valid state."""
        state = WorldState(has_power=True, fire_lit=False)
        state.validate()  # Should not raise

    def test_validate_invalid_type(self):
        """validate() raises for invalid types."""
        state = WorldState()
        state.has_power = "yes"  # type: ignore - intentionally wrong
        
        with pytest.raises(ValueError, match="has_power must be bool"):
            state.validate()


class TestWorldLayer:
    """Tests for the real/wrong world layer flag."""

    def test_defaults_to_real(self):
        state = WorldState()
        assert state.world_layer == "real"
        assert state.is_wrong_layer() is False

    def test_enter_and_exit_wrong_layer(self):
        state = WorldState()
        state.enter_wrong_layer()
        assert state.world_layer == "wrong"
        assert state.is_wrong_layer() is True
        state.exit_wrong_layer()
        assert state.world_layer == "real"
        assert state.is_wrong_layer() is False

    def test_persists_across_serialisation(self):
        state = WorldState()
        state.enter_wrong_layer()
        restored = WorldState.from_dict(state.to_dict())
        assert restored.world_layer == "wrong"

    def test_invalid_layer_coerced_on_load(self):
        restored = WorldState.from_dict({"world_layer": "nonsense"})
        assert restored.world_layer == "real"

    def test_validate_rejects_bad_layer(self):
        state = WorldState()
        state.world_layer = "other"  # type: ignore - intentionally wrong
        with pytest.raises(ValueError, match="world_layer"):
            state.validate()


class TestFalseCabinNightStages:
    """Tests for the extended reunion/night stage model and consent flag.

    The later stages (tended, consented, bedded, night, dawn) and the
    escaped/stayed endings are foundations for the rewritten-canon arc
    (issue #141); v1 beats do not set them yet.
    """

    def test_defaults(self):
        state = WorldState()
        assert state.reunion_stage == "none"
        assert state.consent_given is False
        assert state.ending == "none"

    def test_all_stages_round_trip(self):
        for stage in (
            "none", "arrival", "tended", "seated", "complete",
            "consented", "bedded", "night", "dawn",
        ):
            state = WorldState()
            state.reunion_stage = stage
            restored = WorldState.from_dict(state.to_dict())
            assert restored.reunion_stage == stage

    def test_invalid_stage_coerced_on_load(self):
        restored = WorldState.from_dict({"reunion_stage": "nonsense"})
        assert restored.reunion_stage == "none"

    def test_new_endings_round_trip(self):
        for ending in ("none", "accepted", "refused", "escaped", "stayed"):
            restored = WorldState.from_dict({"ending": ending})
            assert restored.ending == ending

    def test_invalid_ending_coerced_on_load(self):
        restored = WorldState.from_dict({"ending": "won"})
        assert restored.ending == "none"

    def test_invalid_coda_stage_coerced_on_load(self):
        restored = WorldState.from_dict({"coda_stage": "epilogue"})
        assert restored.coda_stage == "none"

    def test_coda_stages_round_trip(self):
        for stage in ("none", "home", "called", "scraping", "end"):
            state = WorldState.from_dict({"coda_stage": stage})
            assert WorldState.from_dict(state.to_dict()).coda_stage == stage

    def test_consent_given_round_trip(self):
        state = WorldState()
        state.consent_given = True
        restored = WorldState.from_dict(state.to_dict())
        assert restored.consent_given is True

    def test_exit_wrong_layer_clears_consent(self):
        state = WorldState()
        state.enter_wrong_layer()
        state.consent_given = True
        state.exit_wrong_layer()
        assert state.consent_given is False
        assert state.reunion_stage == "none"

    def test_stage_ordering_helper(self):
        state = WorldState()
        state.reunion_stage = "night"
        assert state.reunion_stage_at_least("complete") is True
        assert state.reunion_stage_at_least("night") is True
        assert state.reunion_stage_at_least("dawn") is False
        state.reunion_stage = "seated"
        assert state.reunion_stage_at_least("complete") is False

    def test_stage_ordering_tolerates_unknown_values(self):
        """A bad direct assignment must compare as False, not raise."""
        state = WorldState()
        state["reunion_stage"] = "garbage"  # dict-style compat API bypasses coercion
        assert state.reunion_stage_at_least("complete") is False
        assert state.reunion_complete() is False

    def test_reunion_complete_holds_past_complete(self):
        state = WorldState()
        state.reunion_stage = "complete"
        assert state.reunion_complete() is True
        # The gate must keep holding as the night advances.
        for stage in ("consented", "bedded", "night", "dawn"):
            state.reunion_stage = stage
            assert state.reunion_complete() is True
        state.reunion_stage = "seated"
        assert state.reunion_complete() is False


class TestStoryArcTransitions:
    """Executable constraints for the persisted string-valued story arc."""

    def test_reunion_advances_one_beat_at_a_time(self):
        state = WorldState()

        for stage in (
            "arrival",
            "tended",
            "seated",
            "complete",
            "consented",
            "bedded",
            "night",
            "dawn",
        ):
            assert state.transition_reunion_to(stage) is True
            assert state.reunion_stage == stage

    @pytest.mark.parametrize(
        ("current", "target"),
        (
            ("none", "complete"),
            ("arrival", "arrival"),
            ("complete", "seated"),
        ),
        ids=("skip", "repeat", "backwards"),
    )
    def test_forbidden_reunion_transitions_do_not_mutate(self, current, target):
        state = WorldState.from_dict({"reunion_stage": current})

        assert state.transition_reunion_to(target) is False
        assert state.reunion_stage == current

    def test_malformed_direct_reunion_stage_is_terminal(self):
        state = WorldState()
        state["reunion_stage"] = "garbage"

        assert state.transition_reunion_to("arrival") is False
        assert state.reunion_stage == "garbage"

    @pytest.mark.parametrize("ending", ("escaped", "stayed"))
    def test_current_endings_can_be_chosen_once(self, ending):
        state = WorldState()

        assert state.transition_ending_to(ending) is True
        assert state.ending == ending
        assert state.transition_ending_to(ending) is False

    @pytest.mark.parametrize("legacy_ending", ("accepted", "refused"))
    def test_legacy_endings_remain_loadable_and_terminal(self, legacy_ending):
        state = WorldState.from_dict({"ending": legacy_ending})

        assert state.ending == legacy_ending
        assert state.transition_ending_to("escaped") is False
        assert state.ending == legacy_ending

    def test_coda_advances_one_beat_at_a_time(self):
        state = WorldState()

        for stage in ("home", "called", "scraping", "end"):
            assert state.transition_coda_to(stage) is True
            assert state.coda_stage == stage

    @pytest.mark.parametrize(
        ("current", "target"),
        (
            ("none", "called"),
            ("home", "scraping"),
            ("scraping", "called"),
            ("end", "home"),
        ),
    )
    def test_forbidden_coda_transitions_do_not_mutate(self, current, target):
        state = WorldState.from_dict({"coda_stage": current})

        assert state.transition_coda_to(target) is False
        assert state.coda_stage == current

    def test_malformed_direct_coda_and_ending_values_are_terminal(self):
        state = WorldState()
        state["coda_stage"] = "garbage"
        state["ending"] = "won"

        assert state.transition_coda_to("home") is False
        assert state.transition_ending_to("escaped") is False
        assert state.coda_stage == "garbage"
        assert state.ending == "won"

    @pytest.mark.parametrize(
        ("field", "transition", "target"),
        (
            ("reunion_stage", "transition_reunion_to", "arrival"),
            ("ending", "transition_ending_to", "escaped"),
            ("coda_stage", "transition_coda_to", "home"),
        ),
    )
    def test_unhashable_direct_arc_values_are_terminal(
        self, field, transition, target
    ):
        state = WorldState()
        malformed = []
        state[field] = malformed

        assert getattr(state, transition)(target) is False
        assert getattr(state, field) is malformed


class TestWrongnessLog:
    """Tests for the accumulating wrongness log."""

    def test_empty_by_default(self):
        state = WorldState()
        assert state.wrongness.count() == 0
        assert state.wrongness.threshold_met(n=1) is False

    def test_add_logs_new_anomaly(self):
        log = WrongnessLog()
        assert log.add(AnomalyID.FOX_TRACKS.value, "tracks end mid-stride") is True
        assert log.count() == 1
        assert log.has(AnomalyID.FOX_TRACKS.value) is True

    def test_add_is_idempotent_per_anomaly(self):
        log = WrongnessLog()
        assert log.add(AnomalyID.FOX_TRACKS.value) is True
        assert log.add(AnomalyID.FOX_TRACKS.value) is False
        assert log.count() == 1

    def test_seen_at_reflects_insertion_order(self):
        log = WrongnessLog()
        log.add("a")
        log.add("b")
        log.add("c")
        assert [e.seen_at for e in log.entries] == [0, 1, 2]
        assert [e.anomaly_id for e in log.entries] == ["a", "b", "c"]

    def test_threshold_met(self):
        log = WrongnessLog()
        log.add("a")
        log.add("b")
        assert log.threshold_met(n=3) is False
        log.add("c")
        assert log.threshold_met(n=3) is True

    def test_acknowledge(self):
        log = WrongnessLog()
        log.add("a")
        assert log.acknowledged_count() == 0
        assert log.acknowledge("a") is True
        assert log.acknowledged_count() == 1
        assert log.acknowledge("missing") is False

    def test_serialisation_round_trip(self):
        state = WorldState()
        state.wrongness.add(AnomalyID.FOX_TRACKS.value, "tracks end mid-stride")
        state.wrongness.add(AnomalyID.HARE.value, "unbreathing hare")
        state.wrongness.acknowledge(AnomalyID.FOX_TRACKS.value)

        restored = WorldState.from_dict(state.to_dict())
        assert restored.wrongness.count() == 2
        assert restored.wrongness.has(AnomalyID.FOX_TRACKS.value)
        ack = [
            e
            for e in restored.wrongness.entries
            if e.anomaly_id == AnomalyID.FOX_TRACKS.value
        ][0]
        assert ack.acknowledged is True
        assert ack.description == "tracks end mid-stride"

    def test_from_dict_handles_missing_wrongness(self):
        restored = WorldState.from_dict({"has_power": True})
        assert restored.wrongness.count() == 0

    def test_validate_rejects_non_log(self):
        state = WorldState()
        state.wrongness = {}  # type: ignore - intentionally wrong
        with pytest.raises(ValueError, match="wrongness"):
            state.validate()


class TestStoryPhase:
    """The coarse phase is derived from the flags that already drive the gates."""

    @pytest.mark.parametrize(
        "setup, expected",
        [
            (lambda ws: None, "evening"),
            (lambda ws: setattr(ws, "fire_lit", True), "evening"),
            (lambda ws: setattr(ws, "first_morning", True), "morning"),
            (lambda ws: (setattr(ws, "first_morning", True), ws.enter_wrong_layer()), "wrong"),
            (
                lambda ws: (ws.enter_wrong_layer(), setattr(ws, "ending", "escaped")),
                "wrong",
            ),
            (
                lambda ws: (
                    setattr(ws, "first_morning", True),
                    setattr(ws, "ending", "escaped"),
                    setattr(ws, "coda_stage", "home"),
                ),
                "coda",
            ),
            (lambda ws: (ws.enter_wrong_layer(), setattr(ws, "ending", "stayed")), "stayed"),
            (lambda ws: (ws.enter_wrong_layer(), setattr(ws, "ending", "accepted")), "stayed"),
            (lambda ws: setattr(ws, "ending", "refused"), "coda"),
        ],
        ids=[
            "arrival",
            "fire-lit-is-still-evening",
            "first-morning",
            "false-cabin",
            "walk-out-is-still-wrong",
            "coda",
            "stayed",
            "legacy-accepted-is-stayed",
            "legacy-refused-is-coda",
        ],
    )
    def test_phase_follows_the_flags(self, setup, expected):
        ws = WorldState()
        setup(ws)
        assert ws.story_phase() == expected

    def test_phase_is_not_persisted(self):
        assert "story_phase" not in WorldState().to_dict()


@pytest.mark.parametrize("legacy", [
    {"has_power": True, "fire_lit": True},
    {"first_morning": True, "fire_lit": True},
    {},
])
def test_legacy_evening_history_does_not_invent_a_cold_night(legacy):
    restored = WorldState.from_dict(legacy)
    assert restored.reopening_done == bool(legacy)
    assert restored.evening_meal == legacy.get("first_morning", False)
    assert restored.morning_started == legacy.get("first_morning", False)
    assert not restored.slept_cold
