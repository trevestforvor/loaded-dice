---
name: dice-bypass
description: Explain how to skip Loaded Dice classification for the next prompt by using the bypass prefix
---

# /dice-bypass

Inform the user how to bypass classification.

## Instructions

Tell the user: "Prefix your next prompt with `~` to bypass Loaded Dice classification. Example: `~what is the architecture?` will be handled by the session model directly without delegation."

The bypass prefix is configurable via `bypass_prefix` in `~/.claude/loaded-dice.json`.
