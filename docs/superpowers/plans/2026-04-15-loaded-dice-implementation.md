# Loaded Dice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude Code plugin that classifies prompts and subagent dispatches by complexity, delegating to the right model tier automatically.

**Architecture:** Python-based hook system with a shared classifier library. Two hooks (UserPromptSubmit + PreToolUse) call the same classification engine. Session state persisted as JSON. Config supports global + project-level overrides.

**Tech Stack:** Python 3, regex, JSON, optional `anthropic` pip package for LLM fallback

---

## File Map

| File | Responsibility |
|------|---------------|
| `.claude-plugin/plugin.json` | Plugin manifest — metadata, skill refs, hook refs |
| `.claude-plugin/hooks/hooks.json` | Hook registrations for Claude Code |
| `lib/patterns.py` | Default pattern tables per tier (haiku/sonnet/opus) |
| `lib/config.py` | Config loading — global + project merge, schema defaults |
| `lib/classifier.py` | Three-layer classification pipeline (rules → context → LLM) |
| `lib/session.py` | Session state read/write/expiry |
| `lib/analytics.py` | NDJSON log writing |
| `hooks/classify-prompt.py` | UserPromptSubmit hook entry point |
| `hooks/enforce-routing.py` | PreToolUse hook entry point (Agent matcher) |
| `hooks/track-session.py` | Stop hook — write session summary |
| `skills/dice-stats/SKILL.md` | /dice-stats slash command |
| `skills/dice-config/SKILL.md` | /dice-config slash command |
| `skills/dice-bypass/SKILL.md` | /dice-bypass slash command |
| `skills/dice-mode/SKILL.md` | /dice-mode slash command |
| `skills/dice-switch/SKILL.md` | /dice-switch slash command |
| `schema/loaded-dice.schema.json` | JSON Schema for config validation |
| `tests/test_patterns.py` | Unit tests for pattern matching |
| `tests/test_classifier.py` | Unit tests for classification pipeline |
| `tests/test_config.py` | Unit tests for config loading/merging |
| `tests/test_session.py` | Unit tests for session state |
| `tests/test_hooks.py` | Integration tests for hook stdin/stdout |
| `README.md` | Install/usage docs |
| `LICENSE` | MIT license |

---

### Task 1: Project Scaffolding and Plugin Manifest

**Files:**
- Create: `.claude-plugin/plugin.json`
- Create: `.claude-plugin/hooks/hooks.json`
- Create: `LICENSE`
- Create: `lib/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create the plugin manifest**

```json
// .claude-plugin/plugin.json
{
  "name": "loaded-dice",
  "version": "0.1.0",
  "description": "Intelligent model routing for Claude Code — classifies prompts and subagent dispatches by complexity, delegates to the right tier automatically",
  "author": {
    "name": "trevestforvor"
  },
  "homepage": "https://github.com/trevestforvor/loaded-dice",
  "repository": "https://github.com/trevestforvor/loaded-dice",
  "license": "MIT",
  "keywords": ["model-routing", "cost-optimization", "subagent", "haiku", "sonnet", "opus"],
  "skills": [
    "./skills/dice-stats/SKILL.md",
    "./skills/dice-config/SKILL.md",
    "./skills/dice-bypass/SKILL.md",
    "./skills/dice-mode/SKILL.md",
    "./skills/dice-switch/SKILL.md"
  ],
  "hooks": "./hooks/hooks.json"
}
```

- [ ] **Step 2: Create the hooks registration**

```json
// .claude-plugin/hooks/hooks.json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "type": "command",
        "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/classify-prompt.py\"",
        "timeout": 15
      }
    ],
    "PreToolUse": [
      {
        "type": "command",
        "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/enforce-routing.py\"",
        "timeout": 10,
        "matcher": "Agent"
      }
    ],
    "Stop": [
      {
        "type": "command",
        "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/track-session.py\"",
        "timeout": 5
      }
    ]
  }
}
```

- [ ] **Step 3: Create MIT LICENSE**

```
MIT License

Copyright (c) 2026 trevestforvor

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 4: Create empty __init__.py files**

```python
# lib/__init__.py
# Loaded Dice classification library

# tests/__init__.py
# Loaded Dice test suite
```

- [ ] **Step 5: Commit scaffolding**

```bash
git add .claude-plugin/ lib/__init__.py tests/__init__.py LICENSE
git commit -m "feat: scaffold plugin manifest, hooks registration, and license"
```

---

### Task 2: Default Pattern Tables

**Files:**
- Create: `lib/patterns.py`
- Create: `tests/test_patterns.py`

- [ ] **Step 1: Write the failing test for pattern compilation and matching**

```python
# tests/test_patterns.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.patterns import DEFAULT_PATTERNS, compile_patterns, match_tier


def test_patterns_compile_without_error():
    compiled = compile_patterns(DEFAULT_PATTERNS)
    assert "haiku" in compiled
    assert "sonnet" in compiled
    assert "opus" in compiled


def test_haiku_matches_git_status():
    compiled = compile_patterns(DEFAULT_PATTERNS)
    result = match_tier("git status", compiled)
    assert result["tier"] == "haiku"
    assert result["confidence"] >= 0.7


def test_haiku_matches_what_is_question():
    compiled = compile_patterns(DEFAULT_PATTERNS)
    result = match_tier("what is a guard statement?", compiled)
    assert result["tier"] == "haiku"


def test_sonnet_matches_test_writing():
    compiled = compile_patterns(DEFAULT_PATTERNS)
    result = match_tier("write tests for the LoginView", compiled)
    assert result["tier"] == "sonnet"


def test_sonnet_matches_bug_fix():
    compiled = compile_patterns(DEFAULT_PATTERNS)
    result = match_tier("fix the bug in the authentication error handler", compiled)
    assert result["tier"] == "sonnet"


def test_opus_matches_architecture():
    compiled = compile_patterns(DEFAULT_PATTERNS)
    result = match_tier("redesign the sync architecture across all modules", compiled)
    assert result["tier"] == "opus"


def test_opus_matches_tradeoff():
    compiled = compile_patterns(DEFAULT_PATTERNS)
    result = match_tier("compare the trade-offs between these approaches", compiled)
    assert result["tier"] == "opus"


def test_opus_wins_over_haiku_on_tie():
    """'what is the architecture' matches haiku (what is) and opus (architecture) — opus wins."""
    compiled = compile_patterns(DEFAULT_PATTERNS)
    result = match_tier("what is the architecture of this system?", compiled)
    assert result["tier"] == "opus"


def test_no_match_returns_default():
    compiled = compile_patterns(DEFAULT_PATTERNS)
    result = match_tier("hello", compiled)
    assert result["tier"] is None
    assert result["confidence"] == 0.5


def test_multiple_signals_boost_confidence():
    compiled = compile_patterns(DEFAULT_PATTERNS)
    result = match_tier("grep for all file usages and search the codebase", compiled)
    assert result["confidence"] >= 0.9


def test_word_count_guard():
    compiled = compile_patterns(DEFAULT_PATTERNS)
    long_prompt = "what is " + " ".join(["word"] * 100)
    result = match_tier(long_prompt, compiled, max_word_counts={"haiku": 80})
    assert result["tier"] != "haiku"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/trevest/loaded-dice && python3 -m pytest tests/test_patterns.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'lib.patterns'`

- [ ] **Step 3: Implement patterns.py**

```python
# lib/patterns.py
"""Default pattern tables and matching logic for Loaded Dice."""

import re
from typing import Any

DEFAULT_PATTERNS: dict[str, list[str]] = {
    "haiku": [
        r"^what (is|are|does) ",
        r"^how (do|does|to) ",
        r"^(show|list|get) .{0,30}$",
        r"\b(format|lint|prettify|beautify)\b",
        r"\bgit (status|log|diff|add|commit|push|pull)\b",
        r"\b(json|yaml|yml)\b.{0,20}$",
        r"\bregex\b",
        r"\bsyntax (for|of)\b",
        r"\b(grep|glob|search|find)\b.{0,30}(file|usage|instance)",
        r"\bread\b.{0,20}\b(file|contents?)\b",
        r"\bsummar(y|ize)\b.{0,20}\b(file|function|class)\b",
    ],
    "sonnet": [
        r"\b(write|add|create|implement)\b.{0,30}\b(test|spec)\b",
        r"\b(fix|debug)\b.{0,30}\b(bug|error|issue)\b",
        r"\brefactor\b.{0,30}(function|method|class|view)\b",
        r"\b(review|check)\b.{0,20}\b(code|function|method|PR)\b",
        r"\b(document|docstring|comment)\b",
        r"\b(build|implement|create)\b.{0,30}(component|view|screen|endpoint)",
        r"\bauditor?\b",
    ],
    "opus": [
        r"\b(architect|architecture|design pattern|system design)\b",
        r"\b(across|multiple|all) (files?|components?|modules?)\b",
        r"\brefactor.{0,20}(codebase|project|entire)\b",
        r"\b(trade-?off|compare|pros? (and|&) cons?)\b",
        r"\b(analyze|evaluate|assess).{0,30}(option|approach|strateg)",
        r"\boptimiz(e|ation).{0,20}(performance|speed|memory)\b",
        r"\b(plan|planning|roadmap)\b.{0,30}(implement|migration|phase)\b",
        r"\b(security|vulnerab|audit)\b.{0,20}(review|scan|check)\b",
        r"\b(debug|diagnos).{0,30}(race|deadlock|leak|crash)\b",
        r"\b(cross-?domain|end-?to-?end|full-?stack)\b",
    ],
}

# Priority order: opus first (highest stakes for misrouting down)
TIER_PRIORITY = ["opus", "sonnet", "haiku"]


def compile_patterns(
    patterns: dict[str, list[str]],
) -> dict[str, list[re.Pattern]]:
    """Compile pattern strings into regex objects."""
    compiled: dict[str, list[re.Pattern]] = {}
    for tier, pattern_list in patterns.items():
        compiled[tier] = []
        for p in pattern_list:
            try:
                compiled[tier].append(re.compile(p, re.IGNORECASE))
            except re.error:
                continue  # skip bad patterns from user config
    return compiled


def match_tier(
    prompt: str,
    compiled: dict[str, list[re.Pattern]],
    max_word_counts: dict[str, int] | None = None,
    force_min_word_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Match a prompt against compiled patterns. Returns {tier, confidence, signals}.

    Checks tiers in priority order (opus → sonnet → haiku).
    Higher tier wins on ties. Multiple signals boost confidence.
    """
    word_count = len(prompt.split())
    max_word_counts = max_word_counts or {}
    force_min_word_counts = force_min_word_counts or {}

    # Check force_min_word_count escalation first
    for tier in TIER_PRIORITY:
        threshold = force_min_word_counts.get(tier)
        if threshold and word_count >= threshold:
            return {
                "tier": tier,
                "confidence": 0.85,
                "signals": [f"word_count >= {threshold}"],
            }

    # Collect signals per tier
    tier_signals: dict[str, list[str]] = {t: [] for t in TIER_PRIORITY}

    for tier in TIER_PRIORITY:
        # Skip tier if prompt exceeds max_word_count
        max_wc = max_word_counts.get(tier)
        if max_wc and word_count > max_wc:
            continue

        for pattern in compiled.get(tier, []):
            if pattern.search(prompt):
                tier_signals[tier].append(pattern.pattern)

    # Find the highest-priority tier with signals
    best_tier = None
    best_signals: list[str] = []

    for tier in TIER_PRIORITY:
        if tier_signals[tier]:
            best_tier = tier
            best_signals = tier_signals[tier]
            break

    if best_tier is None:
        return {"tier": None, "confidence": 0.5, "signals": []}

    # Confidence based on signal count
    signal_count = len(best_signals)
    if signal_count >= 3:
        confidence = 1.0
    elif signal_count == 2:
        confidence = 0.9
    else:
        confidence = 0.7

    return {"tier": best_tier, "confidence": confidence, "signals": best_signals}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/trevest/loaded-dice && python3 -m pytest tests/test_patterns.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add lib/patterns.py tests/test_patterns.py
git commit -m "feat: add default pattern tables and tier matching logic"
```

---

### Task 3: Config Loading

**Files:**
- Create: `lib/config.py`
- Create: `schema/loaded-dice.schema.json`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing test for config loading**

```python
# tests/test_config.py
import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.config import load_config, merge_configs, DEFAULT_CONFIG


def test_default_config_has_required_fields():
    assert DEFAULT_CONFIG["session_model"] == "auto"
    assert DEFAULT_CONFIG["prompt_mode"] == "suggest"
    assert DEFAULT_CONFIG["confidence_threshold"] == 0.7
    assert DEFAULT_CONFIG["default_tier"] == "sonnet"
    assert DEFAULT_CONFIG["bypass_prefix"] == "~"
    assert DEFAULT_CONFIG["suggest_switch_after"] == 3
    assert DEFAULT_CONFIG["llm_fallback"] is True
    assert DEFAULT_CONFIG["analytics"] is True
    assert "haiku" in DEFAULT_CONFIG["tiers"]
    assert "sonnet" in DEFAULT_CONFIG["tiers"]
    assert "opus" in DEFAULT_CONFIG["tiers"]


def test_load_config_returns_defaults_when_no_file():
    config = load_config(global_path="/nonexistent/path.json", project_path=None)
    assert config == DEFAULT_CONFIG


def test_load_config_merges_global():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"prompt_mode": "instruct", "confidence_threshold": 0.8}, f)
        f.flush()
        config = load_config(global_path=f.name, project_path=None)
    os.unlink(f.name)
    assert config["prompt_mode"] == "instruct"
    assert config["confidence_threshold"] == 0.8
    assert config["session_model"] == "auto"  # unchanged default


def test_project_overrides_global():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as g:
        json.dump({"prompt_mode": "instruct"}, g)
        g.flush()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as p:
        json.dump({"prompt_mode": "suggest"}, p)
        p.flush()
    config = load_config(global_path=g.name, project_path=p.name)
    os.unlink(g.name)
    os.unlink(p.name)
    assert config["prompt_mode"] == "suggest"  # project wins


def test_tier_extend_mode():
    base = {"tiers": {"haiku": {"mode": "extend", "keywords": ["base_kw"]}}}
    override = {"tiers": {"haiku": {"mode": "extend", "keywords": ["new_kw"]}}}
    merged = merge_configs(base, override)
    assert "base_kw" in merged["tiers"]["haiku"]["keywords"]
    assert "new_kw" in merged["tiers"]["haiku"]["keywords"]


def test_tier_replace_mode():
    base = {"tiers": {"haiku": {"mode": "extend", "keywords": ["base_kw"]}}}
    override = {"tiers": {"haiku": {"mode": "replace", "keywords": ["only_kw"]}}}
    merged = merge_configs(base, override)
    assert merged["tiers"]["haiku"]["keywords"] == ["only_kw"]


def test_tier_remove_keywords():
    base = {"tiers": {"haiku": {"mode": "extend", "keywords": ["keep", "remove_me"]}}}
    override = {"tiers": {"haiku": {"mode": "extend", "remove_keywords": ["remove_me"]}}}
    merged = merge_configs(base, override)
    assert "keep" in merged["tiers"]["haiku"]["keywords"]
    assert "remove_me" not in merged["tiers"]["haiku"]["keywords"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/trevest/loaded-dice && python3 -m pytest tests/test_config.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement config.py**

```python
# lib/config.py
"""Config loading with global + project merge for Loaded Dice."""

import json
import os
import copy
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


def _read_json(path: str) -> dict[str, Any] | None:
    """Read a JSON file, return None if missing or invalid."""
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def merge_configs(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge override config on top of base. Handles tier extend/replace/remove."""
    result = copy.deepcopy(base)

    for key, value in override.items():
        if key == "tiers" and isinstance(value, dict):
            if "tiers" not in result:
                result["tiers"] = {}
            for tier_name, tier_override in value.items():
                if tier_name not in result["tiers"]:
                    result["tiers"][tier_name] = copy.deepcopy(tier_override)
                    continue

                base_tier = result["tiers"][tier_name]
                mode = tier_override.get("mode", "extend")

                if mode == "replace":
                    result["tiers"][tier_name] = copy.deepcopy(tier_override)
                else:
                    # Extend: merge lists, override scalars
                    for tk, tv in tier_override.items():
                        if tk in ("keywords", "patterns") and isinstance(tv, list):
                            existing = base_tier.get(tk, [])
                            base_tier[tk] = list(set(existing + tv))
                        elif tk in ("remove_keywords", "remove_patterns"):
                            continue  # handled below
                        else:
                            base_tier[tk] = tv

                    # Apply removals
                    for kw in tier_override.get("remove_keywords", []):
                        kws = base_tier.get("keywords", [])
                        if kw in kws:
                            kws.remove(kw)
                    for pat in tier_override.get("remove_patterns", []):
                        pats = base_tier.get("patterns", [])
                        if pat in pats:
                            pats.remove(pat)
        else:
            result[key] = value

    return result


def load_config(
    global_path: str = "~/.claude/loaded-dice.json",
    project_path: str | None = ".claude/loaded-dice.json",
) -> dict[str, Any]:
    """Load config: defaults ← global ← project."""
    result = copy.deepcopy(DEFAULT_CONFIG)

    global_path = os.path.expanduser(global_path)
    global_cfg = _read_json(global_path)
    if global_cfg:
        result = merge_configs(result, global_cfg)

    if project_path:
        project_cfg = _read_json(project_path)
        if project_cfg:
            result = merge_configs(result, project_cfg)

    return result
```

- [ ] **Step 4: Create JSON schema**

```json
// schema/loaded-dice.schema.json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Loaded Dice Configuration",
  "type": "object",
  "properties": {
    "session_model": {
      "type": "string",
      "enum": ["auto", "haiku", "sonnet", "opus"],
      "default": "auto"
    },
    "prompt_mode": {
      "type": "string",
      "enum": ["suggest", "instruct"],
      "default": "suggest"
    },
    "confidence_threshold": {
      "type": "number",
      "minimum": 0,
      "maximum": 1,
      "default": 0.7
    },
    "default_tier": {
      "type": "string",
      "enum": ["haiku", "sonnet", "opus"],
      "default": "sonnet"
    },
    "bypass_prefix": { "type": "string", "default": "~" },
    "session_timeout_minutes": { "type": "integer", "minimum": 1, "default": 30 },
    "momentum_decay_after": { "type": "integer", "minimum": 1, "default": 3 },
    "suggest_switch_after": { "type": "integer", "minimum": 1, "default": 3 },
    "llm_fallback": { "type": "boolean", "default": true },
    "analytics": { "type": "boolean", "default": true },
    "tiers": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "mode": { "type": "string", "enum": ["extend", "replace"] },
          "keywords": { "type": "array", "items": { "type": "string" } },
          "patterns": { "type": "array", "items": { "type": "string" } },
          "remove_keywords": { "type": "array", "items": { "type": "string" } },
          "remove_patterns": { "type": "array", "items": { "type": "string" } },
          "max_word_count": { "type": "integer", "minimum": 1 },
          "force_min_word_count": { "type": "integer", "minimum": 1 }
        }
      }
    }
  }
}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /Users/trevest/loaded-dice && python3 -m pytest tests/test_config.py -v
```

Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add lib/config.py schema/loaded-dice.schema.json tests/test_config.py
git commit -m "feat: add config loading with global/project merge and tier extend/replace"
```

---

### Task 4: Session State Management

**Files:**
- Create: `lib/session.py`
- Create: `tests/test_session.py`

- [ ] **Step 1: Write the failing test for session state**

```python
# tests/test_session.py
import sys
import os
import json
import time
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.session import SessionState


def test_new_session_has_defaults():
    with tempfile.TemporaryDirectory() as d:
        s = SessionState(state_dir=d, timeout_minutes=30)
        assert s.conversation_depth == 0
        assert s.consecutive_off_tier == 0
        assert s.drift_tier is None
        assert s.drift_suggested is False
        assert s.tier_history == []


def test_record_routing_updates_depth():
    with tempfile.TemporaryDirectory() as d:
        s = SessionState(state_dir=d, timeout_minutes=30)
        s.record_routing("haiku", session_model="opus")
        assert s.conversation_depth == 1
        assert s.tier_history == ["haiku"]


def test_consecutive_off_tier_increments():
    with tempfile.TemporaryDirectory() as d:
        s = SessionState(state_dir=d, timeout_minutes=30)
        s.record_routing("haiku", session_model="opus")
        s.record_routing("haiku", session_model="opus")
        s.record_routing("haiku", session_model="opus")
        assert s.consecutive_off_tier == 3
        assert s.drift_tier == "haiku"


def test_consecutive_off_tier_resets_on_match():
    with tempfile.TemporaryDirectory() as d:
        s = SessionState(state_dir=d, timeout_minutes=30)
        s.record_routing("haiku", session_model="opus")
        s.record_routing("haiku", session_model="opus")
        s.record_routing("opus", session_model="opus")
        assert s.consecutive_off_tier == 0
        assert s.drift_tier is None


def test_drift_direction_change_resets():
    with tempfile.TemporaryDirectory() as d:
        s = SessionState(state_dir=d, timeout_minutes=30)
        s.record_routing("haiku", session_model="opus")
        s.record_routing("haiku", session_model="opus")
        s.record_routing("sonnet", session_model="opus")  # direction change
        assert s.consecutive_off_tier == 1
        assert s.drift_tier == "sonnet"


def test_drift_suggested_flag():
    with tempfile.TemporaryDirectory() as d:
        s = SessionState(state_dir=d, timeout_minutes=30)
        assert not s.should_suggest_switch(threshold=3)
        s.record_routing("haiku", session_model="opus")
        s.record_routing("haiku", session_model="opus")
        s.record_routing("haiku", session_model="opus")
        assert s.should_suggest_switch(threshold=3)
        s.mark_drift_suggested()
        assert not s.should_suggest_switch(threshold=3)  # only fires once


def test_momentum_returns_recent_tier():
    with tempfile.TemporaryDirectory() as d:
        s = SessionState(state_dir=d, timeout_minutes=30)
        s.record_routing("opus", session_model="opus")
        s.record_routing("opus", session_model="opus")
        assert s.get_momentum_tier(window=3) == "opus"


def test_momentum_none_when_mixed():
    with tempfile.TemporaryDirectory() as d:
        s = SessionState(state_dir=d, timeout_minutes=30)
        s.record_routing("opus", session_model="opus")
        s.record_routing("haiku", session_model="opus")
        s.record_routing("sonnet", session_model="opus")
        assert s.get_momentum_tier(window=3) is None


def test_state_persists_to_disk():
    with tempfile.TemporaryDirectory() as d:
        s1 = SessionState(state_dir=d, timeout_minutes=30)
        s1.record_routing("haiku", session_model="opus")
        s1.save()

        s2 = SessionState(state_dir=d, timeout_minutes=30)
        assert s2.conversation_depth == 1
        assert s2.tier_history == ["haiku"]


def test_expired_session_resets():
    with tempfile.TemporaryDirectory() as d:
        s1 = SessionState(state_dir=d, timeout_minutes=0)  # 0 = always expired
        s1.record_routing("haiku", session_model="opus")
        s1.save()

        s2 = SessionState(state_dir=d, timeout_minutes=0)
        assert s2.conversation_depth == 0  # reset due to expiry


def test_is_follow_up():
    with tempfile.TemporaryDirectory() as d:
        s = SessionState(state_dir=d, timeout_minutes=30)
        assert s.is_follow_up("and the networking layer?")
        assert s.is_follow_up("also check the tests")
        assert s.is_follow_up("what about error handling?")
        assert not s.is_follow_up("redesign the architecture from scratch")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/trevest/loaded-dice && python3 -m pytest tests/test_session.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement session.py**

```python
# lib/session.py
"""Session state management for Loaded Dice."""

import json
import os
import re
import time
from typing import Any

FOLLOW_UP_PATTERNS = [
    re.compile(r"^and\b", re.IGNORECASE),
    re.compile(r"^also\b", re.IGNORECASE),
    re.compile(r"^what about\b", re.IGNORECASE),
    re.compile(r"^actually\b", re.IGNORECASE),
    re.compile(r"^wait\b", re.IGNORECASE),
    re.compile(r"^yes\b", re.IGNORECASE),
    re.compile(r"^ok\b", re.IGNORECASE),
    re.compile(r"^how about\b", re.IGNORECASE),
    re.compile(r"^then\b", re.IGNORECASE),
]


class SessionState:
    """Tracks routing history and tier momentum within a session."""

    def __init__(self, state_dir: str = "~/.claude/loaded-dice", timeout_minutes: int = 30):
        self.state_dir = os.path.expanduser(state_dir)
        self.state_file = os.path.join(self.state_dir, "session.json")
        self.timeout_minutes = timeout_minutes

        self.conversation_depth: int = 0
        self.consecutive_off_tier: int = 0
        self.drift_tier: str | None = None
        self.drift_suggested: bool = False
        self.tier_history: list[str] = []
        self.last_updated: float = time.time()
        self.session_start: float = time.time()

        self._load()

    def _load(self) -> None:
        """Load state from disk, reset if expired or missing."""
        if not os.path.isfile(self.state_file):
            return

        try:
            with open(self.state_file, "r") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return

        # Check expiry
        last = data.get("last_updated", 0)
        elapsed = (time.time() - last) / 60
        if elapsed > self.timeout_minutes:
            return  # expired — use fresh defaults

        self.conversation_depth = data.get("conversation_depth", 0)
        self.consecutive_off_tier = data.get("consecutive_off_tier", 0)
        self.drift_tier = data.get("drift_tier")
        self.drift_suggested = data.get("drift_suggested", False)
        self.tier_history = data.get("tier_history", [])
        self.last_updated = last
        self.session_start = data.get("session_start", time.time())

    def save(self) -> None:
        """Persist state to disk."""
        os.makedirs(self.state_dir, exist_ok=True)
        data = {
            "conversation_depth": self.conversation_depth,
            "consecutive_off_tier": self.consecutive_off_tier,
            "drift_tier": self.drift_tier,
            "drift_suggested": self.drift_suggested,
            "tier_history": self.tier_history[-50:],  # cap history
            "last_updated": time.time(),
            "session_start": self.session_start,
        }
        try:
            with open(self.state_file, "w") as f:
                json.dump(data, f)
        except OSError:
            pass  # non-fatal

    def record_routing(self, tier: str, session_model: str) -> None:
        """Record a routing decision and update drift tracking."""
        self.conversation_depth += 1
        self.tier_history.append(tier)

        if tier == session_model:
            self.consecutive_off_tier = 0
            self.drift_tier = None
            self.drift_suggested = False
        elif self.drift_tier == tier:
            self.consecutive_off_tier += 1
        else:
            # Direction changed
            self.consecutive_off_tier = 1
            self.drift_tier = tier
            self.drift_suggested = False

        self.last_updated = time.time()

    def should_suggest_switch(self, threshold: int = 3) -> bool:
        """Return True if drift threshold reached and not yet suggested."""
        return (
            self.consecutive_off_tier >= threshold
            and not self.drift_suggested
            and self.drift_tier is not None
        )

    def mark_drift_suggested(self) -> None:
        """Mark that a drift suggestion has been shown."""
        self.drift_suggested = True

    def get_momentum_tier(self, window: int = 3) -> str | None:
        """Return the tier if the last N entries are all the same, else None."""
        if len(self.tier_history) < 2:
            return None
        recent = self.tier_history[-window:]
        if len(set(recent)) == 1:
            return recent[0]
        return None

    def is_follow_up(self, prompt: str) -> bool:
        """Detect if a prompt looks like a follow-up to the previous topic."""
        prompt = prompt.strip()
        if len(prompt.split()) > 8:
            return False
        return any(p.search(prompt) for p in FOLLOW_UP_PATTERNS)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/trevest/loaded-dice && python3 -m pytest tests/test_session.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add lib/session.py tests/test_session.py
git commit -m "feat: add session state management with drift detection and momentum"
```

---

### Task 5: Analytics Logger

**Files:**
- Create: `lib/analytics.py`

- [ ] **Step 1: Implement analytics.py**

```python
# lib/analytics.py
"""NDJSON analytics logging for Loaded Dice."""

import json
import os
import time
from typing import Any


class AnalyticsLogger:
    """Appends routing events to an NDJSON log file."""

    def __init__(self, log_dir: str = "~/.claude/loaded-dice", enabled: bool = True):
        self.log_dir = os.path.expanduser(log_dir)
        self.log_file = os.path.join(self.log_dir, "analytics.ndjson")
        self.enabled = enabled

    def log(self, event: dict[str, Any]) -> None:
        """Append an event to the log file."""
        if not self.enabled:
            return
        event["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        os.makedirs(self.log_dir, exist_ok=True)
        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(event, default=str) + "\n")
        except OSError:
            pass  # non-fatal

    def read_all(self) -> list[dict[str, Any]]:
        """Read all events from the log. Returns empty list on error."""
        if not os.path.isfile(self.log_file):
            return []
        events = []
        try:
            with open(self.log_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        events.append(json.loads(line))
        except (OSError, json.JSONDecodeError):
            pass
        return events
```

- [ ] **Step 2: Commit**

```bash
git add lib/analytics.py
git commit -m "feat: add NDJSON analytics logger"
```

---

### Task 6: Classification Pipeline

**Files:**
- Create: `lib/classifier.py`
- Create: `tests/test_classifier.py`

- [ ] **Step 1: Write the failing test for the full classification pipeline**

```python
# tests/test_classifier.py
import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.classifier import classify
from lib.config import DEFAULT_CONFIG
from lib.session import SessionState


def _make_session(tmpdir):
    return SessionState(state_dir=tmpdir, timeout_minutes=30)


def test_classify_simple_question():
    with tempfile.TemporaryDirectory() as d:
        result = classify("what is a guard statement?", DEFAULT_CONFIG, _make_session(d))
        assert result["tier"] == "haiku"
        assert result["confidence"] >= 0.7
        assert result["source"] == "rules"


def test_classify_test_writing():
    with tempfile.TemporaryDirectory() as d:
        result = classify("write tests for the LoginView", DEFAULT_CONFIG, _make_session(d))
        assert result["tier"] == "sonnet"


def test_classify_architecture():
    with tempfile.TemporaryDirectory() as d:
        result = classify(
            "redesign the sync architecture across all modules",
            DEFAULT_CONFIG,
            _make_session(d),
        )
        assert result["tier"] == "opus"


def test_classify_no_match_defaults_to_sonnet():
    with tempfile.TemporaryDirectory() as d:
        result = classify("hello there", DEFAULT_CONFIG, _make_session(d))
        # No patterns match, confidence 0.5, below threshold,
        # LLM fallback disabled in test → defaults to sonnet (tier-up rule)
        assert result["tier"] == "sonnet"


def test_classify_follow_up_inherits_momentum():
    with tempfile.TemporaryDirectory() as d:
        session = _make_session(d)
        # First: an opus-level question
        session.record_routing("opus", session_model="opus")
        session.record_routing("opus", session_model="opus")
        # Follow-up: short prompt that would normally be haiku
        result = classify("and the networking?", DEFAULT_CONFIG, session)
        # Should inherit opus momentum, not drop to haiku
        assert result["tier"] == "opus"


def test_classify_respects_word_count_guard():
    with tempfile.TemporaryDirectory() as d:
        long_prompt = "what is " + " ".join(["word"] * 100)
        result = classify(long_prompt, DEFAULT_CONFIG, _make_session(d))
        # Exceeds haiku max_word_count (80), should not be haiku
        assert result["tier"] != "haiku"


def test_classify_force_min_word_count():
    with tempfile.TemporaryDirectory() as d:
        long_prompt = " ".join(["word"] * 260)
        result = classify(long_prompt, DEFAULT_CONFIG, _make_session(d))
        # Exceeds opus force_min_word_count (250), should be opus
        assert result["tier"] == "opus"


def test_classify_context_boost_does_not_override_strong_signal():
    with tempfile.TemporaryDirectory() as d:
        session = _make_session(d)
        session.record_routing("haiku", session_model="opus")
        session.record_routing("haiku", session_model="opus")
        # Strong opus signal should override haiku momentum
        result = classify(
            "redesign the architecture across all components",
            DEFAULT_CONFIG,
            session,
        )
        assert result["tier"] == "opus"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/trevest/loaded-dice && python3 -m pytest tests/test_classifier.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement classifier.py**

```python
# lib/classifier.py
"""Three-layer classification pipeline for Loaded Dice."""

import json
import sys
from typing import Any

from lib.patterns import DEFAULT_PATTERNS, TIER_PRIORITY, compile_patterns, match_tier
from lib.config import DEFAULT_CONFIG
from lib.session import SessionState

# Model IDs per tier
TIER_MODELS = {
    "haiku": "haiku",
    "sonnet": "sonnet",
    "opus": "opus",
}


def _build_patterns(config: dict[str, Any]) -> dict[str, list[str]]:
    """Merge default patterns with config overrides."""
    patterns = {}
    for tier in TIER_PRIORITY:
        tier_cfg = config.get("tiers", {}).get(tier, {})
        mode = tier_cfg.get("mode", "extend")

        if mode == "replace":
            patterns[tier] = tier_cfg.get("patterns", [])
        else:
            base = list(DEFAULT_PATTERNS.get(tier, []))
            # Add user patterns
            base.extend(tier_cfg.get("patterns", []))
            # Add keyword patterns (convert keywords to \bkeyword\b patterns)
            for kw in tier_cfg.get("keywords", []):
                base.append(rf"\b{kw}\b")
            # Remove specified patterns
            for rp in tier_cfg.get("remove_patterns", []):
                if rp in base:
                    base.remove(rp)
            # Remove keyword patterns
            for rk in tier_cfg.get("remove_keywords", []):
                pat = rf"\b{rk}\b"
                if pat in base:
                    base.remove(pat)
            patterns[tier] = base

    return patterns


def _get_word_count_guards(config: dict[str, Any]) -> tuple[dict, dict]:
    """Extract max_word_count and force_min_word_count from tier config."""
    max_wc = {}
    force_wc = {}
    for tier in TIER_PRIORITY:
        tier_cfg = config.get("tiers", {}).get(tier, {})
        if "max_word_count" in tier_cfg:
            max_wc[tier] = tier_cfg["max_word_count"]
        if "force_min_word_count" in tier_cfg:
            force_wc[tier] = tier_cfg["force_min_word_count"]
    return max_wc, force_wc


def _llm_fallback(prompt: str, config: dict[str, Any]) -> dict[str, Any] | None:
    """Layer 3: Haiku LLM classification. Returns None on failure."""
    if not config.get("llm_fallback", True):
        return None

    try:
        import anthropic
    except ImportError:
        return None

    classification_prompt = (
        'Classify this coding query into exactly one tier. Return ONLY valid JSON.\n\n'
        f'Query: "{prompt}"\n\n'
        'Tiers:\n'
        '- "haiku": Simple factual questions, syntax lookups, formatting, git simple ops, '
        'file search/read, summarization\n'
        '- "sonnet": Single-file codegen, bug fixes (clear scope), test writing, code review, '
        'single-file refactor, documentation, auditor tasks\n'
        '- "opus": Architecture decisions, multi-file refactoring, complex debugging, '
        'security audits, trade-off analysis, planning, cross-domain synthesis\n\n'
        'Return: {"tier": "...", "confidence": 0.0-1.0, "signals": ["signal1", "signal2"]}'
    )

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            messages=[{"role": "user", "content": classification_prompt}],
        )
        text = response.content[0].text.strip()
        result = json.loads(text)
        if "tier" in result and result["tier"] in TIER_PRIORITY:
            return {
                "tier": result["tier"],
                "confidence": float(result.get("confidence", 0.8)),
                "signals": result.get("signals", []),
            }
    except Exception:
        pass

    return None


def classify(
    prompt: str,
    config: dict[str, Any],
    session: SessionState,
) -> dict[str, Any]:
    """Full three-layer classification pipeline.

    Returns: {tier, confidence, signals, source}
    """
    # Layer 1: Rule-based pattern matching
    merged_patterns = _build_patterns(config)
    compiled = compile_patterns(merged_patterns)
    max_wc, force_wc = _get_word_count_guards(config)

    result = match_tier(
        prompt,
        compiled,
        max_word_counts=max_wc,
        force_min_word_counts=force_wc,
    )

    tier = result["tier"]
    confidence = result["confidence"]
    signals = result["signals"]
    source = "rules"

    # Layer 2: Context boost
    momentum_tier = session.get_momentum_tier(
        window=config.get("momentum_decay_after", 3)
    )

    if session.is_follow_up(prompt) and momentum_tier:
        # Short follow-up inherits previous tier if no strong signal
        if tier is None or confidence < 0.7:
            tier = momentum_tier
            confidence = 0.75
            signals = ["follow_up_momentum"]
            source = "context"
    elif momentum_tier and tier == momentum_tier:
        # Boost confidence when momentum agrees
        confidence = min(1.0, confidence + 0.1)

    # Layer 3: LLM fallback
    threshold = config.get("confidence_threshold", 0.7)
    if confidence < threshold:
        llm_result = _llm_fallback(prompt, config)
        if llm_result:
            tier = llm_result["tier"]
            confidence = llm_result["confidence"]
            signals = llm_result["signals"]
            source = "llm"

    # Final fallback: tier-up rule
    if tier is None or confidence < threshold:
        tier = config.get("default_tier", "sonnet")
        confidence = 0.6
        if not signals:
            signals = ["default_tier_up"]
        source = "default"

    return {
        "tier": tier,
        "confidence": confidence,
        "signals": signals,
        "source": source,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/trevest/loaded-dice && python3 -m pytest tests/test_classifier.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add lib/classifier.py tests/test_classifier.py
git commit -m "feat: add three-layer classification pipeline (rules, context, LLM fallback)"
```

---

### Task 7: UserPromptSubmit Hook

**Files:**
- Create: `hooks/classify-prompt.py`
- Create: `tests/test_hooks.py`

- [ ] **Step 1: Write the failing test for the hook**

```python
# tests/test_hooks.py
import sys
import os
import json
import subprocess
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

HOOK_PATH = os.path.join(os.path.dirname(__file__), "..", "hooks", "classify-prompt.py")
ENFORCE_PATH = os.path.join(os.path.dirname(__file__), "..", "hooks", "enforce-routing.py")


def _run_hook(hook_path: str, stdin_data: dict, env_extra: dict | None = None) -> dict | None:
    """Run a hook script with JSON stdin and parse JSON stdout."""
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = os.path.join(os.path.dirname(__file__), "..")
    env["LOADED_DICE_DISABLE_LLM"] = "1"  # disable LLM in tests
    if env_extra:
        env.update(env_extra)

    with tempfile.TemporaryDirectory() as tmpdir:
        env["LOADED_DICE_STATE_DIR"] = tmpdir

        result = subprocess.run(
            ["python3", hook_path],
            input=json.dumps(stdin_data),
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )

        if result.returncode != 0:
            return None

        stdout = result.stdout.strip()
        if not stdout:
            return {}

        return json.loads(stdout)


def test_classify_prompt_simple_question():
    output = _run_hook(HOOK_PATH, {"prompt": "what is a guard let?"})
    assert output is not None
    ctx = output.get("hookSpecificOutput", {}).get("additionalContext", "")
    assert "haiku" in ctx.lower() or "delegate" in ctx.lower()


def test_classify_prompt_opus_question_no_delegation():
    output = _run_hook(HOOK_PATH, {"prompt": "redesign the architecture across all modules"})
    assert output is not None
    # On an opus session (default auto → opus), this should NOT suggest delegation
    # But since we can't detect session model in test env, just check it runs


def test_classify_prompt_bypass():
    output = _run_hook(HOOK_PATH, {"prompt": "~what is a guard let?"})
    assert output is not None
    # Bypass prefix: should return empty/no delegation
    ctx = output.get("hookSpecificOutput", {}).get("additionalContext", "")
    assert "delegate" not in ctx.lower()


def test_enforce_routing_mismatch():
    output = _run_hook(ENFORCE_PATH, {
        "tool_name": "Agent",
        "tool_input": {
            "model": "opus",
            "prompt": "grep for all usages of UserStore in the codebase",
        },
    })
    assert output is not None
    ctx = output.get("hookSpecificOutput", {}).get("additionalContext", "")
    assert "haiku" in ctx.lower() or "routing note" in ctx.lower()


def test_enforce_routing_match():
    output = _run_hook(ENFORCE_PATH, {
        "tool_name": "Agent",
        "tool_input": {
            "model": "opus",
            "prompt": "redesign the sync architecture across all components",
        },
    })
    assert output is not None
    # Should be silent on match
    ctx = output.get("hookSpecificOutput", {}).get("additionalContext", "")
    assert "mismatch" not in ctx.lower()


def test_enforce_routing_no_model():
    output = _run_hook(ENFORCE_PATH, {
        "tool_name": "Agent",
        "tool_input": {
            "prompt": "grep for all usages of UserStore",
        },
    })
    assert output is not None
    ctx = output.get("hookSpecificOutput", {}).get("additionalContext", "")
    assert "haiku" in ctx.lower() or "model" in ctx.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/trevest/loaded-dice && python3 -m pytest tests/test_hooks.py -v
```

Expected: FAIL — hook scripts don't exist

- [ ] **Step 3: Implement classify-prompt.py**

```python
#!/usr/bin/env python3
"""UserPromptSubmit hook — classifies user prompts and suggests delegation."""

import json
import os
import sys

# Add lib to path
plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, plugin_root)

from lib.classifier import classify, TIER_MODELS
from lib.config import load_config
from lib.session import SessionState
from lib.analytics import AnalyticsLogger


def _detect_session_model(config: dict) -> str:
    """Detect current session model from settings.json or config."""
    session_model = config.get("session_model", "auto")
    if session_model != "auto":
        return session_model

    settings_path = os.path.expanduser("~/.claude/settings.json")
    try:
        with open(settings_path, "r") as f:
            settings = json.load(f)
        model = settings.get("model", "")
        for tier in ["opus", "sonnet", "haiku"]:
            if tier in model.lower():
                return tier
    except (OSError, json.JSONDecodeError, KeyError):
        pass

    return "opus"  # default assumption


def _build_delegation_message(tier: str, prompt_mode: str, confidence: float, signals: list) -> str:
    """Build the additionalContext message for delegation."""
    model = TIER_MODELS[tier]
    signals_str = ", ".join(signals[:3]) if signals else "general classification"

    if prompt_mode == "instruct":
        return (
            f"[Loaded Dice] This is a {tier}-tier question (confidence: {confidence:.2f}, "
            f"signals: {signals_str}). Delegate using:\n"
            f'Agent({{ model: "{model}", prompt: "<the user\'s question>" }})\n'
            f"Do not answer directly."
        )
    else:
        return (
            f"[Loaded Dice] This appears to be a {tier}-tier question (confidence: {confidence:.2f}, "
            f"signals: {signals_str}). Consider delegating to a {model} subagent for efficiency."
        )


def main():
    # Read stdin
    try:
        stdin_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    prompt = stdin_data.get("prompt", "")
    if not prompt:
        sys.exit(0)

    # Load config
    cwd = os.environ.get("CWD", os.getcwd())
    config = load_config(
        global_path="~/.claude/loaded-dice.json",
        project_path=os.path.join(cwd, ".claude", "loaded-dice.json"),
    )

    # Check bypass
    bypass = config.get("bypass_prefix", "~")
    if bypass and prompt.startswith(bypass):
        sys.exit(0)

    # Load session state
    state_dir = os.environ.get("LOADED_DICE_STATE_DIR", "~/.claude/loaded-dice")
    session = SessionState(
        state_dir=state_dir,
        timeout_minutes=config.get("session_timeout_minutes", 30),
    )

    # Disable LLM in test mode
    if os.environ.get("LOADED_DICE_DISABLE_LLM"):
        config["llm_fallback"] = False

    # Classify
    result = classify(prompt, config, session)
    tier = result["tier"]
    confidence = result["confidence"]
    signals = result["signals"]

    # Detect session model
    session_model = _detect_session_model(config)

    # Record routing
    session.record_routing(tier, session_model)

    # Build response
    parts = []

    if tier != session_model:
        msg = _build_delegation_message(
            tier, config.get("prompt_mode", "suggest"), confidence, signals
        )
        parts.append(msg)

    # Check drift
    if session.should_suggest_switch(config.get("suggest_switch_after", 3)):
        n = session.consecutive_off_tier
        parts.append(
            f"[Loaded Dice] Your last {n} prompts were {tier}-tier. "
            f"Consider switching your session model: /dice-switch {tier}"
        )
        session.mark_drift_suggested()

    # Save session
    session.save()

    # Log analytics
    logger = AnalyticsLogger(log_dir=state_dir, enabled=config.get("analytics", True))
    logger.log({
        "hook": "UserPromptSubmit",
        "prompt_words": len(prompt.split()),
        "tier": tier,
        "confidence": confidence,
        "source": result["source"],
        "session_model": session_model,
        "delegated": tier != session_model,
        "drift_count": session.consecutive_off_tier,
    })

    # Output
    if parts:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": "\n\n".join(parts),
            }
        }
        print(json.dumps(output))

    sys.exit(0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify classify-prompt tests pass**

```bash
cd /Users/trevest/loaded-dice && python3 -m pytest tests/test_hooks.py::test_classify_prompt_simple_question tests/test_hooks.py::test_classify_prompt_bypass -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add hooks/classify-prompt.py tests/test_hooks.py
git commit -m "feat: add UserPromptSubmit hook with delegation and drift detection"
```

---

### Task 8: PreToolUse Enforcement Hook

**Files:**
- Create: `hooks/enforce-routing.py`

- [ ] **Step 1: Implement enforce-routing.py**

```python
#!/usr/bin/env python3
"""PreToolUse hook — validates subagent model selection."""

import json
import os
import sys

plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, plugin_root)

from lib.classifier import classify, TIER_MODELS
from lib.config import load_config
from lib.session import SessionState
from lib.analytics import AnalyticsLogger


def main():
    try:
        stdin_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_input = stdin_data.get("tool_input", {})
    prompt = tool_input.get("prompt", "")
    specified_model = tool_input.get("model")

    if not prompt:
        sys.exit(0)

    # Load config
    cwd = os.environ.get("CWD", os.getcwd())
    config = load_config(
        global_path="~/.claude/loaded-dice.json",
        project_path=os.path.join(cwd, ".claude", "loaded-dice.json"),
    )

    if os.environ.get("LOADED_DICE_DISABLE_LLM"):
        config["llm_fallback"] = False

    # Classify the subagent prompt
    state_dir = os.environ.get("LOADED_DICE_STATE_DIR", "~/.claude/loaded-dice")
    session = SessionState(
        state_dir=state_dir,
        timeout_minutes=config.get("session_timeout_minutes", 30),
    )

    result = classify(prompt, config, session)
    recommended = result["tier"]
    signals = result["signals"]

    # Normalize specified model to tier
    specified_tier = None
    if specified_model:
        for tier in ["haiku", "sonnet", "opus"]:
            if tier in str(specified_model).lower():
                specified_tier = tier
                break

    # Build response
    parts = []

    if specified_tier is None:
        # No model specified — recommend one
        signals_str = ", ".join(signals[:3]) if signals else "general classification"
        parts.append(
            f"[Loaded Dice] No model specified for this subagent. "
            f"Recommended: model: \"{recommended}\" "
            f"(signals: {signals_str}). "
            f"Always specify a model parameter when dispatching agents."
        )
    elif specified_tier != recommended:
        # Mismatch — corrective feedback
        signals_str = ", ".join(signals[:3]) if signals else "general classification"
        parts.append(
            f"[Loaded Dice] Routing note: this subagent task was dispatched to "
            f"{specified_tier} but classified as {recommended}-tier "
            f"(signals: {signals_str}). For future dispatches, use "
            f"model: \"{recommended}\" for this type of task."
        )

    # Log analytics
    logger = AnalyticsLogger(log_dir=state_dir, enabled=config.get("analytics", True))
    logger.log({
        "hook": "PreToolUse",
        "specified_model": specified_model,
        "specified_tier": specified_tier,
        "recommended_tier": recommended,
        "mismatch": specified_tier != recommended,
        "signals": signals[:5],
    })

    # Output — never block, only inject context
    if parts:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": "\n\n".join(parts),
            }
        }
        print(json.dumps(output))

    sys.exit(0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run enforcement tests**

```bash
cd /Users/trevest/loaded-dice && python3 -m pytest tests/test_hooks.py -v
```

Expected: all PASS

- [ ] **Step 3: Commit**

```bash
git add hooks/enforce-routing.py
git commit -m "feat: add PreToolUse enforcement hook for subagent model validation"
```

---

### Task 9: Stop Hook

**Files:**
- Create: `hooks/track-session.py`

- [ ] **Step 1: Implement track-session.py**

```python
#!/usr/bin/env python3
"""Stop hook — writes session summary to analytics."""

import json
import os
import sys
import time

plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, plugin_root)

from lib.config import load_config
from lib.session import SessionState
from lib.analytics import AnalyticsLogger


def main():
    state_dir = os.environ.get("LOADED_DICE_STATE_DIR", "~/.claude/loaded-dice")
    cwd = os.environ.get("CWD", os.getcwd())

    config = load_config(
        global_path="~/.claude/loaded-dice.json",
        project_path=os.path.join(cwd, ".claude", "loaded-dice.json"),
    )

    session = SessionState(
        state_dir=state_dir,
        timeout_minutes=config.get("session_timeout_minutes", 30),
    )

    if session.conversation_depth == 0:
        sys.exit(0)

    # Calculate tier distribution
    tier_dist: dict[str, int] = {}
    for t in session.tier_history:
        tier_dist[t] = tier_dist.get(t, 0) + 1

    # Calculate session duration
    duration = (time.time() - session.session_start) / 60

    logger = AnalyticsLogger(log_dir=state_dir, enabled=config.get("analytics", True))
    logger.log({
        "hook": "SessionSummary",
        "duration_minutes": round(duration, 1),
        "total_prompts": session.conversation_depth,
        "tier_distribution": tier_dist,
    })

    # Clean up session state
    try:
        os.remove(session.state_file)
    except OSError:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add hooks/track-session.py
git commit -m "feat: add Stop hook for session summary analytics"
```

---

### Task 10: Slash Command Skills

**Files:**
- Create: `skills/dice-stats/SKILL.md`
- Create: `skills/dice-config/SKILL.md`
- Create: `skills/dice-bypass/SKILL.md`
- Create: `skills/dice-mode/SKILL.md`
- Create: `skills/dice-switch/SKILL.md`

- [ ] **Step 1: Create dice-stats skill**

```markdown
---
name: dice-stats
description: Show Loaded Dice routing statistics — tier distribution, delegation count, mismatch rate
user_invokable: true
---

# /dice-stats

Read the analytics log at `~/.claude/loaded-dice/analytics.ndjson` and display a routing statistics dashboard.

## Steps

1. Read `~/.claude/loaded-dice/analytics.ndjson` using the Read tool
2. Parse each line as JSON
3. Calculate and display:
   - **Total prompts classified** (count of UserPromptSubmit events)
   - **Tier distribution**: count and percentage per tier (haiku/sonnet/opus)
   - **Delegations**: count of prompts where delegated=true
   - **Subagent mismatches**: count of PreToolUse events where mismatch=true
   - **Drift suggestions**: count of events with drift_count >= 3
   - **Classification sources**: breakdown by rules/context/llm/default
4. Format as a clean table
```

- [ ] **Step 2: Create dice-config skill**

```markdown
---
name: dice-config
description: Show active Loaded Dice configuration (merged global + project)
user_invokable: true
---

# /dice-config

Show the active Loaded Dice configuration by reading and merging config files.

## Steps

1. Check for global config at `~/.claude/loaded-dice.json` — read if exists
2. Check for project config at `.claude/loaded-dice.json` — read if exists
3. Show the merged result with defaults applied
4. Highlight any project-level overrides vs global
5. Format as readable JSON or table
```

- [ ] **Step 3: Create dice-bypass skill**

```markdown
---
name: dice-bypass
description: Skip Loaded Dice classification for the next prompt
user_invokable: true
---

# /dice-bypass

Inform the user how to bypass classification.

## Instructions

Tell the user: "Prefix your next prompt with `~` to bypass Loaded Dice classification. Example: `~what is the architecture?` will be handled by the session model directly without delegation."

The bypass prefix is configurable via `bypass_prefix` in `~/.claude/loaded-dice.json`.
```

- [ ] **Step 4: Create dice-mode skill**

```markdown
---
name: dice-mode
description: Switch Loaded Dice prompt mode between suggest and instruct
user_invokable: true
---

# /dice-mode

Switch the prompt mode for Loaded Dice delegation instructions.

## Usage

`/dice-mode suggest` — Advisory mode: "Consider delegating..."
`/dice-mode instruct` — Directive mode: "Delegate to... Do not answer directly."

## Steps

1. Read the argument (suggest or instruct)
2. Read `~/.claude/loaded-dice.json` (create if missing)
3. Update the `prompt_mode` field
4. Write back to `~/.claude/loaded-dice.json`
5. Confirm: "Loaded Dice prompt mode set to {mode}. Takes effect on next prompt."
```

- [ ] **Step 5: Create dice-switch skill**

```markdown
---
name: dice-switch
description: Switch session model tier — writes to settings.json
user_invokable: true
---

# /dice-switch

Switch the Claude Code session model to a different tier.

## Usage

`/dice-switch haiku` — Switch to Haiku (cheapest)
`/dice-switch sonnet` — Switch to Sonnet (balanced)
`/dice-switch opus` — Switch to Opus (most capable)

## Steps

1. Read the argument (haiku, sonnet, or opus)
2. Map to model ID:
   - haiku → `claude-haiku-4-5-20251001`
   - sonnet → `claude-sonnet-4-6`
   - opus → `claude-opus-4-6`
3. Read `~/.claude/settings.json`
4. Update the `model` field to the mapped model ID
5. Write back to `~/.claude/settings.json`
6. Delete `~/.claude/loaded-dice/session.json` to reset session state
7. Confirm: "Session model switched to {tier}. Session state reset. New model takes effect on next prompt."

## Warning

This modifies `~/.claude/settings.json` directly. The change persists across sessions until manually changed or switched again.
```

- [ ] **Step 6: Commit**

```bash
git add skills/
git commit -m "feat: add slash commands — dice-stats, dice-config, dice-bypass, dice-mode, dice-switch"
```

---

### Task 11: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README.md**

```markdown
# Loaded Dice

Intelligent model routing for Claude Code. Classifies every prompt and subagent dispatch by complexity, delegates to the right model tier automatically.

## What It Does

- **Delegates simple questions to cheaper models** — "what is a guard let?" spawns a Haiku subagent instead of burning Opus tokens
- **Warns on subagent model mismatches** — if you dispatch a grep to Opus, Loaded Dice nudges you to use Haiku next time
- **Suggests session switches** — if 3+ consecutive prompts belong to a different tier, suggests `/dice-switch`
- **Context-aware** — follows conversation momentum so follow-ups don't get misrouted

## Install

```bash
claude plugin marketplace add trevestforvor/loaded-dice
claude plugin install loaded-dice
```

Restart your Claude Code session after install.

## Tier Routing

| Tier | Tasks | Model |
|------|-------|-------|
| **Haiku** | File search, grep/glob, syntax questions, git status, formatting | Cheapest |
| **Sonnet** | Single-file codegen, test writing, bug fixes, code review, docs | Balanced |
| **Opus** | Multi-file architecture, complex debugging, planning, trade-off analysis | Most capable |

## Commands

| Command | Description |
|---------|-------------|
| `/dice-stats` | Routing statistics dashboard |
| `/dice-config` | Show active configuration |
| `/dice-bypass` | How to skip classification |
| `/dice-mode suggest\|instruct` | Switch advisory vs directive mode |
| `/dice-switch <tier>` | Switch session model |

Bypass classification by prefixing any prompt with `~`.

## Configuration

Create `~/.claude/loaded-dice.json` for global config, or `.claude/loaded-dice.json` for project-specific overrides.

```json
{
  "prompt_mode": "suggest",
  "confidence_threshold": 0.7,
  "suggest_switch_after": 3,
  "tiers": {
    "opus": {
      "mode": "extend",
      "keywords": ["SwiftData"]
    }
  }
}
```

See `schema/loaded-dice.schema.json` for full schema.

## How It Works

1. **UserPromptSubmit hook** classifies every prompt using regex patterns + optional Haiku LLM fallback
2. If the recommended tier differs from your session model, it injects delegation instructions
3. **PreToolUse hook** checks every Agent dispatch — warns if the model parameter doesn't match the task complexity
4. Session state tracks tier momentum and drift, suggesting model switches when appropriate

## License

MIT
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with install, usage, and configuration guide"
```

---

### Task 12: Run Full Test Suite and Push

- [ ] **Step 1: Run all tests**

```bash
cd /Users/trevest/loaded-dice && python3 -m pytest tests/ -v
```

Expected: all PASS

- [ ] **Step 2: Fix any failures**

Address any test failures found in Step 1.

- [ ] **Step 3: Push to remote**

```bash
cd /Users/trevest/loaded-dice && git push -u origin main
```

- [ ] **Step 4: Remove 0xrdan plugin**

```bash
claude plugin uninstall claude-router
claude plugin marketplace remove 0xrdan-plugins
```

- [ ] **Step 5: Remove routing rules from CLAUDE.md**

Remove the "Delegation" subsection (lines about routing subagent models by task complexity — haiku/sonnet/opus) from `~/.claude/CLAUDE.md`. The plugin is now the single source of truth.

- [ ] **Step 6: Install Loaded Dice from local**

```bash
claude plugin marketplace add /Users/trevest/loaded-dice
claude plugin install loaded-dice
```

- [ ] **Step 7: Verify plugin is installed**

```bash
claude plugin list | grep loaded-dice
```

Expected: `loaded-dice` shows as enabled.

- [ ] **Step 8: Commit CLAUDE.md changes**

```bash
cd ~ && git add .claude/CLAUDE.md && git commit -m "chore: remove manual routing rules — replaced by Loaded Dice plugin"
```
