"""API coverage for scoreboard, app map, timeline, OS Focus."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from neural_flow_architect.api.server import create_app
from neural_flow_architect.core.session import SessionController
from neural_flow_architect.core.settings import Settings


@pytest.mark.asyncio
async def test_scoreboard_app_map_timeline_os_focus(tmp_path) -> None:  # type: ignore[no-untyped-def]
    settings = Settings(
        adapter="simulator",
        data_dir=tmp_path,
        dry_run=True,
        channels=4,
        sample_rate_hz=128,
        window_sec=0.25,
        hop_sec=0.125,
    )
    controller = SessionController(settings)
    app = create_app(settings, controller)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        sb = await client.get("/scoreboard")
        assert sb.status_code == 200
        body = sb.json()
        assert body["ok"] is True
        assert "scoreboard" in body

        am = await client.get("/app_map")
        assert am.status_code == 200
        assert "map" in am.json()

        set_r = await client.post(
            "/app_map", json={"key": "customide", "category": "create"}
        )
        assert set_r.status_code == 200
        assert set_r.json()["ok"] is True
        assert set_r.json()["map"]["customide"] == "create"

        del_r = await client.post("/app_map/delete", json={"key": "customide"})
        assert del_r.status_code == 200
        assert "customide" not in del_r.json().get("map", {})

        tl = await client.get("/timeline")
        assert tl.status_code == 200
        assert "timeline" in tl.json()

        of = await client.get("/os_focus")
        assert of.status_code == 200
        assert "os_focus" in of.json()

        of_set = await client.post(
            "/os_focus", json={"enabled": True, "force_dry_run": True}
        )
        assert of_set.status_code == 200
        assert of_set.json()["os_focus"]["enabled"] is True
        assert of_set.json()["os_focus"]["mode"] == "dry_run"

        env = await client.get("/environment")
        assert env.status_code == 200
        assert "os_focus" in env.json()
