# Cost Savings Metrics for Loaded Dice

**Date:** 2026-04-15
**Status:** Approved

## Problem

Loaded Dice routes prompts to different model tiers but gives users no visibility into the cost impact of that routing. Users want to understand whether the plugin is saving them money and how their prompts distribute across tiers.

## Constraints

- Users may be on Pro, Max, or Enterprise accounts with different pricing structures. Dollar-denominated savings would be misleading as a default.
- Downward routing (expensive tier to cheaper tier) has a clear savings story.
- Upward routing (cheaper tier to more capable tier) is a quality investment, not a savings event. It should be tracked but not framed as savings.

## Design

### 1. Data Collection: Add `word_count` to `PromptClassified`

The classifier's `match_tier()` already computes word count internally. Bubble it up through the return value and include it in the analytics event.

**Changed files:**
- `lib/patterns.py` — `match_tier()` includes `word_count` in its return dict
- `hooks/classify-prompt.py` — logs `word_count` in the `PromptClassified` event

**New event shape:**

```json
{
  "ts": "2026-04-15T12:00:00+00:00",
  "event": "PromptClassified",
  "tier": "haiku",
  "confidence": 0.85,
  "signals": ["ls", "grep"],
  "source": "rules",
  "session_model": "opus",
  "delegated": true,
  "word_count": 42
}
```

No changes to `SubagentRouting` or `SessionSummary` events. No backfill of historical data.

### 2. Cost Ratio Model

**New file: `lib/pricing.py`**

Defines relative tier cost weights (not absolute prices):

```python
DEFAULT_TIER_WEIGHTS = {
    "haiku": 1,
    "sonnet": 12,
    "opus": 60,
}
```

Ratios reflect approximate per-token cost relationships between tiers (haiku as baseline = 1). Configurable via `loaded-dice.json`:

```json
{
  "tier_weights": {
    "haiku": 1,
    "sonnet": 12,
    "opus": 60
  }
}
```

### 3. Savings Math

**Per-prompt (downward routes only, where `delegated=true` AND `tier_weight < session_tier_weight`):**

```
prompt_savings_weight = (session_tier_weight - routed_tier_weight) * word_count
prompt_baseline_weight = session_tier_weight * word_count
```

**Per-direction aggregate:**

```
direction_savings_pct = sum(prompt_savings_weight) / sum(prompt_baseline_weight) * 100
```

**Overall savings (all prompts, both directions):**

```
total_actual_weight = sum(routed_tier_weight * word_count)    # every prompt
total_baseline_weight = sum(session_tier_weight * word_count)  # every prompt
overall_savings_pct = (1 - total_actual_weight / total_baseline_weight) * 100
```

Upward-routed prompts increase `total_actual_weight`, so the overall percentage honestly reflects the net cost impact of routing in both directions.

### 4. Routing Directions

Six possible routing directions, categorized into two groups:

**Downward (savings):**
- Opus -> Haiku
- Opus -> Sonnet
- Sonnet -> Haiku

**Upward (complexity matches):**
- Haiku -> Sonnet
- Haiku -> Opus
- Sonnet -> Opus

Only directions that actually occurred appear in the output. No empty rows.

### 5. Enhanced `/dice-stats` Display

```
Loaded Dice Stats
===========================================

Prompts classified: 142
Tier distribution:  haiku 68 (48%) . sonnet 51 (36%) . opus 23 (16%)
Delegations:        89 (63%)
Classification:     rules 98 . context 31 . llm 8 . default 5

--- Cost Savings ---------------------------
  Estimates based on relative tier pricing,
  not actual account costs.

Direction        Prompts  Words    Savings
Opus -> Haiku        34    1,240    98.3%
Opus -> Sonnet       18    3,680    80.0%
Sonnet -> Haiku      12      580    91.7%

Overall: ~62% estimated savings vs. running
all prompts at session tier

--- Complexity Matches ---------------------
These prompts were shifted up to a higher tier.

Direction        Prompts
Haiku -> Sonnet       8
Haiku -> Opus         3
Sonnet -> Opus        5

--- Session Info ---------------------------
Subagent mismatches: 4
Drift suggestions:   1
```

**Layout rules:**
- Disclaimer always present at top of savings section
- Only directions with data are shown
- Complexity matches are a separate section with counts only — no savings claims
- Overall savings % is the net number accounting for both directions

### 6. Deferred: `--dollars` Mode

Not included in initial implementation. Planned as a fast follow.

When implemented:
- Fetches current per-token rates from Anthropic pricing page
- Approximates tokens from word count using 1.3x multiplier
- Adds `$ Est.` column to savings table
- Additional disclaimer about account-type variance

The current data model (with `word_count` logged) fully supports this future addition.

## Files Changed

| File | Change |
|------|--------|
| `lib/patterns.py` | `match_tier()` returns `word_count` in result dict |
| `hooks/classify-prompt.py` | Logs `word_count` in `PromptClassified` event |
| `lib/pricing.py` | New file — `DEFAULT_TIER_WEIGHTS`, savings calculation functions |
| `skills/dice-stats/SKILL.md` | Updated display instructions with savings + complexity match sections |
| `schema/analytics.json` | Updated schema to include `word_count` field |
| `loaded-dice.json` (user config) | Optional `tier_weights` override |
| `tests/` | Tests for pricing math, updated analytics tests |

## Not Changing

- `SubagentRouting` event shape
- `SessionSummary` event shape
- No historical data backfill
- No passive notifications or per-session summaries
- No bypass (`~`) logging
