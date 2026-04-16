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
