---
name: dice-mode
description: Switch Loaded Dice prompt mode between suggest and instruct
argument-hint: "<suggest|instruct>"
disable-model-invocation: true
allowed-tools: Read Write
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
