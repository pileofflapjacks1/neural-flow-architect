"""Personal signature and block review tests."""

from pathlib import Path

from neural_flow_architect.core.caregiver import CaregiverChecklist
from neural_flow_architect.core.session import SessionController
from neural_flow_architect.core.settings import Settings
from neural_flow_architect.personalization.signature import build_personal_signature


def test_signature_from_sessions() -> None:
    sessions = [
        {
            "hour_started": 10,
            "recipe": "study",
            "flow_minutes": 20,
            "peak_engagement": 0.8,
            "labels": [{"felt_in_flow": True}],
            "block_review": {"helpful_block": True, "architect_helpful": True},
        },
        {
            "hour_started": 22,
            "recipe": "rest",
            "flow_minutes": 2,
            "peak_engagement": 0.3,
            "labels": [{"felt_in_flow": False}],
        },
    ]
    sig = build_personal_signature(sessions)
    assert sig.sessions_considered == 2
    assert 10 in sig.best_hours or sig.best_hours
    d = sig.to_dict()
    assert "disclaimer" in d


def test_block_review_and_caregiver(tmp_path: Path) -> None:
    session = SessionController(Settings(adapter="simulator", data_dir=tmp_path))
    # Simulate pending review
    session._pending_block_review = {
        "session_id": "abc",
        "prompt": "Was this work block helpful?",
    }
    out = session.submit_block_review(
        helpful_block=True, architect_helpful=True, note="great"
    )
    assert out["ok"]
    assert session._pending_block_review is None
    assert session.caregiver.items.get("label_or_review") is True


def test_caregiver_checklist_complete(tmp_path: Path) -> None:
    path = tmp_path / "c.json"
    c = CaregiverChecklist()
    for key, _ in [
        ("start_session", ""),
        ("pause", ""),
        ("undo", ""),
        ("rest", ""),
        ("label_or_review", ""),
        ("helper_leaves", ""),
    ]:
        c.mark(key, True)
    assert c.completed
    c.save(path)
    loaded = CaregiverChecklist.load(path)
    assert loaded.completed
