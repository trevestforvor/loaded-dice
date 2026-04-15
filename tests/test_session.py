"""Tests for SessionState — TDD pass written before implementation."""

import json
import time
import tempfile
import os
import pytest

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.session import SessionState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_session(**kwargs):
    """Create a SessionState backed by a fresh temp directory."""
    d = tempfile.mkdtemp()
    return SessionState(state_dir=d, **kwargs), d


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

class TestDefaults:
    def test_new_session_defaults(self):
        s, _ = make_session()
        assert s.conversation_depth == 0
        assert s.consecutive_off_tier == 0
        assert s.drift_tier is None
        assert s.drift_suggested is False
        assert s.tier_history == []
        assert isinstance(s.last_updated, float)
        assert isinstance(s.session_start, float)


# ---------------------------------------------------------------------------
# record_routing
# ---------------------------------------------------------------------------

class TestRecordRouting:
    def test_increments_depth_and_history(self):
        s, _ = make_session()
        s.record_routing("haiku", "haiku")
        assert s.conversation_depth == 1
        assert s.tier_history == ["haiku"]

    def test_multiple_records(self):
        s, _ = make_session()
        s.record_routing("haiku", "sonnet")
        s.record_routing("sonnet", "sonnet")
        assert s.conversation_depth == 2
        assert s.tier_history == ["haiku", "sonnet"]

    def test_consecutive_off_tier_increments_on_mismatch(self):
        s, _ = make_session()
        s.record_routing("opus", "haiku")   # tier != session_model
        assert s.consecutive_off_tier == 1
        assert s.drift_tier == "opus"

    def test_consecutive_off_tier_resets_on_match(self):
        s, _ = make_session()
        s.record_routing("opus", "haiku")
        s.record_routing("opus", "haiku")
        assert s.consecutive_off_tier == 2
        s.record_routing("haiku", "haiku")  # matches session_model
        assert s.consecutive_off_tier == 0
        assert s.drift_tier is None

    def test_drift_direction_change_resets_counter(self):
        s, _ = make_session()
        s.record_routing("opus", "haiku")   # drift toward opus, counter=1
        s.record_routing("opus", "haiku")   # same drift direction, counter=2
        s.record_routing("sonnet", "haiku") # different off-tier tier → reset to 1
        assert s.consecutive_off_tier == 1
        assert s.drift_tier == "sonnet"


# ---------------------------------------------------------------------------
# should_suggest_switch / mark_drift_suggested
# ---------------------------------------------------------------------------

class TestDriftSuggestion:
    def test_fires_at_threshold(self):
        s, _ = make_session()
        for _ in range(3):
            s.record_routing("opus", "haiku")
        assert s.should_suggest_switch(threshold=3) is True

    def test_does_not_fire_below_threshold(self):
        s, _ = make_session()
        for _ in range(2):
            s.record_routing("opus", "haiku")
        assert s.should_suggest_switch(threshold=3) is False

    def test_mark_drift_suggested_prevents_repeat(self):
        s, _ = make_session()
        for _ in range(3):
            s.record_routing("opus", "haiku")
        assert s.should_suggest_switch(threshold=3) is True
        s.mark_drift_suggested()
        assert s.should_suggest_switch(threshold=3) is False


# ---------------------------------------------------------------------------
# get_momentum_tier
# ---------------------------------------------------------------------------

class TestMomentumTier:
    def test_returns_tier_when_consistent(self):
        s, _ = make_session()
        for _ in range(3):
            s.record_routing("sonnet", "sonnet")
        assert s.get_momentum_tier(window=3) == "sonnet"

    def test_returns_none_when_mixed(self):
        s, _ = make_session()
        s.record_routing("haiku", "haiku")
        s.record_routing("sonnet", "sonnet")
        s.record_routing("haiku", "haiku")
        assert s.get_momentum_tier(window=3) is None

    def test_returns_none_when_insufficient_history(self):
        s, _ = make_session()
        s.record_routing("haiku", "haiku")
        assert s.get_momentum_tier(window=3) is None

    def test_uses_last_n_entries(self):
        s, _ = make_session()
        s.record_routing("opus", "opus")
        for _ in range(3):
            s.record_routing("haiku", "haiku")
        # Last 3 are all haiku — window=3 should return haiku
        assert s.get_momentum_tier(window=3) == "haiku"


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_save_and_reload(self):
        d = tempfile.mkdtemp()
        s = SessionState(state_dir=d)
        s.record_routing("opus", "haiku")
        s.record_routing("opus", "haiku")
        s.save()

        s2 = SessionState(state_dir=d)
        assert s2.conversation_depth == 2
        assert s2.tier_history == ["opus", "opus"]
        assert s2.consecutive_off_tier == 2
        assert s2.drift_tier == "opus"

    def test_expired_session_resets(self):
        d = tempfile.mkdtemp()
        s = SessionState(state_dir=d)
        s.record_routing("opus", "haiku")
        s.save()

        # timeout_minutes=0 means any elapsed time is "expired"
        s2 = SessionState(state_dir=d, timeout_minutes=0)
        assert s2.conversation_depth == 0
        assert s2.tier_history == []

    def test_tier_history_capped_at_50_on_save(self):
        d = tempfile.mkdtemp()
        s = SessionState(state_dir=d)
        for _ in range(60):
            s.record_routing("haiku", "haiku")
        s.save()

        s2 = SessionState(state_dir=d)
        assert len(s2.tier_history) == 50


# ---------------------------------------------------------------------------
# is_follow_up
# ---------------------------------------------------------------------------

class TestIsFollowUp:
    @pytest.mark.parametrize("prompt", [
        "and what else?",
        "also, can you explain",
        "what about the second part",
        "actually never mind",
        "wait, that's wrong",
        "yes please",
        "ok sounds good",
        "how about next week",
        "then what happened",
    ])
    def test_detects_follow_up_patterns(self, prompt):
        s, _ = make_session()
        assert s.is_follow_up(prompt) is True

    def test_rejects_long_prompt(self):
        s, _ = make_session()
        # 8 words — starts with follow-up pattern but is too long
        prompt = "and what about this other thing entirely though"
        assert s.is_follow_up(prompt) is False

    def test_rejects_non_follow_up(self):
        s, _ = make_session()
        assert s.is_follow_up("Write me a Python class for sorting") is False

    def test_short_prompt_no_pattern(self):
        s, _ = make_session()
        assert s.is_follow_up("explain monads") is False
