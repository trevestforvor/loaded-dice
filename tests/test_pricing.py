"""Tests for pricing module — tier weights and savings calculations."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.pricing import TIER_WEIGHTS, tier_weight, classify_direction, compute_savings


class TestTierWeights:
    def test_haiku_weight_is_1(self):
        assert TIER_WEIGHTS["haiku"] == 1

    def test_sonnet_weight_is_3(self):
        assert TIER_WEIGHTS["sonnet"] == 3

    def test_opus_weight_is_5(self):
        assert TIER_WEIGHTS["opus"] == 5

    def test_tier_weight_lookup(self):
        assert tier_weight("haiku") == 1
        assert tier_weight("sonnet") == 3
        assert tier_weight("opus") == 5

    def test_tier_weight_unknown_returns_none(self):
        assert tier_weight("unknown") is None


class TestClassifyDirection:
    def test_opus_to_haiku_is_downward(self):
        assert classify_direction("opus", "haiku") == "downward"

    def test_opus_to_sonnet_is_downward(self):
        assert classify_direction("opus", "sonnet") == "downward"

    def test_sonnet_to_haiku_is_downward(self):
        assert classify_direction("sonnet", "haiku") == "downward"

    def test_haiku_to_sonnet_is_upward(self):
        assert classify_direction("haiku", "sonnet") == "upward"

    def test_haiku_to_opus_is_upward(self):
        assert classify_direction("haiku", "opus") == "upward"

    def test_sonnet_to_opus_is_upward(self):
        assert classify_direction("sonnet", "opus") == "upward"

    def test_same_tier_is_none(self):
        assert classify_direction("opus", "opus") is None
        assert classify_direction("sonnet", "sonnet") is None
        assert classify_direction("haiku", "haiku") is None


class TestComputeSavings:
    def test_all_downward_opus_to_haiku(self):
        events = [
            {"tier": "haiku", "session_model": "opus", "word_count": 100},
            {"tier": "haiku", "session_model": "opus", "word_count": 100},
        ]
        result = compute_savings(events)
        assert result["overall_savings_pct"] == 80.0
        assert len(result["downward"]) == 1
        d = result["downward"][0]
        assert d["direction"] == "Opus -> Haiku"
        assert d["prompts"] == 2
        assert d["words"] == 200
        assert d["savings_pct"] == 80.0

    def test_all_downward_opus_to_sonnet(self):
        events = [
            {"tier": "sonnet", "session_model": "opus", "word_count": 50},
        ]
        result = compute_savings(events)
        assert result["overall_savings_pct"] == 40.0
        assert result["downward"][0]["savings_pct"] == 40.0

    def test_all_downward_sonnet_to_haiku(self):
        events = [
            {"tier": "haiku", "session_model": "sonnet", "word_count": 90},
        ]
        result = compute_savings(events)
        assert abs(result["overall_savings_pct"] - 66.7) < 0.1

    def test_upward_routing_tracked_separately(self):
        events = [
            {"tier": "opus", "session_model": "haiku", "word_count": 200},
            {"tier": "sonnet", "session_model": "haiku", "word_count": 100},
        ]
        result = compute_savings(events)
        assert len(result["downward"]) == 0
        assert len(result["complexity_matches"]) == 2

    def test_mixed_directions(self):
        events = [
            {"tier": "haiku", "session_model": "opus", "word_count": 100},
            {"tier": "haiku", "session_model": "opus", "word_count": 100},
            {"tier": "haiku", "session_model": "opus", "word_count": 100},
            {"tier": "opus", "session_model": "haiku", "word_count": 100},
        ]
        result = compute_savings(events)
        assert result["overall_savings_pct"] == 50.0
        assert len(result["downward"]) == 1
        assert len(result["complexity_matches"]) == 1

    def test_same_tier_excluded_from_direction_buckets(self):
        events = [
            {"tier": "opus", "session_model": "opus", "word_count": 100},
            {"tier": "haiku", "session_model": "opus", "word_count": 50},
        ]
        result = compute_savings(events)
        assert len(result["downward"]) == 1
        assert len(result["complexity_matches"]) == 0
        assert abs(result["overall_savings_pct"] - 26.7) < 0.1

    def test_no_events_returns_zero(self):
        result = compute_savings([])
        assert result["overall_savings_pct"] == 0.0
        assert result["downward"] == []
        assert result["complexity_matches"] == []

    def test_negative_savings_when_upward_dominates(self):
        """When upward routing dominates, overall savings is negative."""
        events = [
            {"tier": "opus", "session_model": "haiku", "word_count": 100},
            {"tier": "opus", "session_model": "haiku", "word_count": 100},
        ]
        result = compute_savings(events)
        # baseline: 2 * 1 * 100 = 200, actual: 2 * 5 * 100 = 1000
        # savings: (1 - 1000/200) * 100 = -400.0%
        assert result["overall_savings_pct"] == -400.0
        assert len(result["downward"]) == 0
        assert len(result["complexity_matches"]) == 1

    def test_events_missing_word_count_skipped(self):
        events = [
            {"tier": "haiku", "session_model": "opus"},
            {"tier": "haiku", "session_model": "opus", "word_count": 100},
        ]
        result = compute_savings(events)
        assert result["downward"][0]["prompts"] == 1
        assert result["downward"][0]["words"] == 100
