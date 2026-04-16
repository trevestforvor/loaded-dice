import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Maximum log file size before rotation (1 MB)
_MAX_LOG_BYTES = 1_000_000
# Number of rotated log files to keep
_MAX_ROTATED = 2


class AnalyticsLogger:
    """Lightweight NDJSON append-only analytics logger with rotation."""

    def __init__(self, log_dir: str = "~/.claude/loaded-dice", enabled: bool = True) -> None:
        self.enabled = enabled
        self.log_dir = Path(log_dir).expanduser()
        self.log_file = self.log_dir / "analytics.ndjson"

    def _rotate_if_needed(self) -> None:
        """Rotate log file if it exceeds _MAX_LOG_BYTES."""
        try:
            if not self.log_file.exists():
                return
            if self.log_file.stat().st_size < _MAX_LOG_BYTES:
                return

            # Shift existing rotated files: .2 → delete, .1 → .2
            for i in range(_MAX_ROTATED, 0, -1):
                src = self.log_dir / f"analytics.{i}.ndjson"
                if i == _MAX_ROTATED:
                    src.unlink(missing_ok=True)
                elif src.exists():
                    dst = self.log_dir / f"analytics.{i + 1}.ndjson"
                    src.rename(dst)

            # Current → .1
            rotated = self.log_dir / "analytics.1.ndjson"
            self.log_file.rename(rotated)
        except OSError:
            pass

    def log(self, event: dict[str, Any]) -> None:
        """Append an event as a JSON line with UTC timestamp."""
        if not self.enabled:
            return

        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self._rotate_if_needed()

            event_with_ts = {
                "ts": datetime.now(timezone.utc).isoformat(),
                **event,
            }

            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event_with_ts) + "\n")
        except OSError:
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
