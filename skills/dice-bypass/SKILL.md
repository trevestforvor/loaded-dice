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
