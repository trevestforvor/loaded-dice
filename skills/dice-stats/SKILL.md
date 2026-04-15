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
