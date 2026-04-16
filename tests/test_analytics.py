"""Tests for the analytics logger including log rotation."""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.analytics import AnalyticsLogger, _MAX_LOG_BYTES


class TestAnalyticsLogger:
    def _make_logger(self, tmpdir: str, enabled: bool = True) -> AnalyticsLogger:
        return AnalyticsLogger(log_dir=tmpdir, enabled=enabled)

    def test_log_creates_file(self):
        with tempfile.TemporaryDirectory() as d:
            logger = self._make_logger(d)
            logger.log({"event": "test"})
            assert (logger.log_file).exists()

    def test_log_appends_ndjson(self):
        with tempfile.TemporaryDirectory() as d:
            logger = self._make_logger(d)
            logger.log({"event": "first"})
            logger.log({"event": "second"})
            lines = logger.log_file.read_text().strip().split("\n")
            assert len(lines) == 2
            assert json.loads(lines[0])["event"] == "first"
            assert json.loads(lines[1])["event"] == "second"

    def test_log_adds_timestamp(self):
        with tempfile.TemporaryDirectory() as d:
            logger = self._make_logger(d)
            logger.log({"event": "ts_check"})
            data = json.loads(logger.log_file.read_text().strip())
            assert "ts" in data
            assert data["ts"].endswith("+00:00")

    def test_disabled_logger_does_not_write(self):
        with tempfile.TemporaryDirectory() as d:
            logger = self._make_logger(d, enabled=False)
            logger.log({"event": "should_not_appear"})
            assert not logger.log_file.exists()

    def test_read_all_returns_events(self):
        with tempfile.TemporaryDirectory() as d:
            logger = self._make_logger(d)
            logger.log({"event": "a"})
            logger.log({"event": "b"})
            events = logger.read_all()
            assert len(events) == 2
            assert events[0]["event"] == "a"

    def test_read_all_empty_file(self):
        with tempfile.TemporaryDirectory() as d:
            logger = self._make_logger(d)
            assert logger.read_all() == []

    def test_log_rotation_triggers_at_max_size(self):
        with tempfile.TemporaryDirectory() as d:
            logger = self._make_logger(d)
            # Write enough data to exceed _MAX_LOG_BYTES
            big_event = {"event": "x", "data": "A" * 1000}
            # Each line is ~1070 bytes; need _MAX_LOG_BYTES / 1070 + margin
            lines_needed = (_MAX_LOG_BYTES // 1000) + 50
            for _ in range(lines_needed):
                logger.log(big_event)

            # After rotation, a .1 file should exist
            rotated = logger.log_dir / "analytics.1.ndjson"
            assert rotated.exists()
            # Current log file should be small (post-rotation writes)
            assert logger.log_file.stat().st_size < _MAX_LOG_BYTES

    def test_rotation_keeps_max_files(self):
        with tempfile.TemporaryDirectory() as d:
            logger = self._make_logger(d)
            big_event = {"event": "x", "data": "A" * 1000}
            lines_needed = (_MAX_LOG_BYTES // 1000) + 50
            # Trigger multiple rotations
            for _ in range(lines_needed * 4):
                logger.log(big_event)

            # Should have at most .1 and .2 rotated files
            assert (logger.log_dir / "analytics.1.ndjson").exists()
            assert (logger.log_dir / "analytics.2.ndjson").exists()
            assert not (logger.log_dir / "analytics.3.ndjson").exists()
