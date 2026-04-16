"""Three-layer classification pipeline for loaded-dice routing."""

import logging
import re
from typing import Any, Optional

from lib.patterns import DEFAULT_PATTERNS, compile_patterns, match_tier
from lib.config import DEFAULT_CONFIG
from lib.session import SessionState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TIER_MODELS: dict[str, str] = {
    "haiku": "haiku",
    "sonnet": "sonnet",
    "opus": "opus",
}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_patterns(config: dict[str, Any]) -> dict[str, list[str]]:
    """Merge DEFAULT_PATTERNS with per-tier config overrides.

    For "extend" mode:
        start with defaults, add config patterns, convert config keywords to
        \\bkeyword\\b patterns, then remove specified patterns/keywords.
    For "replace" mode:
        use config patterns only (keywords still converted, removes still applied).
    """
    tiers_cfg = config.get("tiers", {})
    result: dict[str, list[str]] = {}

    all_tiers = set(DEFAULT_PATTERNS.keys()) | set(tiers_cfg.keys())

    for tier in all_tiers:
        tier_cfg = tiers_cfg.get(tier, {})
        mode = tier_cfg.get("mode", "extend")

        if mode == "replace":
            base: list[str] = []
        else:
            base = list(DEFAULT_PATTERNS.get(tier, []))

        # Add explicit patterns from config
        for pat in tier_cfg.get("patterns", []):
            if pat not in base:
                base.append(pat)

        # Convert keywords to \bkeyword\b patterns
        for kw in tier_cfg.get("keywords", []):
            pat = rf"\b{re.escape(kw)}\b"
            if pat not in base:
                base.append(pat)

        # Remove patterns explicitly listed for removal
        remove_patterns = set(tier_cfg.get("remove_patterns", []))
        # Also build removal set for keywords
        remove_kw_patterns = {rf"\b{re.escape(k)}\b" for k in tier_cfg.get("remove_keywords", [])}
        remove_all = remove_patterns | remove_kw_patterns

        result[tier] = [p for p in base if p not in remove_all]

    return result


def _get_word_count_guards(config: dict[str, Any]) -> tuple[dict[str, int], dict[str, int]]:
    """Extract max_word_count and force_min_word_count dicts from tier configs."""
    tiers_cfg = config.get("tiers", {})
    max_wc: dict[str, int] = {}
    force_min_wc: dict[str, int] = {}

    for tier, tier_cfg in tiers_cfg.items():
        if "max_word_count" in tier_cfg:
            max_wc[tier] = tier_cfg["max_word_count"]
        if "force_min_word_count" in tier_cfg:
            force_min_wc[tier] = tier_cfg["force_min_word_count"]

    return max_wc, force_min_wc


def _llm_fallback(prompt: str, config: dict[str, Any]) -> Optional[dict]:
    """Layer 3 — LLM classification via claude-haiku.

    Returns a dict {tier, confidence, signals} on success, None on any failure.
    Only fires if config["llm_fallback"] is True.
    """
    if not config.get("llm_fallback", False):
        return None

    try:
        import anthropic  # type: ignore
    except ImportError:
        logger.debug("anthropic package not installed; skipping LLM fallback")
        return None

    try:
        import json

        client = anthropic.Anthropic()
        classification_prompt = (
            "Classify the following user prompt into one of three tiers: "
            "haiku (simple/quick tasks), sonnet (moderate complexity), "
            "opus (complex/architectural tasks).\n\n"
            f'User prompt: "{prompt}"\n\n'
            'Respond ONLY with valid JSON in this exact format: '
            '{"tier": "<haiku|sonnet|opus>", "confidence": <0.0-1.0>, "signals": ["<reason1>"]}'
        )

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            messages=[{"role": "user", "content": classification_prompt}],
        )

        text = message.content[0].text.strip()
        data = json.loads(text)

        tier = data.get("tier")
        if tier not in TIER_MODELS:
            return None

        return {
            "tier": tier,
            "confidence": float(data.get("confidence", 0.7)),
            "signals": data.get("signals", []),
        }

    except Exception as exc:
        logger.debug("LLM fallback failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify(prompt: str, config: dict[str, Any], session: SessionState) -> dict:
    """Full three-layer classification pipeline.

    Returns:
        dict with keys: tier, confidence, signals, source
        source is one of: "rules", "context", "llm", "default"
    """
    threshold = config.get("confidence_threshold", 0.7)

    # ------------------------------------------------------------------
    # Layer 1 — rule-based matching
    # ------------------------------------------------------------------
    patterns = _build_patterns(config)
    max_wc, force_min_wc = _get_word_count_guards(config)
    compiled = {tier: compile_patterns(pats) for tier, pats in patterns.items()}

    rule_result = match_tier(
        prompt,
        compiled,
        max_word_counts=max_wc or None,
        force_min_word_counts=force_min_wc or None,
    )

    tier: Optional[str] = rule_result["tier"]
    confidence: float = rule_result["confidence"]
    signals: list = rule_result["signals"]
    source = "rules"

    # Override force_min_word_count escalation when a lower tier has
    # strong signals. Long prompts that clearly match haiku/sonnet
    # patterns shouldn't be forced to opus just by word count.
    if not signals and confidence == 0.7 and tier is not None:
        # This was a force_min_word_count match (no signals, 0.7 confidence).
        # Check if any lower-priority tier has actual pattern matches.
        lower_result = match_tier(prompt, compiled, max_word_counts=max_wc)
        if lower_result["tier"] is not None and lower_result["confidence"] >= threshold:
            tier = lower_result["tier"]
            confidence = lower_result["confidence"]
            signals = lower_result["signals"]

    # ------------------------------------------------------------------
    # Layer 2 — context / momentum
    # ------------------------------------------------------------------
    momentum_tier = session.get_momentum_tier()
    is_follow_up = session.is_follow_up(prompt)

    # "Strong signal" means rules matched with >= threshold confidence
    has_strong_signal = tier is not None and confidence >= threshold

    if is_follow_up and momentum_tier is not None and not has_strong_signal:
        # Inherit momentum tier
        tier = momentum_tier
        confidence = 0.75
        signals = []
        source = "context"
    elif tier is not None and momentum_tier == tier:
        # Momentum agrees — small confidence boost
        confidence = min(1.0, confidence + 0.1)

    # ------------------------------------------------------------------
    # Layer 3 — LLM fallback
    # ------------------------------------------------------------------
    if confidence < threshold:
        llm_result = _llm_fallback(prompt, config)
        if llm_result is not None:
            tier = llm_result["tier"]
            confidence = llm_result["confidence"]
            signals = llm_result["signals"]
            source = "llm"

    # ------------------------------------------------------------------
    # Final fallback — default_tier
    # ------------------------------------------------------------------
    if tier is None or confidence < threshold:
        tier = config.get("default_tier", "sonnet")
        confidence = 0.6
        signals = []
        source = "default"

    return {
        "tier": tier,
        "confidence": confidence,
        "signals": signals,
        "source": source,
    }
