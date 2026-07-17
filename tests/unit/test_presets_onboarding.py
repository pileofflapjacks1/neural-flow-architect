"""Presets and onboarding tests."""

from pathlib import Path

from neural_flow_architect.core.onboarding import OnboardingState
from neural_flow_architect.core.session import SessionController
from neural_flow_architect.core.settings import Settings
from neural_flow_architect.personalization.presets import get_preset, list_presets


def test_list_builtin_presets() -> None:
    ids = {p["id"] for p in list_presets()}
    assert "morning_focus" in ids
    assert "wind_down" in ids


def test_apply_preset(tmp_path: Path) -> None:
    settings = Settings(adapter="simulator", data_dir=tmp_path)
    session = SessionController(settings)
    out = session.apply_preset("creative")
    assert out["ok"] is True
    assert session._recipe == "create"
    assert session.profile.preferences.active_preset == "creative"


def test_onboarding_advance(tmp_path: Path) -> None:
    path = tmp_path / "onboarding.json"
    state = OnboardingState()
    assert state.completed is False
    state.advance()
    state.save(path)
    loaded = OnboardingState.load(path)
    assert loaded.current_step != "welcome" or "welcome" in loaded.completed_steps


def test_get_preset() -> None:
    p = get_preset("morning_focus")
    assert p is not None
    assert p.recipe == "study"
