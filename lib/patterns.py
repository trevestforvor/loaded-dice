"""Default pattern tables and tier-matching logic for the classification engine."""

import re
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default patterns
# ---------------------------------------------------------------------------

DEFAULT_PATTERNS: dict[str, list[str]] = {
    "haiku": [
        # Questions — factual lookups
        r"^what (is|are|does|did|was|were|happened|changed)\b",
        r"^how (do|does|to|did|can|should) ",
        r"^why (is|are|does|do|did|was|were|isn't|aren't|doesn't|won't|can't)\b",
        r"^(does|is|are|did|will|should|do) (it|this|that|the|we|I|you)\b.{0,10}\b(need|have|want|require|supposed)\b",
        r"^(does|is|are|did|will|should) (it|this|that|the|we|I|you)\b",
        r"^(can|do) (you|we|I)\b.{0,10}\b(show|tell|explain|check|see|look|find|get|read|verify|confirm)\b",
        r"^where (is|are|did|do|does) ",
        r"^(show|list|get) .{0,30}$",
        # Formatting / linting
        r"\b(format|lint|prettify|beautify)\b",
        # Git
        r"\bgit (status|log|diff|add|commit|push|pull|branch|stash|rebase|cherry-?pick)\b",
        # Data formats
        r"\b(json|yaml|yml|csv|xml|plist)\b.{0,20}$",
        r"\bregex\b",
        r"\bsyntax (for|of)\b",
        # Search / lookup
        r"\b(grep|glob|search|find)\b.{0,40}(file|usage|instance|codebase|comment|todo|for\b)",
        r"\bread\b.{0,20}\b(file|contents?|readme|changelog|makefile|package)\b",
        r"\bsummar(y|ize)\b.{0,20}\b(file|function|class)\b",
        # Navigation / location
        r"\bwhere.{0,20}(put|find|located|defined|declared|import)\b",
        r"\b(look at|open|check)\b.{0,10}\b(the|this|that)\b.{0,20}$",
        r"\b(take me|go to|navigate|cd|switch to)\b.{0,60}(directory|folder|dir|repo|project)\b",
        # Confirmation / clarification
        r"\bwhat.{0,5}(that|this) mean\b",
        r"\bexplain\b.{0,20}(this|that|the|error|warning)\b",
    ],
    "sonnet": [
        # Testing
        r"\b(write|add|create|implement)\b.{0,30}\b(test|spec)\b",
        # Bug fixing
        r"\b(fix|debug|solve|resolve)\b.{0,30}\b(bug|error|issue|problem|crash|warning)\b",
        r"\b(fix|debug|solve)\b.{0,10}(this|that|the|it)\b",
        # Refactoring (single scope)
        r"\brefactor\b.{0,30}(function|method|class|view|module)\b",
        # Code review
        r"\b(review|check)\b.{0,20}\b(code|function|method|PR|pull request)\b",
        # Documentation
        r"\b(document|docstring|comment|annotate)\b",
        # Implementation (single feature)
        r"\b(build|implement|create|add|make|set up|setup)\b.{0,30}(component|view|screen|endpoint|button|modal|feature|page|form|field|handler|function|method|api|route)",
        r"\bauditor?\b",
        # Update / modify (single scope)
        r"\b(update|change|modify|rename|move)\b.{0,20}\b(the|this|that|a|an)\b",
        # Natural language implementation requests
        r"\b(can you|could you|please|help me|I need to|let's|let me)\b.{0,30}\b(add|fix|build|create|implement|write|make|update)\b",
    ],
    "opus": [
        # Architecture / design (require design-intent context, not just mentions)
        r"\b(architect|design pattern|system design)\b",
        r"\barchitecture\b.{0,20}\b(for|of|review|design|plan|decision)\b",
        # Multi-file / cross-cutting
        r"\b(across|multiple|all) (files?|components?|modules?)\b",
        r"\brefactor.{0,20}(codebase|project|entire)\b",
        # Analysis / trade-offs (require analytical framing, not bare keywords)
        r"\b(trade-?offs?|pros? (and|&) cons?)\b.{0,30}\b(of|between|for|vs)\b",
        r"\bcompare\b.{0,20}\b(vs\.?|versus|between)\b",
        r"\b(analyze|evaluate|assess).{0,30}(option|approach|strateg|trade-?off|why|how|performance|bottleneck)",
        # Performance optimization
        r"\boptimiz(e|ation).{0,20}(performance|speed|memory)\b",
        # Planning
        r"\b(plan|planning|roadmap)\b.{0,30}(implement|migration|phase|rollout|payment|system)\b",
        # Security
        r"\b(security|vulnerab|audit)\b.{0,30}(review|scan|check|vulnerab|api|flow|code)\b",
        # Design (complex scope)
        r"\bredesign\b.{0,20}(navigation|architecture|system|flow)\b",
        r"\bdesign\b.{0,30}\b(layer|schema|model).{0,30}\b(with|and|relationship|migration)\b",
        # Complex debugging (race conditions, deadlocks, leaks — not simple crashes)
        r"\b(debug|diagnos).{0,30}(race condition|deadlock|memory leak|retain cycle)\b",
        # Cross-domain
        r"\b(cross-?domain|end-?to-?end|full-?stack)\b",
        # Whole-project scope
        r"\b(entire|whole|across the) (app|application|project|codebase)\b",
        r"\b(update|change|modify|handle|manage) .{0,10}(all|every) .{0,20}(screen|view|page|endpoint|module|service)s?\b",
        r"\bacross all\b.{0,20}(screen|view|page|endpoint|module|service)s?\b",
        r"\bstructure\b.{0,30}\b(app|application|project|codebase)\b",
        # Strategy / high-level
        r"\b(strateg(y|ic|ize)|approach)\b.{0,20}\b(for|to|about)\b",
        r"\bhow should (we|I|the)\b.{0,30}\b(structure|organize|handle|approach)\b",
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

    # 2b. Question-form override: when haiku matched a question pattern,
    # demote competing single-signal sonnet/opus matches.
    # Two cases:
    #   - Generic questions: "what is a design pattern?" (indefinite article)
    #   - Deliberation questions: "do we need to...", "should we..."
    # Specific analysis questions ("what is THE architecture") keep their
    # opus routing when opus has strong (2+) signals.
    haiku_signals = tier_signals.get("haiku", [])
    _generic_question_re = re.compile(
        r"^(what|how|where|when|why|which|who)\b.{0,10}\b(is|are|does|do|did)\b.{0,10}\b(a|an)\b",
        re.IGNORECASE,
    )
    _deliberation_re = re.compile(
        r"^(do|does|should|would|could|can|will) (we|I|you|it|this)\b.{0,10}\b(need|have|want|require|supposed|still|even|really|actually)\b",
        re.IGNORECASE,
    )
    is_question_override = (
        bool(_generic_question_re.match(prompt.strip()))
        or bool(_deliberation_re.match(prompt.strip()))
    )
    if is_question_override and haiku_signals:
        for upper_tier in ("opus", "sonnet"):
            upper = tier_signals.get(upper_tier, [])
            if len(upper) < 2:
                tier_signals.pop(upper_tier, None)

    # 3. Find highest-priority tier with signals (opus → sonnet → haiku)
    for tier in TIER_PRIORITY:
        signals = tier_signals.get(tier)
        if signals:
            n = len(signals)
            confidence = 1.0 if n >= 3 else (0.9 if n == 2 else 0.7)
            return {"tier": tier, "confidence": confidence, "signals": signals}

    # 4. No match
    return {"tier": None, "confidence": 0.5, "signals": []}
