"""Benchmark test that measures classification accuracy against labeled prompts.

The accuracy percentage is printed as the LAST line of output for autoresearch
metric parsing: "ACCURACY: XX.X%"
"""

import sys
import os

# Ensure lib/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.classifier import classify
from lib.config import DEFAULT_CONFIG
from lib.session import SessionState
from tests.benchmark_fixture import BENCHMARK_PROMPTS


def _make_config():
    """Default config with LLM fallback disabled (deterministic benchmark)."""
    import copy
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg["llm_fallback"] = False
    return cfg


def _fresh_session():
    """Session with no momentum (isolate rule-based classification)."""
    import tempfile
    tmpdir = tempfile.mkdtemp()
    return SessionState(state_dir=tmpdir, timeout_minutes=0)


def test_benchmark_accuracy():
    """Run all benchmark prompts and assert accuracy is tracked.

    This test always passes — it's a measurement, not a gate.
    The accuracy % is printed for autoresearch metric parsing.
    """
    config = _make_config()
    correct = 0
    total = len(BENCHMARK_PROMPTS)
    mismatches: list[tuple[str, str, str, str]] = []

    for prompt, expected, category in BENCHMARK_PROMPTS:
        session = _fresh_session()
        result = classify(prompt, config, session)
        actual = result["tier"]

        if actual == expected:
            correct += 1
        else:
            mismatches.append((prompt, expected, actual, category))

    accuracy = (correct / total) * 100

    # Print category breakdown for mismatches
    if mismatches:
        print(f"\n--- MISMATCHES ({len(mismatches)}/{total}) ---")
        by_category: dict[str, list] = {}
        for prompt, expected, actual, cat in mismatches:
            by_category.setdefault(cat, []).append((prompt, expected, actual))

        for cat, items in sorted(by_category.items()):
            print(f"\n  [{cat}]")
            for prompt, expected, actual in items:
                prompt_short = prompt[:60] + "..." if len(prompt) > 60 else prompt
                print(f"    {expected} -> {actual}: {prompt_short}")

    # Final accuracy line — autoresearch parses this
    print(f"\nACCURACY: {accuracy:.1f}%")

    # This test measures, it doesn't gate. Always passes.
    assert True


def test_benchmark_per_tier_accuracy():
    """Report per-tier precision and recall."""
    config = _make_config()
    tier_stats: dict[str, dict[str, int]] = {
        "haiku": {"tp": 0, "fp": 0, "fn": 0},
        "sonnet": {"tp": 0, "fp": 0, "fn": 0},
        "opus": {"tp": 0, "fp": 0, "fn": 0},
    }

    for prompt, expected, _category in BENCHMARK_PROMPTS:
        session = _fresh_session()
        result = classify(prompt, config, session)
        actual = result["tier"]

        if actual == expected:
            tier_stats[expected]["tp"] += 1
        else:
            tier_stats[expected]["fn"] += 1
            if actual in tier_stats:
                tier_stats[actual]["fp"] += 1

    print("\n--- PER-TIER METRICS ---")
    for tier in ["haiku", "sonnet", "opus"]:
        s = tier_stats[tier]
        precision = s["tp"] / (s["tp"] + s["fp"]) if (s["tp"] + s["fp"]) > 0 else 0
        recall = s["tp"] / (s["tp"] + s["fn"]) if (s["tp"] + s["fn"]) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        print(f"  {tier:6s}: P={precision:.2f} R={recall:.2f} F1={f1:.2f} (TP={s['tp']} FP={s['fp']} FN={s['fn']})")

    assert True
