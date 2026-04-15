#!/usr/bin/env python3
"""PreToolUse hook (Agent) — validate subagent model selection against prompt classification."""

import json
import os
import sys

_PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, _PLUGIN_ROOT)

from lib.config import load_config
from lib.session import SessionState
from lib.classifier import classify
from lib.analytics import AnalyticsLogger


def _normalize_model_to_tier(model_str: str) -> str | None:
    """Extract tier from a model string. Returns None if not recognizable."""
    if not model_str:
        return None
    low = model_str.lower()
    for tier in ("haiku", "sonnet", "opus"):
        if tier in low:
            return tier
    return None


def main() -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    specified_model_raw = tool_input.get("model", "")
    sub_prompt = tool_input.get("prompt", "")

    cwd = os.getcwd()
    config = load_config(
        global_path=os.path.expanduser("~/.claude/loaded-dice.json"),
        project_path=os.path.join(cwd, ".claude", "loaded-dice.json"),
    )

    state_dir = os.environ.get("LOADED_DICE_STATE_DIR", "~/.claude/loaded-dice")
    session = SessionState(state_dir=state_dir, timeout_minutes=config.get("session_timeout_minutes", 30))

    if os.environ.get("LOADED_DICE_DISABLE_LLM"):
        config["llm_fallback"] = False

    result = classify(sub_prompt, config, session)
    recommended_tier = result["tier"]
    signals = result["signals"]
    signals_str = ", ".join(signals) if signals else "none"

    specified_tier = _normalize_model_to_tier(specified_model_raw)

    analytics = AnalyticsLogger(
        log_dir=os.path.expanduser(state_dir),
        enabled=config.get("analytics", True),
    )

    feedback = ""

    if not specified_model_raw or specified_tier is None:
        feedback = (
            f'[Loaded Dice] No model specified for this subagent. '
            f'Recommended: model: "{recommended_tier}" (signals: {signals_str}). '
            f'Always specify a model parameter when dispatching agents.'
        )
    elif specified_tier != recommended_tier:
        feedback = (
            f'[Loaded Dice] Routing note: this subagent task was dispatched to {specified_tier} '
            f'but classified as {recommended_tier}-tier (signals: {signals_str}). '
            f'For future dispatches, use model: "{recommended_tier}" for this type of task.'
        )
    # else: match — silent allow, no feedback

    analytics.log({
        "event": "SubagentRouting",
        "specified_model": specified_model_raw,
        "specified_tier": specified_tier,
        "recommended_tier": recommended_tier,
        "signals": signals,
        "mismatch": specified_tier != recommended_tier if specified_tier else None,
    })

    if feedback:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": feedback,
            }
        }
        print(json.dumps(output))
    # NEVER set permissionDecision — always allow through


if __name__ == "__main__":
    main()
