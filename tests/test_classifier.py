"""Tests for the three-layer classification pipeline."""

import os
import tempfile

import pytest

from lib.config import DEFAULT_CONFIG
from lib.session import SessionState


def make_config(**overrides):
    """Return a copy of DEFAULT_CONFIG with llm_fallback=False and optional overrides."""
    import copy
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg["llm_fallback"] = False
    for k, v in overrides.items():
        cfg[k] = v
    return cfg


def make_session(tmpdir):
    return SessionState(state_dir=tmpdir, timeout_minutes=30)


# ---------------------------------------------------------------------------
# Layer 1 – rule-based classification
# ---------------------------------------------------------------------------

class TestRuleClassification:
    def test_simple_question_classifies_haiku(self, tmp_path):
        from lib.classifier import classify
        cfg = make_config()
        session = make_session(str(tmp_path))
        result = classify("what is a closure?", cfg, session)
        assert result["tier"] == "haiku"
        assert result["source"] == "rules"
        assert result["confidence"] >= 0.7

    def test_test_writing_classifies_sonnet(self, tmp_path):
        from lib.classifier import classify
        cfg = make_config()
        session = make_session(str(tmp_path))
        result = classify("write a test for the login function", cfg, session)
        assert result["tier"] == "sonnet"
        assert result["source"] == "rules"

    def test_architecture_classifies_opus(self, tmp_path):
        from lib.classifier import classify
        cfg = make_config()
        session = make_session(str(tmp_path))
        result = classify("design the architecture for a distributed system", cfg, session)
        assert result["tier"] == "opus"
        assert result["source"] == "rules"

    def test_no_match_defaults_to_sonnet(self, tmp_path):
        from lib.classifier import classify
        cfg = make_config()
        session = make_session(str(tmp_path))
        # A vague prompt that won't match any pattern
        result = classify("blorp zorp flibble", cfg, session)
        assert result["tier"] == "sonnet"
        assert result["source"] == "default"


# ---------------------------------------------------------------------------
# Layer 2 – context / momentum
# ---------------------------------------------------------------------------

class TestMomentum:
    def test_follow_up_inherits_opus_momentum(self, tmp_path):
        from lib.classifier import classify
        cfg = make_config()
        session = make_session(str(tmp_path))
        # Seed opus momentum: record 3 opus turns
        session.record_routing("opus", "auto")
        session.record_routing("opus", "auto")
        session.record_routing("opus", "auto")
        # Short follow-up with no strong signal — should inherit opus
        result = classify("and the networking?", cfg, session)
        assert result["tier"] == "opus"
        assert result["source"] == "context"

    def test_strong_signal_overrides_haiku_momentum(self, tmp_path):
        from lib.classifier import classify
        cfg = make_config()
        session = make_session(str(tmp_path))
        # Seed haiku momentum
        session.record_routing("haiku", "auto")
        session.record_routing("haiku", "auto")
        session.record_routing("haiku", "auto")
        # Architecture prompt has a strong opus signal — must win
        result = classify("design the architecture for the entire codebase", cfg, session)
        assert result["tier"] == "opus"
        # source should be rules, not context
        assert result["source"] == "rules"


# ---------------------------------------------------------------------------
# Word-count guards
# ---------------------------------------------------------------------------

class TestWordCountGuards:
    def test_exceeds_max_word_count_not_haiku(self, tmp_path):
        from lib.classifier import classify
        cfg = make_config()
        session = make_session(str(tmp_path))
        # Build a prompt that starts with "what is " (haiku pattern) but is > 80 words
        long_prompt = "what is " + " ".join(["something"] * 80)
        result = classify(long_prompt, cfg, session)
        # Must NOT classify as haiku because word count > 80
        assert result["tier"] != "haiku"

    def test_force_min_word_count_opus(self, tmp_path):
        from lib.classifier import classify
        cfg = make_config()
        session = make_session(str(tmp_path))
        # DEFAULT_CONFIG opus force_min_word_count = 250; build a 260-word prompt
        long_prompt = " ".join(["word"] * 260)
        result = classify(long_prompt, cfg, session)
        assert result["tier"] == "opus"
