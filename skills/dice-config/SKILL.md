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
