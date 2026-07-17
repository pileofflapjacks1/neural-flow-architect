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
    # Block review on the summary (if already attached)
    review = summary.get("block_review") or {}
    if review:
        msg = learn_from_block_review(
            profile,
            helpful_block=review.get("helpful_block"),
            architect_helpful=review.get("architect_helpful"),
            undos_count=undos,
            actions_count=actions,
            peak_engagement=float(summary.get("peak_engagement") or 0),
            recipe=str(summary.get("recipe") or profile.preferences.preferred_recipe),
        )
        if msg:
            return msg
    return None


def learn_from_block_review(
    profile: UserProfile,
    *,
    helpful_block: bool | None,
    architect_helpful: bool | None = None,
    undos_count: int = 0,
    actions_count: int = 0,
    peak_engagement: float = 0.0,
    recipe: str | None = None,
    step: float = 0.02,
) -> str | None:
    """
    Nudge thresholds and protect style from end-of-block review.

    - Helpful block + helpful architect → slight ease of protect threshold; keep style
    - Helpful block + noisy architect → calmer style + longer cooldowns via unhelpful bias
    - Unhelpful block → more conservative thresholds
    - Skip (None) → no change
    """
    if helpful_block is None and architect_helpful is None:
        return None

    protect = profile.protect_engagement_threshold
    deep = profile.deep_flow_engagement_threshold
    prefs = profile.preferences
    messages: list[str] = []

    # Track review counts on preferences via label_count-adjacent counters
    # (reuse notes field lightly is messy — store as dynamic attrs via model extra? use notes append no)
    # Use positive_flow_labels / label_count only for labels; reviews go through messages

    if helpful_block is True:
        # Successful work block — slightly easier entry next time
        protect = 0.9 * protect + 0.1 * max(
            0.4, peak_engagement - 0.1 if peak_engagement else protect
        )
        if recipe:
            prefs.preferred_recipe = recipe
        messages.append("Helpful block noted — gently eased flow entry thresholds.")
        if architect_helpful is True:
            prefs.protect_style = (
                "assertive" if prefs.protect_style == "assertive" else prefs.protect_style
            )
            # Mild assertiveness only if already undo-light
            if actions_count > 0 and undos_count / max(actions_count, 1) < 0.15:
                if prefs.protect_style == "calm":
                    # stay calm unless repeatedly positive — don't jump
                    pass
            messages.append("Architect marked helpful — will keep similar protect behavior.")
        elif architect_helpful is False:
            prefs.protect_style = "calm"
            protect = min(0.9, protect + step)  # need stronger signal before acting
            messages.append("Block was OK but co-pilot was noisy — switched to calm protect style.")
    elif helpful_block is False:
        protect = min(0.92, protect + step * 1.5)
        deep = min(0.96, deep + step)
        prefs.protect_style = "calm"
        messages.append("Unhelpful block — raised thresholds and calmed protect style.")
        if architect_helpful is False:
            messages.append("Architect marked unhelpful — fewer medium actions preferred.")

    deep = max(deep, protect + 0.12)
    profile.protect_engagement_threshold = float(round(protect, 3))
    profile.deep_flow_engagement_threshold = float(round(deep, 3))
    return " ".join(messages) if messages else None
