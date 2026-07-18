"""Post-session recap: what helped / hurt flow (local summaries only)."""

from __future__ import annotations

from typing import Any


def build_session_recap(session: dict[str, Any] | None) -> dict[str, Any]:
    """
    Structured end-of-session summary for Insights / export.

    Not medical advice. Uses session stats, labels, timeline, block review.
    """
    if not session:
        return {
            "ok": False,
            "message": "No session summary available.",
            "helped": [],
            "hurt": [],
            "recommendations": [],
        }

    actions = int(session.get("actions_count") or 0)
    undos = int(session.get("undos_count") or 0)
    flow_min = float(session.get("flow_minutes") or 0)
    peak = float(session.get("peak_engagement") or 0)
    recipe = str(session.get("recipe") or "study")
    labels = session.get("labels") or []
    pos = sum(1 for lab in labels if lab.get("felt_in_flow"))
    neg = sum(1 for lab in labels if lab.get("felt_in_flow") is False)
    review = session.get("block_review") or {}
    timeline = session.get("timeline") or []
    state_minutes = session.get("state_minutes") or {}

    undo_rate = undos / max(actions, 1)
    helped: list[str] = []
    hurt: list[str] = []
    recommendations: list[str] = []

    # Helped
    if flow_min >= 10:
        helped.append(f"About {flow_min:.1f} flow-ish minutes — solid block length.")
    if peak >= 0.75:
        helped.append(f"Peak engagement {peak:.2f} — strong sustained attention window.")
    if pos > 0:
        helped.append(f"{pos} positive ‘felt in flow’ label(s) to train personal thresholds.")
    if review.get("helpful_block") is True:
        helped.append("You marked the block as helpful overall.")
    if review.get("architect_helpful") is True:
        helped.append("Co-pilot actions felt helpful this block.")
    if undo_rate < 0.1 and actions > 0:
        helped.append("Low undo rate — protect actions mostly stayed welcome.")
    if recipe:
        helped.append(f"Recipe in use: {recipe}.")

    # Tools that fired (from timeline)
    tools: dict[str, int] = {}
    for ev in timeline:
        if ev.get("kind") != "action":
            continue
        tid = str((ev.get("detail") or {}).get("tool_id") or "action")
        tools[tid] = tools.get(tid, 0) + 1
    if tools:
        top = sorted(tools.items(), key=lambda kv: -kv[1])[:3]
        helped.append(
            "Most frequent co-pilot tools: " + ", ".join(f"{t}×{n}" for t, n in top) + "."
        )

    # Hurt
    if undo_rate >= 0.25 and actions >= 2:
        hurt.append(
            f"Undo rate {undo_rate:.0%} — some co-pilot actions were reversed (use Never on noisy ones)."
        )
    if neg > pos and neg > 0:
        hurt.append(
            "More negative than positive flow labels — thresholds will get more conservative."
        )
    if review.get("architect_helpful") is False:
        hurt.append("You marked the co-pilot as not helpful / noisy this block.")
    if review.get("helpful_block") is False:
        hurt.append("Block itself felt unhelpful — consider rest recipe or quieter hours.")
    if flow_min < 2 and actions > 0:
        hurt.append(
            "Little time in flow-ish states — signal quality or context may need attention."
        )
    fatigued = float(state_minutes.get("fatigued") or 0) + float(state_minutes.get("low") or 0)
    if fatigued > flow_min and fatigued > 5:
        hurt.append("More time in low/fatigued than flow — prioritize recovery windows.")

    # Recommendations
    if undo_rate >= 0.2:
        recommendations.append("Open Why? on the next action you undo and tap Never for that tool.")
    if pos + neg < 2:
        recommendations.append("Add a few ‘Felt in flow’ / ‘Not really’ labels next session.")
    if flow_min >= 5 and recipe == "study":
        recommendations.append("Study recipe worked — keep quiet hours if evenings get noisy.")
    if review.get("architect_helpful") is False:
        recommendations.append("Switch protect style to calm in Access / preferences.")
    if not recommendations:
        recommendations.append("Keep Pause/Undo handy and label a couple of moments next time.")

    return {
        "ok": True,
        "session_id": session.get("session_id"),
        "recipe": recipe,
        "adapter": session.get("adapter"),
        "totals": {
            "flow_minutes": round(flow_min, 2),
            "peak_engagement": round(peak, 3),
            "actions": actions,
            "undos": undos,
            "undo_rate": round(undo_rate, 3),
            "labels_positive": pos,
            "labels_negative": neg,
            "state_minutes": state_minutes,
        },
        "block_review": review or None,
        "helped": helped,
        "hurt": hurt,
        "recommendations": recommendations,
        "disclaimer": (
            "Local session recap from stats and your labels — not a medical or clinical report."
        ),
    }
