"""Session state management for loaded-dice routing hooks.

Tracks conversation flow, drift, and momentum within a single Claude session.
State is persisted to a single JSON file and loaded on each UserPromptSubmit hook.
"""

import json
import os
import re
import time
from typing import Optional


# Pre-compiled follow-up patterns matched at the START of a prompt (case-insensitive).
_FOLLOW_UP_PATTERNS = re.compile(
    r"^(and\b|also\b|what about\b|actually\b|wait\b|yes\b|ok\b|no\b|how about\b|then\b|sure\b|nah\b|yeah\b|nope\b|yep\b)",
    re.IGNORECASE,
)

_MAX_HISTORY = 50
_STATE_FILENAME = "session.json"


class SessionState:
    """Lightweight session state for context-aware model routing."""

    def __init__(self, state_dir: str = "~/.claude/loaded-dice", timeout_minutes: int = 30):
        self._state_dir = os.path.expanduser(state_dir)
        self._timeout_seconds = timeout_minutes * 60
        self._path = os.path.join(self._state_dir, _STATE_FILENAME)

        self._load()

    # ------------------------------------------------------------------
    # Public fields (exposed as plain attributes for easy consumption)
    # ------------------------------------------------------------------

    # These are set in _reset() and _load().

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _reset(self) -> None:
        now = time.time()
        self.conversation_depth: int = 0
        self.consecutive_off_tier: int = 0
        self.drift_tier: Optional[str] = None
        self.drift_suggested: bool = False
        self.tier_history: list[str] = []
        self.last_updated: float = now
        self.session_start: float = now

    def _load(self) -> None:
        if not os.path.exists(self._path):
            self._reset()
            return

        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            self._reset()
            return

        last_updated = data.get("last_updated", 0.0)
        elapsed = time.time() - last_updated

        if elapsed > self._timeout_seconds:
            self._reset()
            return

        self.conversation_depth = int(data.get("conversation_depth", 0))
        self.consecutive_off_tier = int(data.get("consecutive_off_tier", 0))
        self.drift_tier = data.get("drift_tier")  # str or None
        self.drift_suggested = bool(data.get("drift_suggested", False))
        self.tier_history = list(data.get("tier_history", []))
        self.last_updated = float(last_updated)
        self.session_start = float(data.get("session_start", last_updated))

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def record_routing(self, tier: str, session_model: str) -> None:
        """Record a routing decision and update drift tracking."""
        self.conversation_depth += 1
        self.tier_history.append(tier)
        self.last_updated = time.time()

        if tier == session_model:
            # Back on the expected tier — reset drift state.
            self.consecutive_off_tier = 0
            self.drift_tier = None
        else:
            if self.drift_tier == tier:
                # Continuing in the same off-tier direction.
                self.consecutive_off_tier += 1
            else:
                # Direction changed (or first off-tier occurrence).
                self.drift_tier = tier
                self.consecutive_off_tier = 1

    def should_suggest_switch(self, threshold: int = 3) -> bool:
        """Return True if drift has accumulated enough to suggest a model switch."""
        return self.consecutive_off_tier >= threshold and not self.drift_suggested

    def mark_drift_suggested(self) -> None:
        """Record that a drift suggestion has already been shown this session."""
        self.drift_suggested = True

    def get_momentum_tier(self, window: int = 3) -> Optional[str]:
        """Return the tier if the last *window* entries are all the same, else None."""
        if len(self.tier_history) < window:
            return None
        recent = self.tier_history[-window:]
        if len(set(recent)) == 1:
            return recent[0]
        return None

    # Implementation verbs that indicate a real task, not a conversational follow-up.
    # Query verbs (explain, show, check, describe) are excluded — they're
    # compatible with follow-up context ("also, can you explain?").
    _IMPL_VERBS_RE = re.compile(
        r"\b(fix|build|create|implement|add|write|deploy|ship|refactor|redesign|test|review|"
        r"delete|remove|run|update|install|close|start|stop|design|architect|plan|"
        r"analyze|debug|make|set up|move|rename|migrate|optimize|audit|configure|rewrite|rework)\b",
        re.IGNORECASE,
    )

    def is_follow_up(self, prompt: str) -> bool:
        """Return True if prompt looks like a conversational follow-up.

        Criteria:
        - Fewer than 8 words, AND
        - Starts with a recognised follow-up trigger word/phrase,
          AND does not contain an action verb (which means it's a
          task prefixed with a conversational word, not a follow-up).
        - OR is an ultra-short acknowledgement (≤2 words) without action verbs.
        """
        words = prompt.split()
        if len(words) >= 8:
            return False
        stripped = prompt.strip()
        if bool(_FOLLOW_UP_PATTERNS.match(stripped)):
            # "yes" is a follow-up, but "yes please add that feature" is a task
            if self._IMPL_VERBS_RE.search(stripped):
                return False
            return True
        # Ultra-short prompts (≤2 words) without ANY verb (impl or query)
        if len(words) <= 2:
            _any_verb = re.compile(
                r"^(fix|build|create|implement|add|write|deploy|ship|refactor|test|review|"
                r"delete|remove|run|update|install|close|start|stop|design|architect|plan|"
                r"analyze|debug|make|move|rename|migrate|optimize|audit|configure|"
                r"explain|describe|show|list|check|open|read|find|search|get|help)\b",
                re.IGNORECASE,
            )
            if not _any_verb.match(stripped):
                return True
        return False

    def save(self) -> None:
        """Persist state to disk, capping tier_history at 50 entries."""
        os.makedirs(self._state_dir, exist_ok=True)
        data = {
            "conversation_depth": self.conversation_depth,
            "consecutive_off_tier": self.consecutive_off_tier,
            "drift_tier": self.drift_tier,
            "drift_suggested": self.drift_suggested,
            "tier_history": self.tier_history[-_MAX_HISTORY:],
            "last_updated": self.last_updated,
            "session_start": self.session_start,
        }
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
