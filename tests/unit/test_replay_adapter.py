"""Replay adapter tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from neural_flow_architect.adapters.replay import ReplayAdapter, load_trajectory
from neural_flow_architect.core.types import SourceKind


@pytest.mark.asyncio
async def test_replay_emits_frames() -> None:
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "demo_trajectory.json"
    adapter = ReplayAdapter(
        trajectory_path=fixture,
        n_channels=4,
        sample_rate_hz=128,
        chunk_samples=32,
        loop=False,
        realtime=False,
    )
    meta = await adapter.connect()
    assert meta.source_kind == SourceKind.REPLAY
    frames = []
    async for frame in adapter.stream():
        frames.append(frame)
        if len(frames) >= 5:
            break
    await adapter.disconnect()
    assert len(frames) == 5
    assert frames[0].data.shape[0] == 4


def test_load_trajectory_fixture() -> None:
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "demo_trajectory.json"
    traj = load_trajectory(fixture)
    assert traj[0]["engagement"] == 0.2
    assert traj[-1]["t"] == 90.0
