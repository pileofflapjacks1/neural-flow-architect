"""Soak test (short simulated duration)."""

import pytest

from neural_flow_architect.eval.soak import run_soak


@pytest.mark.asyncio
async def test_short_soak() -> None:
    report = await run_soak(duration_sec=5.0, channels=4, memory_limit_mb=1024)
    assert report.ticks >= 1
    assert report.frames >= 1
    assert report.ok
    d = report.to_dict()
    assert "mean_tick_ms" in d
