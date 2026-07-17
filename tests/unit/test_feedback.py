"""Action feedback preference learning tests."""

from pathlib import Path

from neural_flow_architect.core.session import SessionController
from neural_flow_architect.core.settings import Settings
from neural_flow_architect.personalization.feedback import FeedbackStore


def test_never_blocks_tool() -> None:
    store = FeedbackStore()
    out = store.record("focus.enable", "never", denied_tools=[], granted_tools=[])
    assert "focus.enable" in out["denied_tools"]
    assert store.is_never("focus.enable")


def test_helpful_boosts_score() -> None:
    store = FeedbackStore()
    store.record("focus.enable", "helpful")
    store.record("focus.enable", "helpful")
    assert store.score_bonus("focus.enable") > 0


def test_session_feedback(tmp_path: Path) -> None:
    session = SessionController(Settings(adapter="simulator", data_dir=tmp_path))
    out = session.record_feedback("notify.suppress_noncritical", "never")
    assert out["ok"]
    assert "notify.suppress_noncritical" in session.profile.preferences.denied_tools
