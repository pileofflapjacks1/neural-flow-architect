"""Session trust metrics — was the co-pilot actually helpful?"""

from __future__ import annotations

from typing import Any


def compute_trust_metrics(
    *,
    actions_count: int = 0,
    undos_count: int = 0,
    feedback_history: list[dict[str, Any]] | None = None,
    denied_tools: list[str] | None = None,
    failsafe_active_seconds: float = 0.0,
    session_uptime_sec: float = 0.0,
) -> dict[str, Any]:
    """
    Lightweight trust score in [0, 1].

    Higher is better. Purely local analytics — not a clinical metric.
    """
    feedback_history = feedback_history or []
    denied_tools = denied_tools or []

    helpful = sum(1 for f in feedback_history if f.get("rating") == "helpful")
    unhelpful = sum(1 for f in feedback_history if f.get("rating") == "unhelpful")
    never = sum(1 for f in feedback_history if f.get("rating") == "never")
    rated = helpful + unhelpful + never

    undo_rate = undos_count / max(actions_count, 1)
    # Undo rate of 0 → 1.0; 50%+ undos → ~0
    undo_score = max(0.0, 1.0 - min(1.0, undo_rate * 2.0))

    if rated == 0:
        feedback_score = 0.6  # neutral prior until user rates
    else:
        feedback_score = (helpful + 0.25 * max(0, rated - never - unhelpful)) / max(rated, 1)
        feedback_score = max(0.0, min(1.0, helpful / rated))

    failsafe_penalty = 0.0
    if session_uptime_sec > 0 and failsafe_active_seconds > 0:
        failsafe_penalty = min(0.4, failsafe_active_seconds / session_uptime_sec)

    deny_penalty = min(0.3, 0.05 * len(denied_tools))

    trust = (
        0.45 * undo_score
        + 0.45 * feedback_score
        + 0.10 * (1.0 - failsafe_penalty)
        - deny_penalty
    )
    trust = float(max(0.0, min(1.0, trust)))

    return {
        "trust_score": round(trust, 3),
        "undo_rate": round(undo_rate, 3),
        "undo_score": round(undo_score, 3),
        "feedback_score": round(feedback_score, 3),
        "helpful": helpful,
        "unhelpful": unhelpful,
        "never": never,
        "actions_count": actions_count,
        "undos_count": undos_count,
        "denied_tools_count": len(denied_tools),
        "interpretation": _interpret(trust, undo_rate, rated),
    }


def _interpret(trust: float, undo_rate: float, rated: int) -> str:
    if rated == 0 and undo_rate < 0.15:
        return "Not enough feedback yet — rate actions in Why? to personalize."
    if trust >= 0.75:
        return "Co-pilot actions seem well accepted."
    if trust >= 0.45:
        return "Mixed acceptance — use Never on noisy tools or try a calmer preset."
    return "Low trust — consider Pause, simpler recipe, or review denied tools."
