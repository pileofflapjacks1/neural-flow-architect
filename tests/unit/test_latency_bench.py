"""Latency bench tests."""

from __future__ import annotations

import pytest

from neural_flow_architect.eval.latency import run_latency_bench


@pytest.mark.asyncio
async def test_latency_bench_small() -> None:
    report = await run_latency_bench(n_channels=4, iterations=5, sample_rate_hz=128.0)
    data = report.to_dict()
    assert data["iterations"] == 5
    assert data["n_channels"] == 4
    assert "feature_extract" in data["stages_ms"]
    assert "pass" in data


@pytest.mark.asyncio
async def test_high_channel_stub_runs() -> None:
    """Stress path for implant-class channel counts (may be slower)."""
    report = await run_latency_bench(n_channels=256, iterations=3, sample_rate_hz=200.0)
    assert report.n_channels == 256
    assert len(report.e2e_ms) >= 1
