"""Local personalization from self-report labels and session outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from neural_flow_architect.personalization.profile import UserProfile


@dataclass
class ThresholdUpdate:
    protect_engagement_threshold: float
    deep_flow_engagement_threshold: float
    message: str
    applied: bool


def update_thresholds_from_label(
    profile: UserProfile,
    *,
    felt_in_flow: bool,
    engagement_at_label: float,
    step: float = 0.02,
) -> ThresholdUpdate:
    """
    Nudge personal thresholds using self-report.

    - Positive label at high engagement: slightly lower protect threshold (easier entry)
    - Positive label at moderate engagement: align protect threshold toward observed eng
    - Negative label while system thought flow: raise protect threshold (more conservative)
    """
    protect = profile.protect_engagement_threshold
    deep = profile.deep_flow_engagement_threshold
    eng = float(max(0.0, min(1.0, engagement_at_label)))
    prefs = profile.preferences
    prefs.label_count = int(prefs.label_count) + 1

    if felt_in_flow:
        prefs.positive_flow_labels = int(prefs.positive_flow_labels) + 1
        # Move protect threshold toward observed engagement (EMA-like)
        protect = 0.85 * protect + 0.15 * max(0.35, eng - 0.08)
        if eng >= deep - 0.05:
            deep = 0.9 * deep + 0.1 * min(0.95, eng)
        msg = (
            f"Thanks — adjusted personal thresholds toward engagement {eng:.2f} "
            f"(protect={protect:.2f}, deep={deep:.2f})."
        )
    else:
        # User did not feel flow: be slightly more conservative
        protect = min(0.9, protect + step)
        deep = min(0.95, deep + step * 0.5)
        msg = (
            f"Noted — raised thresholds slightly so protect/deep require stronger signals "
            f"(protect={protect:.2f}, deep={deep:.2f})."
        )

    # Keep deep above protect
    deep = max(deep, protect + 0.12)
    profile.protect_engagement_threshold = float(round(protect, 3))
    profile.deep_flow_engagement_threshold = float(round(deep, 3))
    return ThresholdUpdate(
        protect_engagement_threshold=profile.protect_engagement_threshold,
        deep_flow_engagement_threshold=profile.deep_flow_engagement_threshold,
        message=msg,
        applied=True,
    )


def learn_from_session_summary(profile: UserProfile, summary: dict[str, Any]) -> str | None:
    """Light longitudinal tweak from completed session stats (optional)."""
    undos = int(summary.get("undos_count", 0) or 0)
    actions = int(summary.get("actions_count", 0) or 0)
    if actions >= 3 and undos / max(actions, 1) > 0.5:
        # High undo rate → calmer protect style
        profile.preferences.protect_style = "calm"
        return "High undo rate — switched protect style to calm."
    labels = summary.get("labels") or []
    pos = sum(1 for lab in labels if lab.get("felt_in_flow"))
    if pos >= 2 and profile.preferences.preferred_recipe == "study":
        return "Multiple positive flow labels this session — study recipe still preferred."
    return None
