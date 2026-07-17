"""Offline evaluation harness tests."""

from __future__ import annotations

import pytest

from neural_flow_architect.eval.harness import run_offline_eval


@pytest.mark.asyncio
async def test_offline_eval_produces_report() -> None:
    report = await run_offline_eval(duration_sec=3.0, channels=4, sample_rate_hz=64.0)
    assert report.ticks >= 1
    data = report.to_dict()
    assert "mean_engagement" in data
    assert data["ticks"] == report.ticks
