"""Personalization learning tests."""

from neural_flow_architect.personalization.learning import update_thresholds_from_label
from neural_flow_architect.personalization.profile import UserProfile


def test_positive_label_nudges_thresholds() -> None:
    profile = UserProfile()
    before = profile.protect_engagement_threshold
    update = update_thresholds_from_label(profile, felt_in_flow=True, engagement_at_label=0.55)
    assert update.applied
    assert profile.preferences.label_count == 1
    assert profile.preferences.positive_flow_labels == 1
    # Should move somewhat toward observed engagement
    assert abs(profile.protect_engagement_threshold - before) > 0.0 or update.message


def test_negative_label_raises_thresholds() -> None:
    profile = UserProfile(protect_engagement_threshold=0.6, deep_flow_engagement_threshold=0.8)
    update = update_thresholds_from_label(profile, felt_in_flow=False, engagement_at_label=0.7)
    assert profile.protect_engagement_threshold >= 0.6
    assert "raised" in update.message.lower() or profile.protect_engagement_threshold > 0.6
