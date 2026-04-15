# Loaded Dice

Intelligent agent routing for Claude Code — automatically delegate tasks to the right model tier (Haiku, Sonnet, Opus) based on task complexity, codebase context, and classification rules.

## Install

```bash
claude plugin marketplace add trevestforvor/loaded-dice
claude plugin install loaded-dice
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

| Command | Effect |
|---------|--------|
| `/dice-stats` | View routing statistics — tier distribution, delegation count, mismatch rate |
| `/dice-config` | Show merged configuration (global + project) |
| `/dice-bypass` | Learn how to skip classification for the next prompt |
| `/dice-mode suggest` | Switch to advisory mode ("Consider delegating...") |
| `/dice-mode instruct` | Switch to directive mode ("Delegate to... Do not answer directly.") |
| `/dice-switch haiku` | Force session to Haiku model |
| `/dice-switch sonnet` | Force session to Sonnet model |
| `/dice-switch opus` | Force session to Opus model |

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
  "enabled": true,
  "prompt_mode": "instruct",
  "bypass_prefix": "~",
  "tier_thresholds": {
    "haiku_context_tokens": 1000,
    "sonnet_context_tokens": 5000,
    "context_expansion_factor": 2.5
  },
  "classification": {
    "rules_weight": 0.4,
    "context_weight": 0.35,
    "llm_weight": 0.25
  }
}
```

### Project Config (`.claude/loaded-dice.json`)

Override global settings per project. Example:

```json
{
  "enabled": true,
  "prompt_mode": "suggest",
  "tier_thresholds": {
    "haiku_context_tokens": 500
  }
}
```

Project config merges with and overrides global config.

## How It Works

**Classification Pipeline:**

1. **Rules-based** (40% weight) — Check prompt patterns, keywords, file count
2. **Context-aware** (35% weight) — Estimate codebase complexity from recent files
3. **LLM-guided** (25% weight) — Run a fast classification prompt on ambiguous tasks
4. **Mismatch detection** — Track when human judgment differs from classification

**Delegation:**

- **Haiku:** Simple queries, file reads, small grep/search tasks
- **Sonnet:** Standard feature dev, refactors, test writing
- **Opus:** Architecture decisions, complex debugging, multi-file judgment

**Analytics:**

Loaded Dice logs all classifications to `~/.claude/loaded-dice/analytics.ndjson`. Use `/dice-stats` to view routing patterns and improve over time.

## License

MIT
