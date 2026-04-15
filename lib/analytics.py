import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AnalyticsLogger:
    """Lightweight NDJSON append-only analytics logger."""

    def __init__(self, log_dir: str = "~/.claude/loaded-dice", enabled: bool = True) -> None:
        """
        Initialize the analytics logger.

        Args:
            log_dir: Directory to store analytics logs. Defaults to ~/.claude/loaded-dice
            enabled: Whether logging is enabled. Defaults to True
        """
        self.enabled = enabled
        self.log_dir = Path(log_dir).expanduser()
        self.log_file = self.log_dir / "analytics.ndjson"

    def log(self, event: dict[str, Any]) -> None:
        """
        Log an event to the analytics file.

        Adds a "ts" field with UTC ISO format timestamp and appends as a JSON line.
        Creates the log directory if needed. Silently ignores OSError.

        Args:
            event: Dictionary of event data to log
        """
        if not self.enabled:
            return

        try:
            # Create directory if it doesn't exist
            self.log_dir.mkdir(parents=True, exist_ok=True)

            # Add timestamp in UTC ISO format
            event_with_ts = {
                "ts": datetime.now(timezone.utc).isoformat(),
                **event,
            }

            # Append as NDJSON line
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event_with_ts) + "\n")
        except OSError:
            # Silently ignore file system errors
            pass

    def read_all(self) -> list[dict[str, Any]]:
        """
        Read all events from the analytics log file.

        Returns:
            List of event dictionaries. Returns empty list on error or missing file.
        """
        try:
            if not self.log_file.exists():
                return []

            events = []
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        events.append(json.loads(line))
            return events
        except (OSError, json.JSONDecodeError):
            return []
