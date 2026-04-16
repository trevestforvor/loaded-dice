"""Default pattern tables and tier-matching logic for the classification engine."""

import re
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default patterns
# ---------------------------------------------------------------------------

DEFAULT_PATTERNS: dict[str, list[str]] = {
    "haiku": [
        r"^what (is|are|does) ",
        r"^how (do|does|to) ",
        r"^(show|list|get) .{0,30}$",
        r"\b(format|lint|prettify|beautify)\b",
        r"\bgit (status|log|diff|add|commit|push|pull)\b",
        r"\b(json|yaml|yml)\b.{0,20}$",
        r"\bregex\b",
        r"\bsyntax (for|of)\b",
        r"\b(grep|glob|search|find)\b.{0,40}(file|usage|instance|codebase|comment|todo|for\b)",
        r"\bread\b.{0,20}\b(file|contents?|readme|changelog|makefile|package)\b",
        r"\bsummar(y|ize)\b.{0,20}\b(file|function|class)\b",
    ],
    "sonnet": [
        r"\b(write|add|create|implement)\b.{0,30}\b(test|spec)\b",
        r"\b(fix|debug)\b.{0,30}\b(bug|error|issue)\b",
        r"\brefactor\b.{0,30}(function|method|class|view)\b",
        r"\b(review|check)\b.{0,20}\b(code|function|method|PR)\b",
        r"\b(document|docstring|comment)\b",
        r"\b(build|implement|create)\b.{0,30}(component|view|screen|endpoint)",
        r"\bauditor?\b",
    ],
    "opus": [
        r"\b(architect|architecture|design pattern|system design)\b",
        r"\b(across|multiple|all) (files?|components?|modules?)\b",
        r"\brefactor.{0,20}(codebase|project|entire)\b",
        r"\b(trade-?offs?|compare|pros? (and|&) cons?)\b",
        r"\b(analyze|evaluate|assess).{0,30}(option|approach|strateg|trade-?off)",
        r"\boptimiz(e|ation).{0,20}(performance|speed|memory)\b",
        r"\b(plan|planning|roadmap)\b.{0,30}(implement|migration|phase|rollout|payment|system)\b",
        r"\b(security|vulnerab|audit)\b.{0,30}(review|scan|check|vulnerab|api|flow|code)\b",
        r"\bredesign\b.{0,20}(navigation|architecture|system|flow)\b",
        r"\b(debug|diagnos).{0,30}(race|deadlock|leak|crash)\b",
        r"\b(cross-?domain|end-?to-?end|full-?stack)\b",
    ],
}

# Checked in this order; first tier with signals wins.
TIER_PRIORITY: list[str] = ["opus", "sonnet", "haiku"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def compile_patterns(patterns: list[str]) -> list[re.Pattern]:
    """Compile a list of regex pattern strings.

    Bad patterns are skipped with a warning rather than raising.
    All patterns are compiled with re.IGNORECASE.
    """
    compiled: list[re.Pattern] = []
    for pat in patterns:
        try:
            compiled.append(re.compile(pat, re.IGNORECASE))
        except re.error as exc:
            logger.warning("Skipping bad pattern %r: %s", pat, exc)
    return compiled


# ---------------------------------------------------------------------------
# Tier matching
# ---------------------------------------------------------------------------

def match_tier(
    prompt: str,
    compiled: dict[str, list[re.Pattern]],
    max_word_counts: dict[str, int] | None = None,
    force_min_word_counts: dict[str, int] | None = None,
) -> dict:
    """Match *prompt* against compiled tier patterns and return a result dict.

    Result keys:
        tier        – winning tier name, or None
        confidence  – float in {0.5, 0.7, 0.9, 1.0}
        signals     – list of matched pattern strings for the winning tier

    Args:
        prompt              – the raw user prompt text
        compiled            – {tier: [compiled regex, ...]}
        max_word_counts     – skip a tier when prompt exceeds this word count
        force_min_word_counts – immediately return that tier when prompt meets
                               or exceeds the given word count (checked in
                               TIER_PRIORITY order)
    """
    word_count = len(prompt.split())

    # 1. force_min_word_count escalation — return immediately on first match
    if force_min_word_counts:
        for tier in TIER_PRIORITY:
            threshold = force_min_word_counts.get(tier)
            if threshold is not None and word_count >= threshold:
                return {"tier": tier, "confidence": 0.7, "signals": []}

    # 2. Collect signals per tier, respecting max_word_count guards
    tier_signals: dict[str, list[str]] = {}
    for tier in TIER_PRIORITY:
        if max_word_counts and word_count > max_word_counts.get(tier, float("inf")):
            continue
        patterns = compiled.get(tier, [])
        matched = [pat.pattern for pat in patterns if pat.search(prompt)]
        if matched:
            tier_signals[tier] = matched

    # 3. Find highest-priority tier with signals (opus → sonnet → haiku)
    for tier in TIER_PRIORITY:
        signals = tier_signals.get(tier)
        if signals:
            n = len(signals)
            confidence = 1.0 if n >= 3 else (0.9 if n == 2 else 0.7)
            return {"tier": tier, "confidence": confidence, "signals": signals}

    # 4. No match
    return {"tier": None, "confidence": 0.5, "signals": []}
