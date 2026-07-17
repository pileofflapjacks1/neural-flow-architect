"""Coaching notes tests."""

from neural_flow_architect.insights.coaching import build_coaching_notes


def test_empty_sessions_onboarding() -> None:
    notes = build_coaching_notes([])
    assert notes
    assert notes[0]["kind"] == "onboarding"


def test_with_sessions() -> None:
    sessions = [
        {
            "started_at": "2026-07-17T10:00:00",
            "peak_engagement": 0.8,
            "flow_minutes": 12.0,
            "actions_count": 4,
            "undos_count": 0,
            "labels": [{"felt_in_flow": True}],
        }
    ]
    notes = build_coaching_notes(sessions)
    kinds = {n["kind"] for n in notes}
    assert "summary" in kinds
    assert "safety" in kinds
