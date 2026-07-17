"""Profile backup and a11y settings tests."""

from pathlib import Path

import pytest

from neural_flow_architect.core.session import SessionController
from neural_flow_architect.core.settings import Settings
from neural_flow_architect.personalization.backup import (
    export_profile_bundle,
    import_profile_bundle,
)
from neural_flow_architect.personalization.profile import UserProfile


def test_export_import_roundtrip(tmp_path: Path) -> None:
    profile = UserProfile()
    profile.preferences.ui_scale = 1.4
    profile.preferences.high_contrast = True
    profile.protect_engagement_threshold = 0.55
    bundle = export_profile_bundle(profile, onboarding={"completed": True})
    assert "raw" not in str(bundle).lower() or "raw neural" in bundle["disclaimer"].lower()
    dest = tmp_path / "profiles"
    imported = import_profile_bundle(dest, bundle)
    assert imported.preferences.ui_scale == 1.4
    assert imported.preferences.high_contrast is True
    assert imported.protect_engagement_threshold == 0.55


def test_update_a11y(tmp_path: Path) -> None:
    settings = Settings(adapter="simulator", data_dir=tmp_path)
    session = SessionController(settings)
    out = session.update_a11y(ui_scale=1.5, high_contrast=True)
    assert out["ok"]
    assert out["a11y"]["ui_scale"] == 1.5
    assert out["a11y"]["high_contrast"] is True


@pytest.mark.asyncio
async def test_multimodal_command(tmp_path: Path) -> None:
    settings = Settings(adapter="simulator", data_dir=tmp_path)
    session = SessionController(settings)
    res = await session.multimodal_command(source="voice", text="undo")
    # nothing to undo is still a recognized command
    assert res.get("parsed", {}).get("intent") == "undo"
