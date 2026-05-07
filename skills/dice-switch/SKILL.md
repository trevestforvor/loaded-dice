---
name: dice-switch
description: Switch session model tier — writes to settings.json
argument-hint: "<haiku|sonnet|opus>"
disable-model-invocation: true
allowed-tools: Read Write Bash(rm *)
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
   - opus → `claude-opus-4-7`
3. Read `~/.claude/settings.json`
4. Update the `model` field to the mapped model ID
5. Write back to `~/.claude/settings.json`
6. Delete `~/.claude/loaded-dice/session.json` to reset session state
7. Confirm: "Session model switched to {tier}. Session state reset. New model takes effect on next prompt."

## Warning

This modifies `~/.claude/settings.json` directly. The change persists across sessions until manually changed or switched again.
