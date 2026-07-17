"""Local API integration tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from neural_flow_architect.api.server import create_app
from neural_flow_architect.core.session import SessionController
from neural_flow_architect.core.settings import Settings


@pytest.mark.asyncio
async def test_health_and_state(tmp_path) -> None:  # type: ignore[no-untyped-def]
    settings = Settings(
        adapter="simulator",
        data_dir=tmp_path,
        dry_run=False,
        channels=4,
        sample_rate_hz=128,
        window_sec=0.25,
        hop_sec=0.125,
    )
    controller = SessionController(settings)
    app = create_app(settings, controller)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/health")
        assert health.status_code == 200
        assert health.json()["ok"] is True

        state = await client.get("/state")
        assert state.status_code == 200
        assert state.json()["running"] is False

        started = await client.post("/session/start", json={"duration_sec": 2.0})
        assert started.status_code == 200
        assert started.json()["ok"] is True

        # Let loop produce ticks
        import asyncio

        await asyncio.sleep(1.2)
        live = await client.get("/state")
        body = live.json()
        assert body["running"] is True
        assert "flow" in body

        pause = await client.post("/agent/pause", json={"paused": True})
        assert pause.json()["agent_paused"] is True

        label = await client.post(
            "/session/label", json={"felt_in_flow": True, "note": "test"}
        )
        assert label.json()["ok"] is True

        stopped = await client.post("/session/stop")
        assert stopped.json()["ok"] is True
