"""Integration: short simulator closed loop."""

from __future__ import annotations

import pytest

from neural_flow_architect.core.runtime import NeuralFlowRuntime
from neural_flow_architect.core.settings import Settings


@pytest.mark.asyncio
async def test_simulator_runtime_ticks() -> None:
    settings = Settings(adapter="simulator", channels=4, sample_rate_hz=128, dry_run=True)
    # Smaller windows for faster test
    settings.window_sec = 0.25
    settings.hop_sec = 0.125
    runtime = NeuralFlowRuntime(settings)
    ticks = await runtime.run(duration_sec=2.5)
    assert len(ticks) >= 1
    assert ticks[-1].flow.confidence >= 0.0
    assert ticks[-1].decision.mode is not None
