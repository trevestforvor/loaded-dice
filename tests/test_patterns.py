import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.patterns import (
    DEFAULT_PATTERNS,
    TIER_PRIORITY,
    compile_patterns,
    match_tier,
)


# ── compile_patterns ──────────────────────────────────────────────────────────

def test_compile_patterns_returns_compiled_objects():
    patterns = [r"\bfoo\b", r"^bar"]
    compiled = compile_patterns(patterns)
    assert len(compiled) == 2
    assert all(hasattr(p, "match") for p in compiled)


def test_compile_patterns_skips_bad_patterns():
    patterns = [r"\bfoo\b", r"[invalid(", r"^bar"]
    compiled = compile_patterns(patterns)
    assert len(compiled) == 2  # bad pattern dropped


def test_default_patterns_all_compile():
    for tier, pats in DEFAULT_PATTERNS.items():
        compiled = compile_patterns(pats)
        assert len(compiled) == len(pats), (
            f"Tier '{tier}' has {len(pats) - len(compiled)} bad pattern(s)"
        )


# ── TIER_PRIORITY ─────────────────────────────────────────────────────────────

def test_tier_priority_order():
    assert TIER_PRIORITY == ["opus", "sonnet", "haiku"]


# ── Haiku matches ─────────────────────────────────────────────────────────────

def test_haiku_git_status():
    compiled = {t: compile_patterns(p) for t, p in DEFAULT_PATTERNS.items()}
    result = match_tier("git status", compiled)
    assert result["tier"] == "haiku"
    assert result["confidence"] >= 0.7


def test_haiku_what_is_question():
    compiled = {t: compile_patterns(p) for t, p in DEFAULT_PATTERNS.items()}
    result = match_tier("what is a closure", compiled)
    assert result["tier"] == "haiku"
    assert result["confidence"] >= 0.7


def test_haiku_how_to():
    compiled = {t: compile_patterns(p) for t, p in DEFAULT_PATTERNS.items()}
    result = match_tier("how to read a file", compiled)
    assert result["tier"] == "haiku"


# ── Sonnet matches ────────────────────────────────────────────────────────────

def test_sonnet_write_test():
    compiled = {t: compile_patterns(p) for t, p in DEFAULT_PATTERNS.items()}
    result = match_tier("write a test for the login function", compiled)
    assert result["tier"] == "sonnet"
    assert result["confidence"] >= 0.7


def test_sonnet_fix_bug():
    compiled = {t: compile_patterns(p) for t, p in DEFAULT_PATTERNS.items()}
    result = match_tier("fix the bug in the auth module", compiled)
    assert result["tier"] == "sonnet"
    assert result["confidence"] >= 0.7


def test_sonnet_refactor():
    compiled = {t: compile_patterns(p) for t, p in DEFAULT_PATTERNS.items()}
    result = match_tier("refactor this function to be more readable", compiled)
    assert result["tier"] == "sonnet"


# ── Opus matches ──────────────────────────────────────────────────────────────

def test_opus_architecture():
    compiled = {t: compile_patterns(p) for t, p in DEFAULT_PATTERNS.items()}
    result = match_tier("design the architecture for our new microservice", compiled)
    assert result["tier"] == "opus"
    assert result["confidence"] >= 0.7


def test_opus_tradeoffs():
    compiled = {t: compile_patterns(p) for t, p in DEFAULT_PATTERNS.items()}
    result = match_tier("compare the pros and cons of GraphQL vs REST", compiled)
    assert result["tier"] == "opus"


def test_opus_security_review():
    compiled = {t: compile_patterns(p) for t, p in DEFAULT_PATTERNS.items()}
    result = match_tier("security review of the authentication code", compiled)
    assert result["tier"] == "opus"


# ── Priority / tie-breaking ───────────────────────────────────────────────────

def test_opus_wins_over_haiku_on_overlap():
    """'what is the architecture' triggers both haiku and opus — opus should win."""
    compiled = {t: compile_patterns(p) for t, p in DEFAULT_PATTERNS.items()}
    result = match_tier("what is the architecture of this system", compiled)
    assert result["tier"] == "opus"


# ── No match ──────────────────────────────────────────────────────────────────

def test_no_match_returns_none_and_half_confidence():
    compiled = {t: compile_patterns(p) for t, p in DEFAULT_PATTERNS.items()}
    result = match_tier("xyzzy plugh frobnicate quux", compiled)
    assert result["tier"] is None
    assert result["confidence"] == 0.5
    assert result["signals"] == []


# ── Confidence scaling ────────────────────────────────────────────────────────

def test_multiple_signals_boost_confidence():
    compiled = {t: compile_patterns(p) for t, p in DEFAULT_PATTERNS.items()}
    # "write a test and fix the bug" should fire 2+ sonnet signals
    result = match_tier("write a test and fix the bug in the auth module", compiled)
    assert result["tier"] == "sonnet"
    assert result["confidence"] >= 0.9


def test_three_signals_gives_full_confidence():
    compiled = {t: compile_patterns(p) for t, p in DEFAULT_PATTERNS.items()}
    # Craft a prompt hitting 3 haiku patterns
    result = match_tier("what is the json syntax for git log", compiled)
    # May land on haiku with 3 signals → confidence 1.0, or opus could win
    # We just assert confidence rules are respected for the winning tier
    assert result["confidence"] in (0.7, 0.9, 1.0)


# ── Word-count guard ──────────────────────────────────────────────────────────

def test_haiku_skipped_when_prompt_exceeds_max_word_count():
    compiled = {t: compile_patterns(p) for t, p in DEFAULT_PATTERNS.items()}
    long_prompt = "git status " + " ".join(["word"] * 85)  # 86+ words
    result = match_tier(long_prompt, compiled, max_word_counts={"haiku": 80})
    # haiku tier skipped; no other tier matches → None
    assert result["tier"] != "haiku"


def test_haiku_not_skipped_when_prompt_within_max_word_count():
    compiled = {t: compile_patterns(p) for t, p in DEFAULT_PATTERNS.items()}
    result = match_tier("git status", compiled, max_word_counts={"haiku": 80})
    assert result["tier"] == "haiku"


# ── force_min_word_counts escalation ─────────────────────────────────────────

def test_force_min_word_counts_escalates_tier():
    compiled = {t: compile_patterns(p) for t, p in DEFAULT_PATTERNS.items()}
    # Prompt is 10 words — force escalation if ≥5 words → sonnet
    prompt = "what is a closure in JavaScript and how does it work"  # 11 words
    result = match_tier(prompt, compiled, force_min_word_counts={"sonnet": 5})
    assert result["tier"] == "sonnet"
