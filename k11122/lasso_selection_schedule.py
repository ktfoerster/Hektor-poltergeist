"""Deterministic, policy-space-preserving K11122 witness-selection schedule.

This module selects only which independently justified failing-walk clauses
to learn. It never constrains routing selectors or packet state.
"""


def validate_selection(strategy, walker, hybrid_every):
    if strategy not in ("first", "short-diverse", "hybrid"):
        raise ValueError("unknown witness selection")
    if strategy != "first" and walker != "cpp":
        raise ValueError("short-diverse and hybrid require the C++ walker")
    if type(hybrid_every) is not int or not 2 <= hybrid_every <= 1024:
        raise ValueError("hybrid_every must be an integer in [2,1024]")


def effective_selection(strategy, hybrid_every, global_model_index):
    """Return the scanner mode for a 1-based, globally counted SAT assignment."""
    if type(global_model_index) is not int or global_model_index <= 0:
        raise ValueError("global SAT model index must be positive")
    if strategy not in ("first", "short-diverse", "hybrid"):
        raise ValueError("unknown witness selection")
    if type(hybrid_every) is not int or hybrid_every < 2 or hybrid_every > 1024:
        raise ValueError("invalid hybrid interval")
    if strategy != "hybrid":
        return strategy
    return "short-diverse" if global_model_index % hybrid_every == 0 else "first"


def inherited_model_offset(previous):
    """Check previous *audited* checkpoint progress before carrying its clock.

    Do not call this function on unverified metadata. A resumed search has
    no restored backend-internal learning; it only preserves the deterministic
    model-selection clock and independently checked CNF constraints.
    """
    if not isinstance(previous, dict):
        raise ValueError("invalid prior manifest")
    progress = previous.get("progress", {})
    if not isinstance(progress, dict):
        raise ValueError("invalid prior progress")
    local = progress.get("raw_models", 0)
    offset = progress.get("selection_model_offset", 0)
    if (type(local) is not int or local < 0 or
            type(offset) is not int or offset < 0):
        raise ValueError("malformed prior model clock")
    return local + offset
