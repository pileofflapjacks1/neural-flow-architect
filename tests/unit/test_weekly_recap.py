"""Weekly recap, sparkline scores, timeline-related scoreboard fields."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from neural_flow_architect.api.server import create_app
from neural_flow_architect.core.session import SessionController
from neural_flow_architect.core.settings import Settings
from neural_flow_architect.insights.scoreboard import (
    build_policy_scoreboard,
    build_weekly_recap,
    single_session_score,
)


def _session(
    *,
    days_ago: float,
    actions: int = 10,
    undos: int = 1,
    flow: float = 12.0,
    recipe: str = "study",
    helpful: bool | None = True,
    now: datetime | None = None,
) -> dict:
    now = now or datetime(2026, 7, 17, 12, 0, 0)
    started = now - timedelta(days=days_ago)
    rev = None
    if helpful is not None:
        rev = {"helpful_block": helpful, "architect_helpful": helpful}
    return {
        "session_id": f"s-{days_ago}",
        "started_at": started.isoformat(),
        "actions_count": actions,
        "undos_count": undos,
        "flow_minutes": flow,
        "peak_engagement": 0.7,
        "recipe": recipe,
        "block_review": rev,
    }


def test_single_session_score_range() -> None:
    good = single_session_score(
        {
            "actions_count": 10,
            "undos_count": 0,
            "flow_minutes": 25,
            "block_review": {"helpful_block": True},
        }
    )
    bad = single_session_score(
        {
            "actions_count": 10,
            "undos_count": 8,
            "flow_minutes": 0,
            "block_review": {"helpful_block": False, "architect_helpful": False},
        }
    )
    assert 0 <= good <= 100
    assert 0 <= bad <= 100
    assert good > bad


def test_weekly_recap_filters_window() -> None:
    now = datetime(2026, 7, 17, 12, 0, 0)
    sessions = [
        _session(days_ago=1, recipe="study", now=now),
        _session(days_ago=3, recipe="create", undos=0, now=now),
        _session(days_ago=10, recipe="study", now=now),  # outside 7d
    ]
    recap = build_weekly_recap(sessions, days=7, now=now)
    assert recap["sessions"] == 2
    assert recap["window_days"] == 7
    assert recap["score"] is not None
    assert len(recap["sparkline"]) == 2
    # chronological
    assert recap["sparkline"][0]["started_at"] <= recap["sparkline"][1]["started_at"]
    assert recap["top_recipe"] in {"study", "create"}
    assert recap["highlights"]
    assert recap["totals"]["flow_minutes"] > 0
    assert recap["trend"] in {"up", "down", "flat"}


def test_weekly_recap_empty() -> None:
    recap = build_weekly_recap([], days=7)
    assert recap["sessions"] == 0
    assert recap["score"] is None
    assert recap["sparkline"] == []
    assert any("No sessions" in h for h in recap["highlights"])


def test_scoreboard_includes_sparkline() -> None:
    now = datetime(2026, 7, 17, 12, 0, 0)
    sessions = [
        _session(days_ago=0.1, now=now),
        _session(days_ago=1, undos=0, now=now),
    ]
    sb = build_policy_scoreboard(sessions)
    assert sb["score"] is not None
    assert len(sb["sparkline"]) == 2


@pytest.mark.asyncio
async def test_weekly_api(tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    settings = Settings(adapter="simulator", data_dir=tmp_path, dry_run=True)
    controller = SessionController(settings)
    # Seed one finished session via insights store
    store = controller.runtime.insights
    store.start_session(adapter="simulator", recipe="study")
    store.observe_action("test", tool_id="focus.enable")
    store.end_session(persist=True)

    app = create_app(settings, controller)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/weekly?days=7")
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        recap = body["recap"]
        assert "sparkline" in recap
        assert "highlights" in recap
        assert recap["window_days"] == 7

        sb = await client.get("/scoreboard")
        assert sb.status_code == 200
        assert "sparkline" in sb.json()["scoreboard"]
