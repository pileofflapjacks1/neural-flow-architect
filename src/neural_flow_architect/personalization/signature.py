"""Personal flow signature v0 — from labels, time-of-day, recipe only.

Honest, local, no overclaimed neural biomarkers.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PersonalFlowSignature:
    """Aggregated 'what works for you' profile from session history."""

    sessions_considered: int = 0
    positive_labels: int = 0
    total_labels: int = 0
    best_hours: list[int] = field(default_factory=list)
    best_recipes: list[str] = field(default_factory=list)
    avg_peak_engagement: float = 0.0
    avg_flow_minutes: float = 0.0
    block_reviews_positive: int = 0
    block_reviews_total: int = 0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sessions_considered": self.sessions_considered,
            "positive_labels": self.positive_labels,
            "total_labels": self.total_labels,
            "label_positive_rate": round(
                self.positive_labels / max(self.total_labels, 1), 3
            ),
            "best_hours": self.best_hours,
            "best_recipes": self.best_recipes,
            "avg_peak_engagement": round(self.avg_peak_engagement, 3),
            "avg_flow_minutes": round(self.avg_flow_minutes, 2),
            "block_reviews_positive": self.block_reviews_positive,
            "block_reviews_total": self.block_reviews_total,
            "block_positive_rate": round(
                self.block_reviews_positive / max(self.block_reviews_total, 1), 3
            ),
            "notes": self.notes,
            "disclaimer": (
                "Estimated from your local self-reports and session stats only — "
                "not a clinical neural signature."
            ),
        }


def build_personal_signature(
    sessions: list[dict[str, Any]],
    *,
    min_sessions: int = 1,
) -> PersonalFlowSignature:
    sig = PersonalFlowSignature(sessions_considered=len(sessions))
    if len(sessions) < min_sessions:
        sig.notes.append("Need a few more sessions for stable patterns.")
        return sig

    hour_scores: dict[int, list[float]] = defaultdict(list)
    recipe_scores: dict[str, list[float]] = defaultdict(list)
    peaks: list[float] = []
    flow_mins: list[float] = []

    for s in sessions:
        peaks.append(float(s.get("peak_engagement") or 0))
        flow_mins.append(float(s.get("flow_minutes") or 0))
        hour = s.get("hour_started")
        if hour is None and s.get("started_at"):
            try:
                hour = int(str(s["started_at"])[11:13])
            except (ValueError, IndexError):
                hour = None
        recipe = str(s.get("recipe") or "study")
        # Score: flow minutes + positive labels weight
        score = float(s.get("flow_minutes") or 0)
        for lab in s.get("labels") or []:
            sig.total_labels += 1
            if lab.get("felt_in_flow"):
                sig.positive_labels += 1
                score += 5.0
        review = s.get("block_review") or {}
        if review.get("helpful_block") is not None:
            sig.block_reviews_total += 1
            if review.get("helpful_block"):
                sig.block_reviews_positive += 1
                score += 8.0
            if review.get("architect_helpful"):
                score += 3.0
        if hour is not None:
            hour_scores[int(hour)].append(score)
        recipe_scores[recipe].append(score)

    if peaks:
        sig.avg_peak_engagement = sum(peaks) / len(peaks)
    if flow_mins:
        sig.avg_flow_minutes = sum(flow_mins) / len(flow_mins)

    def top_keys(d: dict[Any, list[float]], n: int = 3) -> list[Any]:
        ranked = sorted(
            (
                (k, vals)
                for k, vals in d.items()
                if vals and max(vals) > 0
            ),
            key=lambda kv: sum(kv[1]) / max(len(kv[1]), 1),
            reverse=True,
        )
        return [k for k, _ in ranked[:n]]

    sig.best_hours = [int(h) for h in top_keys(hour_scores)]
    sig.best_recipes = [str(r) for r in top_keys(recipe_scores)]

    if sig.best_hours:
        hrs = ", ".join(f"{h:02d}:00" for h in sig.best_hours[:2])
        sig.notes.append(f"Your stronger blocks often start near {hrs} (local).")
    if sig.best_recipes:
        sig.notes.append(
            f"Recipes that correlate with better blocks: {', '.join(sig.best_recipes)}."
        )
    if sig.total_labels == 0:
        sig.notes.append("Add ‘I felt in flow’ labels to sharpen your personal signature.")
    if sig.block_reviews_total == 0:
        sig.notes.append("Complete an end-of-block review after sessions to train the co-pilot.")

    return sig
