"""Tier cost weights and savings calculations for loaded-dice metrics."""

from __future__ import annotations

# Relative per-token cost ratios (April 2026 Anthropic API pricing).
# Input and output ratios are both 1:3:5 across haiku/sonnet/opus.
TIER_WEIGHTS: dict[str, int] = {
    "haiku": 1,
    "sonnet": 3,
    "opus": 5,
}


def tier_weight(tier: str) -> int | None:
    """Return the cost weight for a tier, or None if unknown."""
    return TIER_WEIGHTS.get(tier)


def classify_direction(session_tier: str, routed_tier: str) -> str | None:
    """Classify a routing event as 'downward', 'upward', or None (same tier).

    Returns:
        'downward' if routed to a cheaper tier (savings)
        'upward' if routed to a more expensive tier (complexity match)
        None if same tier (no routing)
    """
    session_w = TIER_WEIGHTS.get(session_tier)
    routed_w = TIER_WEIGHTS.get(routed_tier)
    if session_w is None or routed_w is None or session_w == routed_w:
        return None
    return "downward" if routed_w < session_w else "upward"


def compute_savings(events: list[dict]) -> dict:
    """Compute cost savings metrics from PromptClassified analytics events.

    Args:
        events: List of PromptClassified event dicts. Each must have
                'tier', 'session_model', and 'word_count' keys.
                Events missing 'word_count' are skipped.

    Returns:
        dict with keys:
            overall_savings_pct: float — net savings across all events.
                Can be negative when upward routing dominates (more cost
                than running everything at the session tier).
            downward: list of dicts — per-direction savings for cheaper routing
            complexity_matches: list of dicts — per-direction counts for upward routing
    """
    down_prompts: dict[tuple[str, str], int] = {}
    down_words: dict[tuple[str, str], int] = {}
    down_savings_weight: dict[tuple[str, str], float] = {}
    down_baseline_weight: dict[tuple[str, str], float] = {}

    up_prompts: dict[tuple[str, str], int] = {}

    total_actual = 0.0
    total_baseline = 0.0

    for ev in events:
        wc = ev.get("word_count")
        if wc is None:
            continue

        session_tier = ev.get("session_model", "")
        routed_tier = ev.get("tier", "")
        s_w = TIER_WEIGHTS.get(session_tier)
        r_w = TIER_WEIGHTS.get(routed_tier)

        if s_w is None or r_w is None:
            continue

        total_actual += r_w * wc
        total_baseline += s_w * wc

        direction = classify_direction(session_tier, routed_tier)
        if direction == "downward":
            key = (session_tier, routed_tier)
            down_prompts[key] = down_prompts.get(key, 0) + 1
            down_words[key] = down_words.get(key, 0) + wc
            down_savings_weight[key] = down_savings_weight.get(key, 0.0) + (s_w - r_w) * wc
            down_baseline_weight[key] = down_baseline_weight.get(key, 0.0) + s_w * wc
        elif direction == "upward":
            key = (session_tier, routed_tier)
            up_prompts[key] = up_prompts.get(key, 0) + 1

    _LABEL = {"opus": "Opus", "sonnet": "Sonnet", "haiku": "Haiku"}
    downward = []
    for key in sorted(down_prompts.keys()):
        s_tier, r_tier = key
        baseline = down_baseline_weight[key]
        pct = (down_savings_weight[key] / baseline * 100) if baseline else 0.0
        downward.append({
            "direction": f"{_LABEL.get(s_tier, s_tier)} -> {_LABEL.get(r_tier, r_tier)}",
            "prompts": down_prompts[key],
            "words": down_words[key],
            "savings_pct": round(pct, 1),
        })

    complexity_matches = []
    for key in sorted(up_prompts.keys()):
        s_tier, r_tier = key
        complexity_matches.append({
            "direction": f"{_LABEL.get(s_tier, s_tier)} -> {_LABEL.get(r_tier, r_tier)}",
            "prompts": up_prompts[key],
        })

    overall = round((1 - total_actual / total_baseline) * 100, 1) if total_baseline else 0.0

    return {
        "overall_savings_pct": overall,
        "downward": downward,
        "complexity_matches": complexity_matches,
    }
