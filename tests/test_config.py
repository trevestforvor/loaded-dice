"""Tests for lib/config.py — TDD first pass."""
import json
import os
import tempfile

import pytest

from lib.config import DEFAULT_CONFIG, load_config, merge_configs


class TestDefaultConfig:
    def test_has_session_model(self):
        assert DEFAULT_CONFIG["session_model"] == "auto"

    def test_has_prompt_mode(self):
        assert DEFAULT_CONFIG["prompt_mode"] == "suggest"

    def test_has_confidence_threshold(self):
        assert DEFAULT_CONFIG["confidence_threshold"] == 0.7

    def test_has_default_tier(self):
        assert DEFAULT_CONFIG["default_tier"] == "sonnet"

    def test_has_bypass_prefix(self):
        assert DEFAULT_CONFIG["bypass_prefix"] == "~"

    def test_has_session_timeout(self):
        assert DEFAULT_CONFIG["session_timeout_minutes"] == 30

    def test_has_momentum_decay(self):
        assert DEFAULT_CONFIG["momentum_decay_after"] == 3

    def test_has_suggest_switch(self):
        assert DEFAULT_CONFIG["suggest_switch_after"] == 3

    def test_has_llm_fallback(self):
        assert DEFAULT_CONFIG["llm_fallback"] is True

    def test_has_analytics(self):
        assert DEFAULT_CONFIG["analytics"] is True

    def test_has_tiers(self):
        assert "tiers" in DEFAULT_CONFIG
        assert "haiku" in DEFAULT_CONFIG["tiers"]
        assert "sonnet" in DEFAULT_CONFIG["tiers"]
        assert "opus" in DEFAULT_CONFIG["tiers"]

    def test_tier_mode_extend(self):
        for tier in ("haiku", "sonnet", "opus"):
            assert DEFAULT_CONFIG["tiers"][tier]["mode"] == "extend"

    def test_tier_empty_keyword_lists(self):
        for tier in ("haiku", "sonnet", "opus"):
            t = DEFAULT_CONFIG["tiers"][tier]
            assert t["keywords"] == []
            assert t["patterns"] == []
            assert t["remove_keywords"] == []
            assert t["remove_patterns"] == []

    def test_haiku_max_word_count(self):
        assert DEFAULT_CONFIG["tiers"]["haiku"]["max_word_count"] == 80

    def test_opus_force_min_word_count(self):
        assert DEFAULT_CONFIG["tiers"]["opus"]["force_min_word_count"] == 250


class TestLoadConfig:
    def test_returns_defaults_when_no_files(self):
        cfg = load_config(None, None)
        assert cfg["session_model"] == DEFAULT_CONFIG["session_model"]
        assert cfg["tiers"]["haiku"]["max_word_count"] == 80

    def test_returns_defaults_for_missing_paths(self):
        cfg = load_config("/nonexistent/global.yaml", "/nonexistent/project.yaml")
        assert cfg["session_model"] == DEFAULT_CONFIG["session_model"]

    def test_global_overrides_defaults(self):
        data = {"session_model": "opus", "confidence_threshold": 0.9}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            cfg = load_config(f.name, None)
        os.unlink(f.name)
        assert cfg["session_model"] == "opus"
        assert cfg["confidence_threshold"] == 0.9
        # defaults preserved
        assert cfg["default_tier"] == "sonnet"

    def test_project_overrides_global(self):
        global_data = {"session_model": "haiku", "analytics": False}
        project_data = {"session_model": "opus"}
        with (
            tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as gf,
            tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as pf,
        ):
            json.dump(global_data, gf)
            json.dump(project_data, pf)
            gf.flush()
            pf.flush()
            cfg = load_config(gf.name, pf.name)
        os.unlink(gf.name)
        os.unlink(pf.name)
        assert cfg["session_model"] == "opus"
        # global value preserved where not overridden by project
        assert cfg["analytics"] is False


class TestMergeConfigs:
    def test_scalar_override(self):
        base = {"a": 1, "b": 2}
        override = {"b": 99}
        result = merge_configs(base, override)
        assert result["a"] == 1
        assert result["b"] == 99

    def test_tier_extend_merges_keywords(self):
        base = {
            "tiers": {
                "haiku": {
                    "mode": "extend",
                    "keywords": ["short", "quick"],
                    "patterns": [],
                    "remove_keywords": [],
                    "remove_patterns": [],
                    "max_word_count": 80,
                }
            }
        }
        override = {
            "tiers": {
                "haiku": {
                    "mode": "extend",
                    "keywords": ["tiny"],
                    "patterns": [],
                    "remove_keywords": [],
                    "remove_patterns": [],
                }
            }
        }
        result = merge_configs(base, override)
        kw = result["tiers"]["haiku"]["keywords"]
        assert "short" in kw
        assert "quick" in kw
        assert "tiny" in kw

    def test_tier_extend_union_no_duplicates(self):
        base = {"tiers": {"haiku": {"mode": "extend", "keywords": ["a", "b"], "patterns": [], "remove_keywords": [], "remove_patterns": []}}}
        override = {"tiers": {"haiku": {"mode": "extend", "keywords": ["b", "c"], "patterns": [], "remove_keywords": [], "remove_patterns": []}}}
        result = merge_configs(base, override)
        kw = result["tiers"]["haiku"]["keywords"]
        assert kw.count("b") == 1

    def test_tier_replace_overwrites(self):
        base = {
            "tiers": {
                "sonnet": {
                    "mode": "extend",
                    "keywords": ["standard", "normal"],
                    "patterns": [],
                    "remove_keywords": [],
                    "remove_patterns": [],
                }
            }
        }
        override = {
            "tiers": {
                "sonnet": {
                    "mode": "replace",
                    "keywords": ["only-this"],
                    "patterns": [],
                    "remove_keywords": [],
                    "remove_patterns": [],
                }
            }
        }
        result = merge_configs(base, override)
        kw = result["tiers"]["sonnet"]["keywords"]
        assert kw == ["only-this"]
        assert "standard" not in kw

    def test_remove_keywords_subtracts(self):
        base = {
            "tiers": {
                "opus": {
                    "mode": "extend",
                    "keywords": ["arch", "complex", "design"],
                    "patterns": [],
                    "remove_keywords": [],
                    "remove_patterns": [],
                    "force_min_word_count": 250,
                }
            }
        }
        override = {
            "tiers": {
                "opus": {
                    "mode": "extend",
                    "keywords": [],
                    "patterns": [],
                    "remove_keywords": ["complex"],
                    "remove_patterns": [],
                }
            }
        }
        result = merge_configs(base, override)
        kw = result["tiers"]["opus"]["keywords"]
        assert "complex" not in kw
        assert "arch" in kw
        assert "design" in kw
