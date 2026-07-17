"""Block-review → personalization learning tests."""

from pathlib import Path

from neural_flow_architect.core.session import SessionController
from neural_flow_architect.core.settings import Settings
from neural_flow_architect.personalization.learning import learn_from_block_review
from neural_flow_architect.personalization.profile import UserProfile


def test_noisy_architect_forces_calm() -> None:
    profile = UserProfile(protect_engagement_threshold=0.6, deep_flow_engagement_threshold=0.8)
    profile.preferences.protect_style = "assertive"
    msg = learn_from_block_review(
        profile,
        helpful_block=True,
        architect_helpful=False,
        undos_count=2,
        actions_count=5,
        peak_engagement=0.7,
    )
    assert msg is not None
    assert profile.preferences.protect_style == "calm"
    assert "noisy" in msg.lower() or "calm" in msg.lower()


def test_unhelpful_block_raises_thresholds() -> None:
    profile = UserProfile(protect_engagement_threshold=0.6, deep_flow_engagement_threshold=0.8)
    before = profile.protect_engagement_threshold
    learn_from_block_review(
        profile,
        helpful_block=False,
        architect_helpful=False,
        peak_engagement=0.5,
    )
    assert profile.protect_engagement_threshold >= before


def test_session_applies_block_review_learning(tmp_path: Path) -> None:
    session = SessionController(Settings(adapter="simulator", data_dir=tmp_path))
    session._pending_block_review = {"session_id": "x", "prompt": "test"}
    before = session.profile.protect_engagement_threshold
    out = session.submit_block_review(
        helpful_block=False, architect_helpful=False, note="meh"
    )
    assert out["ok"]
    assert out.get("learning")
    assert session.profile.protect_engagement_threshold >= before
    assert session.profile.preferences.protect_style == "calm"
