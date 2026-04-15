#!/usr/bin/env python3
"""Stop hook — emit session summary analytics and clean up state file."""

import os
import sys
import time

_PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, _PLUGIN_ROOT)

from lib.session import SessionState
from lib.analytics import AnalyticsLogger


def main() -> None:
    state_dir = os.environ.get("LOADED_DICE_STATE_DIR", "~/.claude/loaded-dice")
    session = SessionState(state_dir=state_dir)

    if session.conversation_depth == 0:
        sys.exit(0)

    # Calculate tier distribution
    tier_distribution: dict[str, int] = {}
    for t in session.tier_history:
        tier_distribution[t] = tier_distribution.get(t, 0) + 1

    # Calculate session duration
    session_duration = time.time() - session.session_start

    analytics = AnalyticsLogger(log_dir=os.path.expanduser(state_dir), enabled=True)
    analytics.log({
        "event": "SessionSummary",
        "conversation_depth": session.conversation_depth,
        "tier_distribution": tier_distribution,
        "session_duration_seconds": round(session_duration, 1),
        "drift_tier": session.drift_tier,
        "drift_suggested": session.drift_suggested,
    })

    # Cleanup state file
    state_path = os.path.join(os.path.expanduser(state_dir), "session.json")
    try:
        os.remove(state_path)
    except OSError:
        pass


if __name__ == "__main__":
    main()
