# Loaded Dice

Intelligent agent routing for Claude Code — automatically delegate tasks to the right model tier (Haiku, Sonnet, Opus) based on task complexity, codebase context, and classification rules.

## Install

Inside Claude Code, run:

```
/plugin marketplace add trevestforvor/loaded-dice
/plugin install loaded-dice@loaded-dice
```

## Quick Start

Loaded Dice activates by default. Every prompt is classified into one of three tiers:

| Tier | Best For | Cost |
|------|----------|------|
| **Haiku** | Simple searches, file reads, straightforward refactors | Cheapest |
| **Sonnet** | Standard codegen, test writing, single-file changes | Balanced |
| **Opus** | Multi-file architecture, debugging, complex judgment | Most capable |

Classification happens automatically. You can adjust the mode or disable routing with slash commands.

## Commands

Plugin skills are namespaced; type the full command in Claude Code:

| Command | Effect |
|---------|--------|
| `/loaded-dice:dice-stats` | View routing statistics — tier distribution, delegation count, mismatch rate |
| `/loaded-dice:dice-config` | Show merged configuration (global + project) |
| `/loaded-dice:dice-bypass` | Learn how to skip classification for the next prompt |
| `/loaded-dice:dice-mode suggest` | Switch to advisory mode ("Consider delegating...") |
| `/loaded-dice:dice-mode instruct` | Switch to directive mode ("Delegate to... Do not answer directly.") |
| `/loaded-dice:dice-switch haiku` | Force session to Haiku model |
| `/loaded-dice:dice-switch sonnet` | Force session to Sonnet model |
| `/loaded-dice:dice-switch opus` | Force session to Opus model |

## Bypass Classification

Prefix your prompt with `~` to skip Loaded Dice and use your current session model directly:

```
~what is the architecture of this codebase?
```

The bypass prefix is configurable via `~/.claude/loaded-dice.json`.

## Configuration

### Global Config (`~/.claude/loaded-dice.json`)

```json
{
  "prompt_mode": "instruct",
  "bypass_prefix": "~",
  "confidence_threshold": 0.7,
  "default_tier": "sonnet",
  "llm_fallback": true,
  "analytics": true,
  "tiers": {
    "haiku": { "max_word_count": 80 },
    "opus":  { "force_min_word_count": 250 }
  }
}
```

See `schema/loaded-dice.schema.json` for the full set of fields and per-tier
keyword/pattern overrides.

### Project Config (`.claude/loaded-dice.json`)

Override global settings per project. Example:

```json
{
  "prompt_mode": "suggest",
  "tiers": {
    "haiku": { "keywords": ["readme", "changelog"] }
  }
}
```

Project config merges with and overrides global config.

## How It Works

**Classification Pipeline:**

1. **Rules-based** — Match prompt against per-tier keyword and regex patterns; multiple signals raise confidence (`opus` > `sonnet` > `haiku` priority).
2. **Context / momentum** — Inherit the recent tier on conversational follow-ups; boost confidence when momentum agrees with the rule match.
3. **LLM fallback** — When confidence stays below the threshold, ask Haiku to classify.
4. **Drift detection** — Track when the routed tier diverges from the session model and offer to switch after repeated drift.

**Delegation:**

- **Haiku:** Simple queries, file reads, small grep/search tasks
- **Sonnet:** Standard feature dev, refactors, test writing
- **Opus:** Architecture decisions, complex debugging, multi-file judgment

**Analytics:**

Loaded Dice logs all classifications to `~/.claude/loaded-dice/analytics.ndjson`. Use `/dice-stats` to view routing patterns and improve over time.

## License

MIT
