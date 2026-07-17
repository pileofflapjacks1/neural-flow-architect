"""Offline policy scoreboard and weekly recap — did the co-pilot help?"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
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
            "sparkline": [],
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

    sparkline = _sparkline_points(sessions, limit=14)

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
        "sparkline": sparkline,
    }


def single_session_score(session: dict[str, Any]) -> float:
    """Lightweight 0–100 score for one session (sparkline / recap)."""
    actions = max(int(session.get("actions_count") or 0), 0)
    undos = int(session.get("undos_count") or 0)
    undo_c = max(0.0, 1.0 - min(1.0, (undos / max(actions, 1)) * 2))
    rev = session.get("block_review") or {}
    if rev.get("helpful_block") is True:
        rev_c = 1.0
    elif rev.get("helpful_block") is False:
        rev_c = 0.25
    else:
        rev_c = 0.55
    if rev.get("architect_helpful") is False:
        rev_c = min(rev_c, 0.3)
    flow = float(session.get("flow_minutes") or 0)
    flow_c = min(1.0, flow / 20.0)  # ~20 flow-ish minutes → full component
    score = 100.0 * (0.40 * undo_c + 0.35 * rev_c + 0.25 * flow_c)
    return round(max(0.0, min(100.0, score)), 1)


def _parse_started(session: dict[str, Any]) -> datetime | None:
    raw = session.get("started_at")
    if not raw:
        return None
    if isinstance(raw, datetime):
        return raw
    try:
        text = str(raw).replace("Z", "+00:00")
        return datetime.fromisoformat(text).replace(tzinfo=None)
    except ValueError:
        return None


def _sparkline_points(sessions: list[dict[str, Any]], *, limit: int = 14) -> list[dict[str, Any]]:
    """Chronological (oldest→newest) per-session scores for sparklines."""
    dated: list[tuple[datetime, dict[str, Any]]] = []
    for s in sessions:
        started = _parse_started(s)
        if started is None:
            continue
        dated.append((started, s))
    dated.sort(key=lambda x: x[0])
    if limit > 0:
        dated = dated[-limit:]
    points: list[dict[str, Any]] = []
    for started, s in dated:
        sid = str(s.get("session_id") or "")
        points.append(
            {
                "session_id": sid,
                "started_at": started.isoformat(),
                "score": single_session_score(s),
                "flow_minutes": round(float(s.get("flow_minutes") or 0), 2),
                "actions": int(s.get("actions_count") or 0),
                "undos": int(s.get("undos_count") or 0),
                "recipe": str(s.get("recipe") or "study"),
            }
        )
    return points


def build_weekly_recap(
    sessions: list[dict[str, Any]],
    *,
    days: int = 7,
    feedback_history: list[dict[str, Any]] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """
    One-page local recap for the last ``days`` (default 7).

    Filters by session ``started_at``. Not a clinical metric.
    """
    feedback_history = feedback_history or []
    now = now or datetime.utcnow()
    days = max(1, min(int(days), 90))
    cutoff = now - timedelta(days=days)

    week: list[dict[str, Any]] = []
    for s in sessions:
        started = _parse_started(s)
        if started is None:
            continue
        if started >= cutoff:
            week.append(s)

    scoreboard = build_policy_scoreboard(week, feedback_history=feedback_history)
    sparkline = _sparkline_points(week, limit=0)  # all in window, chrono

    total_flow = sum(float(s.get("flow_minutes") or 0) for s in week)
    total_actions = sum(int(s.get("actions_count") or 0) for s in week)
    total_undos = sum(int(s.get("undos_count") or 0) for s in week)
    avg_peak = sum(float(s.get("peak_engagement") or 0) for s in week) / len(week) if week else 0.0

    # Recipe mix for the week
    recipe_counts: dict[str, int] = defaultdict(int)
    for s in week:
        recipe_counts[str(s.get("recipe") or "study")] += 1
    top_recipe = None
    if recipe_counts:
        top_recipe = max(recipe_counts.items(), key=lambda kv: kv[1])[0]

    highlights = _highlights(sparkline, week, scoreboard, top_recipe)

    trend = "flat"
    if len(sparkline) >= 2:
        first = float(sparkline[0]["score"])
        last = float(sparkline[-1]["score"])
        if last - first >= 8:
            trend = "up"
        elif first - last >= 8:
            trend = "down"

    return {
        "window_days": days,
        "from": cutoff.isoformat(),
        "to": now.isoformat(),
        "sessions": len(week),
        "score": scoreboard.get("score"),
        "interpretation": scoreboard.get("interpretation"),
        "trend": trend,
        "totals": {
            "flow_minutes": round(total_flow, 2),
            "actions": total_actions,
            "undos": total_undos,
            "avg_peak_engagement": round(avg_peak, 3),
            "undo_rate": round(total_undos / max(total_actions, 1), 3),
        },
        "top_recipe": top_recipe,
        "by_recipe": scoreboard.get("by_recipe") or {},
        "sparkline": sparkline,
        "highlights": highlights,
        "scoreboard": scoreboard,
        "disclaimer": (
            "Local weekly summary from session stats and reviews — not a medical or clinical score."
        ),
    }


def _highlights(
    sparkline: list[dict[str, Any]],
    week: list[dict[str, Any]],
    scoreboard: dict[str, Any],
    top_recipe: str | None,
) -> list[str]:
    notes: list[str] = []
    if not week:
        notes.append("No sessions in this window yet — complete a few blocks to build a recap.")
        return notes

    n = len(week)
    notes.append(f"{n} session{'s' if n != 1 else ''} in the window.")

    score = scoreboard.get("score")
    if score is not None:
        notes.append(f"Policy score {score}/100 — {scoreboard.get('interpretation', '')}".strip())

    if len(sparkline) >= 2:
        first = float(sparkline[0]["score"])
        last = float(sparkline[-1]["score"])
        if last > first + 5:
            notes.append("Session scores trending up — keep current protect style.")
        elif first > last + 5:
            notes.append("Session scores dipped — try calmer protect or more Pause.")
        else:
            notes.append("Session scores roughly steady across the window.")

    flow = sum(float(s.get("flow_minutes") or 0) for s in week)
    if flow >= 30:
        notes.append(f"About {flow:.0f} flow-ish minutes logged — solid deep-work time.")
    elif flow > 0:
        notes.append(f"{flow:.1f} flow-ish minutes — labels help refine this.")

    undos = sum(int(s.get("undos_count") or 0) for s in week)
    actions = sum(int(s.get("actions_count") or 0) for s in week)
    if actions > 0 and undos / actions > 0.25:
        notes.append("Undo rate is high — expand Never list for noisy tools.")
    elif actions > 0 and undos == 0:
        notes.append("No undos this window — co-pilot actions stayed acceptable.")

    if top_recipe:
        notes.append(f"Most-used recipe: {top_recipe}.")

    return notes[:8]
