"""Config loading for loaded-dice Claude Code plugin.

Loads defaults <- global <- project with deep merge and tier extend/replace/remove logic.
"""
import copy
import json
import os
from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "session_model": "auto",
    "prompt_mode": "suggest",
    "confidence_threshold": 0.7,
    "default_tier": "sonnet",
    "bypass_prefix": "~",
    "session_timeout_minutes": 30,
    "momentum_decay_after": 3,
    "suggest_switch_after": 3,
    "llm_fallback": True,
    "analytics": True,
    "tiers": {
        "haiku": {
            "mode": "extend",
            "keywords": [],
            "patterns": [],
            "remove_keywords": [],
            "remove_patterns": [],
            "max_word_count": 80,
        },
        "sonnet": {
            "mode": "extend",
            "keywords": [],
            "patterns": [],
            "remove_keywords": [],
            "remove_patterns": [],
        },
        "opus": {
            "mode": "extend",
            "keywords": [],
            "patterns": [],
            "remove_keywords": [],
            "remove_patterns": [],
            "force_min_word_count": 250,
        },
    },
}


def _load_file(path: str | None) -> dict[str, Any]:
    """Load a JSON/YAML config file, returning empty dict if missing or None."""
    if not path or not os.path.exists(path):
        return {}
    with open(path) as f:
        content = f.read().strip()
    if not content:
        return {}
    # Try JSON first; fall back to yaml if available
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore
            return yaml.safe_load(content) or {}
        except ImportError:
            raise ValueError(f"Config file {path} is not valid JSON and PyYAML is not installed")


def merge_configs(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge override onto base with tier extend/replace/remove logic."""
    result = copy.deepcopy(base)

    for key, val in override.items():
        if key == "tiers" and isinstance(val, dict):
            result_tiers = result.setdefault("tiers", {})
            for tier_name, tier_override in val.items():
                if tier_name not in result_tiers:
                    result_tiers[tier_name] = copy.deepcopy(tier_override)
                    continue

                base_tier = result_tiers[tier_name]
                mode = tier_override.get("mode", base_tier.get("mode", "extend"))

                if mode == "replace":
                    result_tiers[tier_name] = copy.deepcopy(tier_override)
                else:
                    # extend: union keyword/pattern lists, then subtract removes
                    merged_tier = copy.deepcopy(base_tier)
                    merged_tier["mode"] = mode

                    for list_key in ("keywords", "patterns"):
                        base_list = base_tier.get(list_key, [])
                        override_list = tier_override.get(list_key, [])
                        # Union preserving order, deduplicating
                        seen = dict.fromkeys(base_list)
                        for item in override_list:
                            seen.setdefault(item, None)
                        merged_tier[list_key] = list(seen)

                    # Apply removals
                    remove_kw = tier_override.get("remove_keywords", [])
                    remove_pat = tier_override.get("remove_patterns", [])
                    merged_tier["keywords"] = [k for k in merged_tier["keywords"] if k not in remove_kw]
                    merged_tier["patterns"] = [p for p in merged_tier["patterns"] if p not in remove_pat]
                    merged_tier["remove_keywords"] = []
                    merged_tier["remove_patterns"] = []

                    # Scalar overrides from tier_override (skip list/remove keys already handled)
                    skip = {"mode", "keywords", "patterns", "remove_keywords", "remove_patterns"}
                    for k, v in tier_override.items():
                        if k not in skip:
                            merged_tier[k] = v

                    result_tiers[tier_name] = merged_tier
        elif isinstance(val, dict) and isinstance(result.get(key), dict):
            result[key] = merge_configs(result[key], val)
        else:
            result[key] = val

    return result


def load_config(global_path: str | None, project_path: str | None) -> dict[str, Any]:
    """Load and merge: defaults <- global <- project."""
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    global_data = _load_file(global_path)
    if global_data:
        cfg = merge_configs(cfg, global_data)
    project_data = _load_file(project_path)
    if project_data:
        cfg = merge_configs(cfg, project_data)
    return cfg
