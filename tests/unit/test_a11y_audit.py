"""A11y audit pack: scan/dwell prefs, announce, keymap, API body fields."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from neural_flow_architect.api.server import create_app
from neural_flow_architect.core.multimodal import keymap_for_ui
from neural_flow_architect.core.session import SessionController
from neural_flow_architect.core.settings import Settings
from neural_flow_architect.personalization.a11y import AccessibilitySettings


def test_scan_and_dwell_presets_defined() -> None:
    assert AccessibilitySettings.SCAN_PRESETS_MS == (800, 1400, 2000)
    assert AccessibilitySettings.DWELL_PRESETS_MS == (800, 1200, 1800)


def test_keymap_for_ui_covers_primary_controls() -> None:
    keys = keymap_for_ui()
    assert len(keys) >= 8
    intents = {k["intent"] for k in keys}
    assert "pause_agent" in intents
    assert "undo" in intents
    assert "rest_mode" in intents
    labels = {k["key"] for k in keys}
    assert "P" in labels
    assert "U" in labels


def test_update_a11y_scan_announce_presets(tmp_path: Path) -> None:
    settings = Settings(adapter="simulator", data_dir=tmp_path)
    session = SessionController(settings)
    out = session.update_a11y(
        scan_mode=True,
        scan_interval_ms=800,
        dwell_ms=1800,
        announce_actions=False,
    )
    assert out["ok"]
    a11y = out["a11y"]
    assert a11y["scan_mode"] is True
    assert a11y["scan_interval_ms"] == 800
    assert a11y["dwell_ms"] == 1800
    assert a11y["announce_actions"] is False
    assert a11y["scan_presets_ms"] == [800, 1400, 2000]
    assert a11y["dwell_presets_ms"] == [800, 1200, 1800]
    assert len(a11y["keyboard_map"]) >= 8


def test_keyboard_map_session_helper(tmp_path: Path) -> None:
    settings = Settings(adapter="simulator", data_dir=tmp_path)
    session = SessionController(settings)
    km = session.keyboard_map_for_ui()
    assert any(e["intent"] == "pause_agent" for e in km)


@pytest.mark.asyncio
async def test_a11y_and_keymap_api(tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    settings = Settings(adapter="simulator", data_dir=tmp_path, dry_run=True)
    controller = SessionController(settings)
    app = create_app(settings, controller)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        g = await client.get("/a11y")
        assert g.status_code == 200
        body = g.json()["a11y"]
        assert "keyboard_map" in body
        assert "announce_actions" in body

        p = await client.post(
            "/a11y",
            json={
                "scan_mode": True,
                "scan_interval_ms": 2000,
                "announce_actions": True,
                "quiet_hours_enabled": True,
            },
        )
        assert p.status_code == 200
        a11y = p.json()["a11y"]
        assert a11y["scan_mode"] is True
        assert a11y["scan_interval_ms"] == 2000
        assert a11y["quiet_hours_enabled"] is True

        km = await client.get("/keymap")
        assert km.status_code == 200
        assert km.json()["ok"] is True
        assert len(km.json()["keys"]) >= 8
