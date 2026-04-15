# Loaded Dice — Design Spec

**Date**: 2026-04-15
**Repo**: github.com/trevestforvor/loaded-dice
**Status**: Draft — pending user approval

---

## Problem

Claude Code sessions default to a single model for the entire conversation. When running Opus, trivial questions (syntax lookups, git status, file reads) burn expensive output tokens. When running Haiku or Sonnet, complex architecture questions get weak responses. Manual model routing via CLAUDE.md rules depends on the orchestrator remembering to follow them — which it often doesn't.

## Solution

**Loaded Dice** is a Claude Code plugin that classifies every prompt and subagent dispatch by complexity, then:

1. **Delegates mismatched prompts to subagents at the right tier** — a syntax question on an Opus session spawns a Haiku subagent instead of Opus answering directly
2. **Warns on subagent model mismatches** — if Opus dispatches a grep to an Opus subagent, corrective feedback nudges it to use Haiku next time
3. **Suggests session model switches** — if 3+ consecutive prompts belong to a different tier, suggests switching the session model entirely

The plugin replaces manual CLAUDE.md routing rules with automated, enforceable, context-aware classification.

---

## Architecture

```
User Prompt
    |
    v
+---------------------------+
|   UserPromptSubmit Hook   |
|   (classify-prompt.py)    |
|                           |
|  1. Classify prompt       |
|  2. Check session state   |
|  3. Context boost/decay   |
|  4. LLM fallback if      |
|     confidence < 0.7      |
|                           |
|  Result: tier + conf      |
+----------+----------------+
           |
           +-- tier != session model --> inject "spawn subagent at tier X"
           |                             (advisory or instruct mode)
           |
           +-- tier == session model --> no injection, handle directly
           |
           +-- 3+ consecutive off-tier --> suggest /dice-switch


Opus/Sonnet/Haiku Spawns Subagent
    |
    v
+---------------------------+
|   PreToolUse Hook         |
|   (enforce-routing.py)    |
|   matcher: "Agent"        |
|                           |
|  1. Read Agent tool_input |
|     (model, prompt)       |
|  2. Classify the subtask  |
|  3. Compare model param   |
|     vs recommended tier   |
|  4. WARN if mismatch      |
|     (never block)         |
+---------------------------+


Session End
    |
    v
+---------------------------+
|   Stop Hook               |
|   (track-session.py)      |
|   Write final analytics   |
+---------------------------+
```

### Key Constraint

Hooks cannot programmatically switch models or modify tool calls. Both hooks operate via `additionalContext` injection — instructing the session model through its context, not through API-level control. The PreToolUse hook always allows the tool call through (`permissionDecision` is never set to `deny`).

---

## Classification Engine

Three-layer pipeline, shared by both hooks via `lib/classifier.py`:

### Layer 1: Rule-Based Pattern Matching

Pre-compiled regex patterns produce a tier + confidence score.

**Haiku patterns** (simple, factual, lookup):
- `^what (is|are|does) ` — factual questions
- `^how (do|does|to) ` — how-to questions
- `^(show|list|get) .{0,30}$` — simple show/list operations
- `\b(format|lint|prettify|beautify)\b` — formatting tasks
- `\bgit (status|log|diff|add|commit|push|pull)\b` — git simple ops
- `\b(json|yaml|yml)\b.{0,20}$` — JSON/YAML manipulation
- `\bregex\b` — regex help
- `\bsyntax (for|of)\b` — syntax questions
- `\b(grep|glob|search|find)\b.{0,30}(file|usage|instance)` — file search
- `\bread\b.{0,20}\b(file|contents?)\b` — file reading
- `\bsummar(y|ize)\b.{0,20}\b(file|function|class)\b` — summarization

**Sonnet patterns** (standard codegen, single-scope work):
- `\b(write|add|create|implement)\b.{0,30}\b(test|spec)\b` — test writing
- `\b(fix|debug)\b.{0,30}\b(bug|error|issue)\b` — bug fixes (clear scope)
- `\brefactor\b.{0,30}(function|method|class|view)\b` — single-file refactor
- `\b(review|check)\b.{0,20}\b(code|function|method|PR)\b` — code review
- `\b(document|docstring|comment)\b` — documentation
- `\b(build|implement|create)\b.{0,30}(component|view|screen|endpoint)` — single-file codegen
- `\bauditor?\b` — auditor agent tasks

**Opus patterns** (architecture, judgment, multi-scope):
- `\b(architect|architecture|design pattern|system design)\b` — architecture
- `\b(across|multiple|all) (files?|components?|modules?)\b` — multi-file scope
- `\brefactor.{0,20}(codebase|project|entire)\b` — codebase-wide refactor
- `\b(trade-?off|compare|pros? (and|&) cons?)\b` — trade-off analysis
- `\b(analyze|evaluate|assess).{0,30}(option|approach|strateg)\b` — complex analysis
- `\boptimiz(e|ation).{0,20}(performance|speed|memory)\b` — performance optimization
- `\b(plan|planning|roadmap)\b.{0,30}(implement|migration|phase)\b` — planning
- `\b(security|vulnerab|audit)\b.{0,20}(review|scan|check)\b` — security audit
- `\b(debug|diagnos).{0,30}(race|deadlock|leak|crash)\b` — complex debugging
- `\b(cross-?domain|end-?to-?end|full-?stack)\b` — cross-domain synthesis

**Confidence scoring**:

| Condition | Confidence |
|-----------|------------|
| 3+ signals in same tier | 1.0 (early exit) |
| 2 signals | 0.9 |
| 1 signal | 0.7 |
| No pattern match | 0.5 |

**Priority order**: Opus checked first (highest stakes for misrouting down), then Sonnet, then Haiku. On tie between tiers, higher tier wins.

### Layer 2: Context Boost

Session state adjusts confidence based on conversational flow:

- **Tier momentum**: If the last 2+ prompts routed to the same tier, boost confidence for that tier by 0.1. Prevents ping-ponging on follow-up messages.
- **Relevance decay**: Momentum resets after 3+ prompts at a different tier. A genuine topic shift isn't trapped by stale momentum.
- **Follow-up detection**: Short prompts (< 8 words) starting with "and ", "also ", "what about", "actually", etc. inherit the previous tier's boost. Prevents "and the networking layer?" from dropping to haiku mid-architecture discussion.

### Layer 3: LLM Fallback

Fires when Layer 1 + Layer 2 confidence is below `confidence_threshold` (default 0.7).

**Model**: `claude-haiku-4-5-20251001`

**Prompt**:
```
Classify this coding query into exactly one tier. Return ONLY valid JSON.

Query: "{prompt}"

Tiers:
- "haiku": Simple factual questions, syntax lookups, formatting, git simple ops, file search/read, summarization
- "sonnet": Single-file codegen, bug fixes (clear scope), test writing, code review, single-file refactor, documentation, auditor tasks
- "opus": Architecture decisions, multi-file refactoring, complex debugging, security audits, trade-off analysis, planning, cross-domain synthesis

Return: {"tier": "...", "confidence": 0.0-1.0, "signals": ["signal1", "signal2"]}
```

**Failure handling**: If `anthropic` package is not installed, API call fails, or JSON parsing fails — fall back to Layer 1 result. If Layer 1 confidence was below threshold, apply the "when uncertain, tier up" rule: default to `sonnet` (not haiku).

---

## Session Model Awareness

The plugin detects the current session model at session start (from `~/.claude/settings.json` or config override) and compares classification results against it.

| Session Model | Recommended Tier | Action |
|---------------|-----------------|--------|
| opus | haiku | Delegate down via subagent |
| opus | sonnet | Delegate down via subagent |
| opus | opus | No delegation |
| sonnet | haiku | Delegate down via subagent |
| sonnet | sonnet | No delegation |
| sonnet | opus | Delegate **up** via subagent |
| haiku | sonnet | Delegate up via subagent |
| haiku | opus | Delegate up via subagent |

Delegation instruction injected via `additionalContext`:
```
This is a {tier}-tier question. Delegate using:
Agent({ model: "{tier_model}", prompt: "<the user's question>" })
Do not answer directly.
```

The exact wording varies by `prompt_mode` (see Configuration).

---

## Tier Drift Detection

Session state tracks `consecutive_off_tier` — the number of consecutive prompts where the recommended tier differs from the session model.

When `consecutive_off_tier >= suggest_switch_after` (default 3), inject a one-time suggestion:

> "Your last {N} prompts were {tier}-tier. Consider switching your session model: `/dice-switch {tier}`"

The suggestion fires once per drift streak. It resets when:
- The user runs `/dice-switch`
- A prompt matches the current session tier
- The drift direction changes (e.g., was drifting toward haiku, now drifting toward opus)

---

## Hook Specifications

### Hook 1: UserPromptSubmit — `classify-prompt.py`

**Trigger**: Every user message.

**Stdin**: `{"prompt": "user's message text"}`

**Logic**:
1. Check for bypass prefix (`~` by default) — if present, strip prefix, skip classification, output nothing
2. Load config (global + project merge)
3. Load session state
4. Run classification pipeline → `{tier, confidence, signals, source}`
5. Compare tier vs session model
6. If different: build `additionalContext` with delegation instruction
7. Update session state (tier history, consecutive_off_tier, drift detection)
8. If drift threshold reached: append switch suggestion to `additionalContext`
9. Log to analytics
10. Write JSON to stdout: `{"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "..."}}`

**Prompt modes** (config: `prompt_mode`):
- `"suggest"`: "This appears to be a {tier}-tier question. Consider delegating to a {tier} subagent for efficiency."
- `"instruct"`: "This is a {tier}-tier question. Delegate to a subagent with model: {tier_model}. Do not answer directly." (Note: even in instruct mode, this is context injection — it cannot programmatically force delegation. The session model may still choose to answer directly.)

### Hook 2: PreToolUse on Agent — `enforce-routing.py`

**Trigger**: Every `Agent` tool call.

**Matcher**: `"Agent"`

**Stdin**: `{"tool_name": "Agent", "tool_input": {"model": "opus", "prompt": "...", ...}}`

**Logic**:
1. Extract `model` and `prompt` from `tool_input`
2. If `model` is missing/null: flag as "no model specified" — recommend one
3. Run classification pipeline on the subagent `prompt`
4. Compare specified `model` vs recommended tier
5. If match: output nothing (allow silently)
6. If mismatch: output corrective `additionalContext`
7. Log to analytics (track mismatch rate over time)
8. Never set `permissionDecision` — always allow through

**Corrective message example**:
> "Routing note: this subagent task was dispatched to opus but classified as haiku-tier (signals: file search, grep). For future dispatches, use model: haiku for search/lookup tasks."

### Hook 3: Stop — `track-session.py`

**Trigger**: Session end.

**Logic**:
1. Read session state
2. Write summary entry to analytics log (session duration, total prompts, tier distribution, mismatch count)
3. Clean up session state file

---

## Configuration

### Global config: `~/.claude/loaded-dice.json`

### Project override: `.claude/loaded-dice.json`

Project config merges on top of global. Per-tier `mode` controls merge behavior.

### Schema

```json
{
  "session_model": "auto",
  "prompt_mode": "suggest",
  "confidence_threshold": 0.7,
  "default_tier": "sonnet",
  "bypass_prefix": "~",
  "session_timeout_minutes": 30,
  "momentum_decay_after": 3,
  "suggest_switch_after": 3,
  "llm_fallback": true,
  "analytics": true,

  "tiers": {
    "haiku": {
      "mode": "extend",
      "keywords": [],
      "patterns": [],
      "remove_keywords": [],
      "remove_patterns": [],
      "max_word_count": 80
    },
    "sonnet": {
      "mode": "extend",
      "keywords": [],
      "patterns": [],
      "remove_keywords": [],
      "remove_patterns": []
    },
    "opus": {
      "mode": "extend",
      "keywords": [],
      "patterns": [],
      "remove_keywords": [],
      "remove_patterns": [],
      "force_min_word_count": 250
    }
  }
}
```

**Field reference**:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `session_model` | string | `"auto"` | `"auto"` reads from settings.json; or `"haiku"` / `"sonnet"` / `"opus"` |
| `prompt_mode` | string | `"suggest"` | `"suggest"` = advisory; `"instruct"` = directive |
| `confidence_threshold` | float | `0.7` | Below this, LLM fallback fires |
| `default_tier` | string | `"sonnet"` | Fallback when uncertain (tier-up rule) |
| `bypass_prefix` | string | `"~"` | Prefix to skip classification |
| `session_timeout_minutes` | int | `30` | Session state expiry |
| `momentum_decay_after` | int | `3` | Tier momentum resets after N prompts at different tier |
| `suggest_switch_after` | int | `3` | Suggest session switch after N consecutive off-tier prompts |
| `llm_fallback` | bool | `true` | Enable/disable Haiku LLM classifier |
| `analytics` | bool | `true` | Enable/disable NDJSON logging |

**Per-tier fields**:

| Field | Type | Description |
|-------|------|-------------|
| `mode` | string | `"extend"` adds to defaults; `"replace"` overwrites defaults |
| `keywords` | string[] | Additional keywords to match |
| `patterns` | string[] | Additional regex patterns to match |
| `remove_keywords` | string[] | Remove specific keywords from defaults |
| `remove_patterns` | string[] | Remove specific patterns from defaults |
| `max_word_count` | int | Hard cap — prompts exceeding this skip the tier |
| `force_min_word_count` | int | Auto-escalate to this tier if word count exceeds threshold |

---

## Slash Commands

| Command | Purpose |
|---------|---------|
| `/dice-stats` | Routing stats dashboard — tier distribution, mismatch rate, delegation count, estimated savings |
| `/dice-config` | Show active config (merged global + project) |
| `/dice-bypass` | Skip classification for the next prompt |
| `/dice-mode suggest\|instruct` | Switch prompt mode mid-session |
| `/dice-switch <tier>` | Switch session model — writes to settings.json, resets session state |

---

## Analytics

**Log file**: `~/.claude/loaded-dice/analytics.ndjson`

**Per-prompt entry**:
```json
{
  "ts": "2026-04-15T10:30:00Z",
  "session_id": "abc123",
  "hook": "UserPromptSubmit",
  "prompt_words": 12,
  "tier": "haiku",
  "confidence": 0.92,
  "source": "rules",
  "session_model": "opus",
  "delegated": true,
  "drift_count": 0
}
```

**Per-subagent entry**:
```json
{
  "ts": "2026-04-15T10:30:05Z",
  "session_id": "abc123",
  "hook": "PreToolUse",
  "specified_model": "opus",
  "recommended_tier": "haiku",
  "mismatch": true,
  "signals": ["file search", "grep"]
}
```

**Session summary** (written by Stop hook):
```json
{
  "ts": "2026-04-15T11:00:00Z",
  "session_id": "abc123",
  "duration_minutes": 30,
  "total_prompts": 45,
  "tier_distribution": {"haiku": 20, "sonnet": 15, "opus": 10},
  "delegations": 18,
  "subagent_mismatches": 3,
  "drift_suggestions": 1
}
```

---

## Plugin Structure

```
loaded-dice/
├── .claude-plugin/
│   ├── plugin.json
│   └── hooks/
│       └── hooks.json
├── hooks/
│   ├── classify-prompt.py
│   ├── enforce-routing.py
│   └── track-session.py
├── skills/
│   ├── dice-stats/SKILL.md
│   ├── dice-config/SKILL.md
│   ├── dice-bypass/SKILL.md
│   ├── dice-mode/SKILL.md
│   └── dice-switch/SKILL.md
├── lib/
│   ├── classifier.py
│   ├── session.py
│   ├── config.py
│   └── patterns.py
├── schema/
│   └── loaded-dice.schema.json
├── README.md
└── LICENSE
```

**Runtime data** (not in repo, created at runtime):
- `~/.claude/loaded-dice/session.json` — current session state
- `~/.claude/loaded-dice/analytics.ndjson` — routing log
- `~/.claude/loaded-dice.json` — global config (user-created)
- `.claude/loaded-dice.json` — project config (user-created)

---

## Install / Uninstall

**Install**:
```bash
claude plugin marketplace add trevestforvor/loaded-dice
claude plugin install loaded-dice
```

**Post-install**: Remove the "Delegation" routing section from CLAUDE.md. The plugin is now the single source of truth for model routing.

**Uninstall**:
```bash
claude plugin uninstall loaded-dice
```

Add the routing rules back to CLAUDE.md if desired.

---

## What This Plugin Does NOT Do

- **Does not switch models programmatically** — Claude Code hooks cannot change the session model via API. Model switching happens via `additionalContext` instructions (for delegation) or `/dice-switch` (writes settings.json).
- **Does not block tool calls** — PreToolUse hook never denies. All corrections are advisory.
- **Does not access conversation history** — hooks only see the current event payload. Session awareness is maintained via the plugin's own state file.
- **Does not define custom agents** — uses the built-in `Agent` tool with `model:` parameter to avoid namespace conflicts with other plugins.

---

## Open Questions for Implementation

1. **Python dependency**: The LLM fallback requires the `anthropic` pip package. Should the install script check for it and offer to install, or just degrade gracefully?
2. **Hook timeout**: Claude Code hooks have a practical timeout (~10-15s). The LLM fallback should have its own timeout (e.g., 3s) to avoid blocking the session.
3. **Testing**: How do we test the classification engine? Unit tests on `lib/classifier.py` with sample prompts and expected tiers.
