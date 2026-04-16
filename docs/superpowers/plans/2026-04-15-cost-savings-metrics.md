# Cost Savings Metrics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add percentage-based cost savings estimates and complexity match tracking to `/dice-stats`

**Architecture:** New `lib/pricing.py` module handles tier weight definitions and savings calculations. The `/dice-stats` skill instructions are updated to display two new sections (Cost Savings, Complexity Matches). No changes needed to data collection — `word_count` is already logged in `PromptClassified` events.

**Tech Stack:** Python 3, pytest, NDJSON analytics log

---

### Task 1: Create `lib/pricing.py` with tier weights and savings calculations

**Files:**
- Create: `lib/pricing.py`
- Create: `tests/test_pricing.py`

- [ ] **Step 1: Write failing tests for tier weight lookups**

```python
"""Tests for pricing module — tier weights and savings calculations."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.pricing import TIER_WEIGHTS, tier_weight


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/trevest/developer/loaded-dice && python -m pytest tests/test_pricing.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'lib.pricing'`

- [ ] **Step 3: Implement tier weights**

Create `lib/pricing.py`:

```python
"""Tier cost weights and savings calculations for loaded-dice metrics."""

from __future__ import annotations

# Relative per-token cost ratios (April 2026 Anthropic API pricing).
# Input and output ratios are both 1:3:5 across haiku/sonnet/opus.
TIER_WEIGHTS: dict[str, int] = {
    "haiku": 1,
    "sonnet": 3,
    "opus": 5,
}


def tier_weight(tier: str) -> int | None:
    """Return the cost weight for a tier, or None if unknown."""
    return TIER_WEIGHTS.get(tier)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/trevest/developer/loaded-dice && python -m pytest tests/test_pricing.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/trevest/developer/loaded-dice
git add lib/pricing.py tests/test_pricing.py
git commit -m "feat: add lib/pricing.py with tier cost weights"
```

---

### Task 2: Add savings calculation functions to `lib/pricing.py`

**Files:**
- Modify: `lib/pricing.py`
- Modify: `tests/test_pricing.py`

- [ ] **Step 1: Write failing tests for `classify_direction`**

Append to `tests/test_pricing.py`:

```python
from lib.pricing import classify_direction


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/trevest/developer/loaded-dice && python -m pytest tests/test_pricing.py::TestClassifyDirection -v`
Expected: FAIL — `ImportError: cannot import name 'classify_direction'`

- [ ] **Step 3: Implement `classify_direction`**

Add to `lib/pricing.py`:

```python
def classify_direction(session_tier: str, routed_tier: str) -> str | None:
    """Classify a routing event as 'downward', 'upward', or None (same tier).

    Returns:
        'downward' if routed to a cheaper tier (savings)
        'upward' if routed to a more expensive tier (complexity match)
        None if same tier (no routing)
    """
    session_w = TIER_WEIGHTS.get(session_tier)
    routed_w = TIER_WEIGHTS.get(routed_tier)
    if session_w is None or routed_w is None or session_w == routed_w:
        return None
    return "downward" if routed_w < session_w else "upward"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/trevest/developer/loaded-dice && python -m pytest tests/test_pricing.py::TestClassifyDirection -v`
Expected: All 9 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/trevest/developer/loaded-dice
git add lib/pricing.py tests/test_pricing.py
git commit -m "feat: add classify_direction to pricing module"
```

---

### Task 3: Add `compute_savings` function

**Files:**
- Modify: `lib/pricing.py`
- Modify: `tests/test_pricing.py`

- [ ] **Step 1: Write failing tests for `compute_savings`**

Append to `tests/test_pricing.py`:

```python
from lib.pricing import compute_savings


class TestComputeSavings:
    def test_all_downward_opus_to_haiku(self):
        """All prompts routed from opus to haiku — 80% savings."""
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
        """All prompts routed from opus to sonnet — 40% savings."""
        events = [
            {"tier": "sonnet", "session_model": "opus", "word_count": 50},
        ]
        result = compute_savings(events)
        assert result["overall_savings_pct"] == 40.0
        assert result["downward"][0]["savings_pct"] == 40.0

    def test_all_downward_sonnet_to_haiku(self):
        """All prompts routed from sonnet to haiku — 66.7% savings."""
        events = [
            {"tier": "haiku", "session_model": "sonnet", "word_count": 90},
        ]
        result = compute_savings(events)
        assert abs(result["overall_savings_pct"] - 66.7) < 0.1

    def test_upward_routing_tracked_separately(self):
        """Upward routes appear in complexity_matches, not downward."""
        events = [
            {"tier": "opus", "session_model": "haiku", "word_count": 200},
            {"tier": "sonnet", "session_model": "haiku", "word_count": 100},
        ]
        result = compute_savings(events)
        assert len(result["downward"]) == 0
        assert len(result["complexity_matches"]) == 2

    def test_mixed_directions(self):
        """Mix of downward and upward — overall reflects net effect."""
        events = [
            # 3 downward: opus -> haiku (weight saved: (5-1)*100 = 400 each)
            {"tier": "haiku", "session_model": "opus", "word_count": 100},
            {"tier": "haiku", "session_model": "opus", "word_count": 100},
            {"tier": "haiku", "session_model": "opus", "word_count": 100},
            # 1 upward: haiku -> opus (weight added: (5-1)*100 = 400)
            {"tier": "opus", "session_model": "haiku", "word_count": 100},
        ]
        result = compute_savings(events)
        # baseline: 3*5*100 + 1*1*100 = 1600
        # actual:   3*1*100 + 1*5*100 = 800
        # savings: 1 - 800/1600 = 50%
        assert result["overall_savings_pct"] == 50.0
        assert len(result["downward"]) == 1
        assert len(result["complexity_matches"]) == 1

    def test_same_tier_events_ignored(self):
        """Events where tier == session_model don't appear in either list."""
        events = [
            {"tier": "opus", "session_model": "opus", "word_count": 100},
            {"tier": "haiku", "session_model": "opus", "word_count": 50},
        ]
        result = compute_savings(events)
        assert len(result["downward"]) == 1
        assert len(result["complexity_matches"]) == 0
        # baseline: 5*100 + 5*50 = 750
        # actual:   5*100 + 1*50 = 550
        # savings: 1 - 550/750 ≈ 26.7%
        assert abs(result["overall_savings_pct"] - 26.7) < 0.1

    def test_no_events_returns_zero(self):
        """Empty event list returns zero savings."""
        result = compute_savings([])
        assert result["overall_savings_pct"] == 0.0
        assert result["downward"] == []
        assert result["complexity_matches"] == []

    def test_events_missing_word_count_skipped(self):
        """Events without word_count are excluded from calculations."""
        events = [
            {"tier": "haiku", "session_model": "opus"},
            {"tier": "haiku", "session_model": "opus", "word_count": 100},
        ]
        result = compute_savings(events)
        assert result["downward"][0]["prompts"] == 1
        assert result["downward"][0]["words"] == 100
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/trevest/developer/loaded-dice && python -m pytest tests/test_pricing.py::TestComputeSavings -v`
Expected: FAIL — `ImportError: cannot import name 'compute_savings'`

- [ ] **Step 3: Implement `compute_savings`**

Add to `lib/pricing.py`:

```python
def compute_savings(events: list[dict]) -> dict:
    """Compute cost savings metrics from PromptClassified analytics events.

    Args:
        events: List of PromptClassified event dicts. Each must have
                'tier', 'session_model', and 'word_count' keys.
                Events missing 'word_count' are skipped.

    Returns:
        dict with keys:
            overall_savings_pct: float — net savings across all events
            downward: list of dicts — per-direction savings for cheaper routing
            complexity_matches: list of dicts — per-direction counts for upward routing
    """
    # Accumulators for per-direction stats
    # key: (session_tier, routed_tier)
    down_prompts: dict[tuple[str, str], int] = {}
    down_words: dict[tuple[str, str], int] = {}
    down_savings_weight: dict[tuple[str, str], float] = {}
    down_baseline_weight: dict[tuple[str, str], float] = {}

    up_prompts: dict[tuple[str, str], int] = {}

    total_actual = 0.0
    total_baseline = 0.0

    for ev in events:
        wc = ev.get("word_count")
        if wc is None:
            continue

        session_tier = ev.get("session_model", "")
        routed_tier = ev.get("tier", "")
        s_w = TIER_WEIGHTS.get(session_tier)
        r_w = TIER_WEIGHTS.get(routed_tier)

        if s_w is None or r_w is None:
            continue

        total_actual += r_w * wc
        total_baseline += s_w * wc

        direction = classify_direction(session_tier, routed_tier)
        if direction == "downward":
            key = (session_tier, routed_tier)
            down_prompts[key] = down_prompts.get(key, 0) + 1
            down_words[key] = down_words.get(key, 0) + wc
            down_savings_weight[key] = down_savings_weight.get(key, 0.0) + (s_w - r_w) * wc
            down_baseline_weight[key] = down_baseline_weight.get(key, 0.0) + s_w * wc
        elif direction == "upward":
            key = (session_tier, routed_tier)
            up_prompts[key] = up_prompts.get(key, 0) + 1

    # Build downward list
    _label = {"opus": "Opus", "sonnet": "Sonnet", "haiku": "Haiku"}
    downward = []
    for key in sorted(down_prompts.keys()):
        s_tier, r_tier = key
        baseline = down_baseline_weight[key]
        pct = (down_savings_weight[key] / baseline * 100) if baseline else 0.0
        downward.append({
            "direction": f"{_label.get(s_tier, s_tier)} -> {_label.get(r_tier, r_tier)}",
            "prompts": down_prompts[key],
            "words": down_words[key],
            "savings_pct": round(pct, 1),
        })

    # Build complexity matches list
    complexity_matches = []
    for key in sorted(up_prompts.keys()):
        s_tier, r_tier = key
        complexity_matches.append({
            "direction": f"{_label.get(s_tier, s_tier)} -> {_label.get(r_tier, r_tier)}",
            "prompts": up_prompts[key],
        })

    # Overall savings
    overall = round((1 - total_actual / total_baseline) * 100, 1) if total_baseline else 0.0

    return {
        "overall_savings_pct": overall,
        "downward": downward,
        "complexity_matches": complexity_matches,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/trevest/developer/loaded-dice && python -m pytest tests/test_pricing.py -v`
Expected: All tests PASS (TestTierWeights + TestClassifyDirection + TestComputeSavings)

- [ ] **Step 5: Commit**

```bash
cd /Users/trevest/developer/loaded-dice
git add lib/pricing.py tests/test_pricing.py
git commit -m "feat: add compute_savings function with per-direction breakdowns"
```

---

### Task 4: Update `/dice-stats` skill with savings and complexity match sections

**Files:**
- Modify: `skills/dice-stats/SKILL.md`

- [ ] **Step 1: Read the current skill file**

Read: `/Users/trevest/developer/loaded-dice/skills/dice-stats/SKILL.md`

- [ ] **Step 2: Replace the skill content with the enhanced version**

Replace the entire content of `skills/dice-stats/SKILL.md` with:

````markdown
---
name: dice-stats
description: Show Loaded Dice routing statistics — tier distribution, delegation count, mismatch rate, cost savings estimates, and complexity matches
user_invokable: true
---

# /dice-stats

Read the analytics log at `~/.claude/loaded-dice/analytics.ndjson` and display a routing statistics dashboard with cost savings estimates.

## Steps

1. Read `~/.claude/loaded-dice/analytics.ndjson` using the Read tool
2. Parse each line as JSON
3. Filter events by type:
   - `PromptClassified` events for tier stats, savings, and complexity matches
   - `SubagentRouting` events for mismatch tracking
4. Calculate and display the sections below

## Display Format

### Section 1: Overview

```
Loaded Dice Stats
===========================================

Prompts classified: {count of PromptClassified events}
Tier distribution:  haiku {n} ({pct}%) · sonnet {n} ({pct}%) · opus {n} ({pct}%)
Delegations:        {count where delegated=true} ({pct}%)
Classification:     rules {n} · context {n} · llm {n} · default {n}
```

### Section 2: Cost Savings

For each `PromptClassified` event that has a `word_count` field, calculate savings using relative tier cost weights: **haiku=1, sonnet=3, opus=5**.

**Downward routes** (where the routed tier is cheaper than the session tier):
- Opus -> Haiku: savings_pct = 80.0%
- Opus -> Sonnet: savings_pct = 40.0%
- Sonnet -> Haiku: savings_pct = 66.7%

**Overall savings**: `(1 - sum(routed_weight * word_count) / sum(session_weight * word_count)) * 100` across ALL events (including upward routes and same-tier events in the denominator).

Only show directions that have at least one event. Skip this section entirely if no events have `word_count`.

```
--- Cost Savings ---------------------------
  Estimates based on relative tier pricing,
  not actual account costs.

Direction        Prompts  Words    Savings
Opus -> Haiku        {n}  {words}  {pct}%
Opus -> Sonnet       {n}  {words}  {pct}%
Sonnet -> Haiku      {n}  {words}  {pct}%

Overall: ~{pct}% estimated savings vs. running
all prompts at session tier
```

### Section 3: Complexity Matches

**Upward routes** (where the routed tier is more expensive than the session tier). Show count only — no savings claims.

Only show directions that have at least one event. Skip this section entirely if no upward routes occurred.

```
--- Complexity Matches ---------------------
These prompts were shifted up to a higher tier.

Direction        Prompts
Haiku -> Sonnet      {n}
Haiku -> Opus        {n}
Sonnet -> Opus       {n}
```

### Section 4: Session Info

```
--- Session Info ---------------------------
Subagent mismatches: {count of SubagentRouting events where mismatch=true}
Drift suggestions:   {count of events with drift_count >= 3}
```
````

- [ ] **Step 3: Commit**

```bash
cd /Users/trevest/developer/loaded-dice
git add skills/dice-stats/SKILL.md
git commit -m "feat: update dice-stats skill with savings and complexity match sections"
```

---

### Task 5: Run full test suite and verify

**Files:**
- No changes — verification only

- [ ] **Step 1: Run full test suite**

Run: `cd /Users/trevest/developer/loaded-dice && python -m pytest tests/ -v`
Expected: All tests PASS, including existing tests (no regressions)

- [ ] **Step 2: Verify pricing module imports cleanly**

Run: `cd /Users/trevest/developer/loaded-dice && python -c "from lib.pricing import TIER_WEIGHTS, tier_weight, classify_direction, compute_savings; print('OK:', TIER_WEIGHTS)"`
Expected: `OK: {'haiku': 1, 'sonnet': 3, 'opus': 5}`

- [ ] **Step 3: Update spec to note word_count was already logged**

Edit `/Users/trevest/developer/loaded-dice/docs/superpowers/specs/2026-04-15-cost-savings-metrics-design.md` section 1 to note that `word_count` and `prompt_preview` were already being logged by the hook — no data collection changes were needed.

- [ ] **Step 4: Commit spec update**

```bash
cd /Users/trevest/developer/loaded-dice
git add docs/superpowers/specs/2026-04-15-cost-savings-metrics-design.md
git commit -m "docs: note word_count was already logged, no data collection changes needed"
```
