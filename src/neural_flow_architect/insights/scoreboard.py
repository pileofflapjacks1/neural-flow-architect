"""Offline policy scoreboard — did the co-pilot help this week?"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from neural_flow_architect.insights.trust import compute_trust_metrics


def build_policy_scoreboard(
    sessions: list[dict[str, Any]],
    *,
    feedback_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Aggregate local sessions into a simple policy scorecard.

    Not a clinical metric. Higher score ≈ fewer undos, better reviews/feedback.
    """
    feedback_history = feedback_history or []
    if not sessions:
        return {
            "sessions": 0,
            "score": None,
            "interpretation": "No sessions yet — run a few blocks and complete reviews.",
            "by_recipe": {},
            "trust": compute_trust_metrics(),
        }

    total_actions = sum(int(s.get("actions_count") or 0) for s in sessions)
    total_undos = sum(int(s.get("undos_count") or 0) for s in sessions)
    reviews = [s.get("block_review") or {} for s in sessions if s.get("block_review")]
    helpful_blocks = sum(1 for r in reviews if r.get("helpful_block") is True)
    noisy = sum(1 for r in reviews if r.get("architect_helpful") is False)

    trust = compute_trust_metrics(
        actions_count=total_actions,
        undos_count=total_undos,
        feedback_history=feedback_history,
        session_uptime_sec=1.0,
    )

    # Recipe breakdown
    by_recipe: dict[str, dict[str, float]] = defaultdict(
        lambda: {"sessions": 0, "flow_minutes": 0.0, "helpful_reviews": 0, "reviews": 0}
    )
    for s in sessions:
        r = str(s.get("recipe") or "study")
        by_recipe[r]["sessions"] += 1
        by_recipe[r]["flow_minutes"] += float(s.get("flow_minutes") or 0)
        rev = s.get("block_review") or {}
        if rev.get("helpful_block") is not None:
            by_recipe[r]["reviews"] += 1
            if rev.get("helpful_block"):
                by_recipe[r]["helpful_reviews"] += 1

    # Composite score 0–100
    undo_component = max(0.0, 1.0 - min(1.0, (total_undos / max(total_actions, 1)) * 2))
    review_component = helpful_blocks / max(len(reviews), 1) if reviews else 0.55
    trust_component = float(trust.get("trust_score") or 0.5)
    noisy_penalty = min(0.25, 0.08 * noisy)
    score = 100.0 * (
        0.35 * undo_component + 0.35 * review_component + 0.30 * trust_component - noisy_penalty
    )
    score = max(0.0, min(100.0, score))

    if score >= 75:
        interpretation = "Policy looks well accepted — keep current presets and protect style."
    elif score >= 50:
        interpretation = "Mixed results — review Never list and try calmer protect or quiet hours."
    else:
        interpretation = "Low policy score — prefer Pause more, reduce assertive tools, add labels."

    return {
        "sessions": len(sessions),
        "score": round(score, 1),
        "interpretation": interpretation,
        "totals": {
            "actions": total_actions,
            "undos": total_undos,
            "block_reviews": len(reviews),
            "helpful_blocks": helpful_blocks,
            "architect_noisy_reviews": noisy,
        },
        "trust": trust,
        "by_recipe": {
            k: {
                "sessions": int(v["sessions"]),
                "flow_minutes": round(v["flow_minutes"], 2),
                "helpful_review_rate": round(v["helpful_reviews"] / max(v["reviews"], 1), 3),
            }
            for k, v in by_recipe.items()
        },
    }
