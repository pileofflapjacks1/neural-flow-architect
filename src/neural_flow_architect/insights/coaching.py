"""Gentle, local-only coaching suggestions from longitudinal session data."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any


def build_coaching_notes(
    sessions: list[dict[str, Any]],
    *,
    max_notes: int = 5,
) -> list[dict[str, str]]:
    """
    Produce non-prescriptive coaching notes. Never medical advice.
    """
    if not sessions:
        return [
            {
                "title": "Getting started",
                "body": (
                    "Run a few labeled sessions (tap “I felt in flow” when it fits). "
                    "Personal thresholds improve from your own reports — not population norms."
                ),
                "kind": "onboarding",
            }
        ]

    notes: list[dict[str, str]] = []
    # Peak engagement averages
    peaks = [float(s.get("peak_engagement") or 0) for s in sessions]
    avg_peak = sum(peaks) / len(peaks) if peaks else 0.0

    # Flow minutes
    flow_mins = [float(s.get("flow_minutes") or 0) for s in sessions]
    avg_flow = sum(flow_mins) / len(flow_mins) if flow_mins else 0.0

    # Undo rates
    undo_rates = []
    for s in sessions:
        a = float(s.get("actions_count") or 0)
        u = float(s.get("undos_count") or 0)
        if a > 0:
            undo_rates.append(u / a)
    avg_undo = sum(undo_rates) / len(undo_rates) if undo_rates else 0.0

    # Hour-of-day heuristic from started_at
    hour_flow: dict[int, list[float]] = defaultdict(list)
    for s in sessions:
        started = s.get("started_at")
        fm = float(s.get("flow_minutes") or 0)
        if not started:
            continue
        try:
            dt = datetime.fromisoformat(str(started).replace("Z", ""))
            hour_flow[dt.hour].append(fm)
        except ValueError:
            continue

    best_hour = None
    best_avg = -1.0
    for h, vals in hour_flow.items():
        avg = sum(vals) / len(vals)
        if avg > best_avg:
            best_avg = avg
            best_hour = h

    notes.append(
        {
            "title": "Recent engagement",
            "body": (
                f"Across {len(sessions)} session(s), average peak engagement is {avg_peak:.2f} "
                f"and average flow-ish minutes is {avg_flow:.1f}. These are estimates, not diagnosis."
            ),
            "kind": "summary",
        }
    )

    if best_hour is not None and best_avg > 0:
        notes.append(
            {
                "title": "Time-of-day pattern",
                "body": (
                    f"Your higher flow-ish minutes often cluster near {best_hour:02d}:00 "
                    f"(local session start). Consider protecting that window when you can."
                ),
                "kind": "timing",
            }
        )

    if avg_undo > 0.35:
        notes.append(
            {
                "title": "Architect friction",
                "body": (
                    "Undo rate is relatively high. Prefer Pause or “Never” on noisy tools, "
                    "or switch recipe to rest when you need fewer interventions."
                ),
                "kind": "agent",
            }
        )
    elif avg_undo < 0.1 and any(float(s.get("actions_count") or 0) > 0 for s in sessions):
        notes.append(
            {
                "title": "Co-pilot fit",
                "body": (
                    "Few undos recently — protect actions may be well-tuned. "
                    "You can still Pause anytime; you remain in control."
                ),
                "kind": "agent",
            }
        )

    # Label agreement
    pos = 0
    total_labels = 0
    for s in sessions:
        for lab in s.get("labels") or []:
            total_labels += 1
            if lab.get("felt_in_flow"):
                pos += 1
    if total_labels == 0:
        notes.append(
            {
                "title": "Self-report helps personalization",
                "body": (
                    "No self-report labels yet. When a stretch feels like flow (or clearly doesn’t), "
                    "tap the label buttons — thresholds adapt on-device."
                ),
                "kind": "labels",
            }
        )
    elif total_labels >= 3:
        notes.append(
            {
                "title": "Your labels",
                "body": (
                    f"{pos}/{total_labels} labels were positive. "
                    "Personal thresholds have been nudged from these reports."
                ),
                "kind": "labels",
            }
        )

    notes.append(
        {
            "title": "Safety reminder",
            "body": (
                "Neural Flow Architect is research/assistive software, not a medical device. "
                "Rest when fatigued; never ignore pain or clinical guidance for productivity."
            ),
            "kind": "safety",
        }
    )
    return notes[:max_notes]
