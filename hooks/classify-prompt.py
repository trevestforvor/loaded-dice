#!/usr/bin/env python3
"""UserPromptSubmit hook — classify prompt and emit delegation guidance."""

import json
import os
import sys

# Allow importing from lib/ relative to the repo root
_PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, _PLUGIN_ROOT)

from lib.config import load_config
from lib.session import SessionState
from lib.classifier import classify
from lib.analytics import AnalyticsLogger

TIER_MODELS = {
    "haiku": "haiku",
    "sonnet": "sonnet",
    "opus": "opus",
}


def _detect_session_model(config: dict) -> str:
    """Resolve session model: config value, or read from ~/.claude/settings.json."""
    session_model = config.get("session_model", "auto")
    if session_model != "auto":
        return session_model

    settings_path = os.path.expanduser("~/.claude/settings.json")
    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
        model_str = settings.get("model", "")
        # Extract tier name from model string (e.g. "claude-opus-4-5" -> "opus")
        for tier in ("haiku", "sonnet", "opus"):
            if tier in model_str.lower():
                return tier
    except (OSError, json.JSONDecodeError):
        pass

    return "opus"


def main() -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        sys.exit(0)

    prompt = data.get("prompt", "")

    # Bypass prefix check
    bypass_prefix = "~"
    if prompt.startswith(bypass_prefix):
        sys.exit(0)

    cwd = os.getcwd()
    config = load_config(
        global_path=os.path.expanduser("~/.claude/loaded-dice.json"),
        project_path=os.path.join(cwd, ".claude", "loaded-dice.json"),
    )

    state_dir = os.environ.get("LOADED_DICE_STATE_DIR", "~/.claude/loaded-dice")
    session = SessionState(state_dir=state_dir, timeout_minutes=config.get("session_timeout_minutes", 30))

    # Disable LLM if env var set
    if os.environ.get("LOADED_DICE_DISABLE_LLM"):
        config["llm_fallback"] = False

    result = classify(prompt, config, session)
    tier = result["tier"]
    confidence = result["confidence"]
    signals = result["signals"]

    session_model = _detect_session_model(config)
    session.record_routing(tier, session_model)

    messages = []

    if tier != session_model:
        model = TIER_MODELS.get(tier, tier)
        signals_str = ", ".join(signals) if signals else "none"
        prompt_mode = config.get("prompt_mode", "suggest")

        if prompt_mode == "instruct":
            msg = (
                f'[Loaded Dice] This is a {tier}-tier question '
                f'(confidence: {confidence:.2f}, signals: {signals_str}). '
                f'Delegate using:\n'
                f'Agent({{ model: "{model}", prompt: "<the user\'s question>" }})\n'
                f'Do not answer directly.'
            )
        else:
            msg = (
                f'[Loaded Dice] This appears to be a {tier}-tier question '
                f'(confidence: {confidence:.2f}, signals: {signals_str}). '
                f'Consider delegating to a {model} subagent for efficiency.'
            )
        messages.append(msg)

    suggest_threshold = config.get("suggest_switch_after", 3)
    if session.should_suggest_switch(threshold=suggest_threshold):
        n = session.consecutive_off_tier
        drift_tier = session.drift_tier or tier
        drift_msg = (
            f'[Loaded Dice] Your last {n} prompts were {drift_tier}-tier. '
            f'Consider switching your session model: /dice-switch {drift_tier}'
        )
        messages.append(drift_msg)
        session.mark_drift_suggested()

    session.save()

    analytics = AnalyticsLogger(
        log_dir=os.path.expanduser(state_dir),
        enabled=config.get("analytics", True),
    )
    analytics.log({
        "event": "PromptClassified",
        "prompt_preview": prompt[:120],
        "word_count": len(prompt.split()),
        "tier": tier,
        "confidence": confidence,
        "signals": signals,
        "source": result.get("source"),
        "session_model": session_model,
        "delegated": tier != session_model,
    })

    additional_context = "\n\n".join(messages)
    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": additional_context,
        }
    }
    print(json.dumps(output))


if __name__ == "__main__":
    main()
