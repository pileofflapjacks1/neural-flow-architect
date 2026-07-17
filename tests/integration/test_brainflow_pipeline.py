"""BrainFlow file-mode closed loop: adapter → features → flow → agent."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pytest

from neural_flow_architect.adapters.brainflow_adapter import BrainFlowAdapter
from neural_flow_architect.adapters.registry import (
    default_brainflow_fixture,
    resolve_brainflow_file,
)
from neural_flow_architect.core.doctor import run_doctor
from neural_flow_architect.core.runtime import NeuralFlowRuntime
from neural_flow_architect.core.settings import Settings
from neural_flow_architect.flow.engine import FlowEngine
from neural_flow_architect.signal.features import FeatureExtractor


@pytest.fixture
def eeg_fixture() -> Path:
    path = default_brainflow_fixture()
    assert path.is_file(), f"missing fixture {path}"
    return path


@pytest.mark.asyncio
async def test_brainflow_file_to_flow_pipeline(eeg_fixture: Path) -> None:
    adapter = BrainFlowAdapter(
        file_path=str(eeg_fixture),
        chunk_samples=64,
        sample_rate_hz=250.0,
        realtime=False,
    )
    meta = await adapter.connect()
    assert meta.n_channels == 4
    assert "file_replay" in adapter.capabilities()

    extractor = FeatureExtractor(
        sample_rate_hz=meta.sampling_rate_hz,
        window_sec=0.5,
        hop_sec=0.25,
    )
    engine = FlowEngine()
    windows = 0
    qualities: list[float] = []
    async for frame in adapter.stream():
        assert frame.data.ndim == 2
        qualities.append(frame.quality.overall)
        for fw in extractor.push(frame):
            est = engine.update(fw)
            assert 0.0 <= est.engagement <= 1.0
            assert est.state is not None
            windows += 1
        if windows >= 8:
            break
    await adapter.disconnect()
    assert windows >= 8
    assert all(0.0 <= q <= 1.0 for q in qualities)


@pytest.mark.asyncio
async def test_brainflow_runtime_closed_loop(eeg_fixture: Path) -> None:
    settings = Settings(
        adapter="brainflow",
        brainflow_file=str(eeg_fixture),
        channels=4,
        sample_rate_hz=250.0,
        window_sec=0.25,
        hop_sec=0.125,
        dry_run=True,
    )
    runtime = NeuralFlowRuntime(settings)
    if hasattr(runtime.adapter, "realtime"):
        runtime.adapter.realtime = False  # type: ignore[attr-defined]
    ticks = await runtime.run(duration_sec=1.0)
    assert len(ticks) >= 1
    assert ticks[-1].flow.confidence >= 0.0
    assert ticks[-1].decision.mode is not None
    # Quality present on ticks
    assert 0.0 <= ticks[-1].quality_overall <= 1.0


@pytest.mark.asyncio
async def test_brainflow_feature_latency_budget(eeg_fixture: Path) -> None:
    """Feature extract + flow update should stay under open-EEG guidance budget."""
    adapter = BrainFlowAdapter(
        file_path=str(eeg_fixture),
        chunk_samples=64,
        sample_rate_hz=250.0,
        realtime=False,
    )
    meta = await adapter.connect()
    extractor = FeatureExtractor(
        sample_rate_hz=meta.sampling_rate_hz,
        window_sec=0.5,
        hop_sec=0.25,
    )
    engine = FlowEngine()
    times_ms: list[float] = []
    windows = 0
    async for frame in adapter.stream():
        t0 = time.perf_counter()
        for fw in extractor.push(frame):
            engine.update(fw)
            windows += 1
        times_ms.append((time.perf_counter() - t0) * 1000.0)
        if windows >= 15:
            break
    await adapter.disconnect()
    assert times_ms
    times_ms.sort()
    p95 = times_ms[int(0.95 * (len(times_ms) - 1))]
    # LATENCY_BUDGET.md: feature ~50ms + flow ~20ms → 80ms guidance
    assert p95 <= 80.0, f"p95 feature→flow {p95:.2f}ms exceeds 80ms budget"


def test_resolve_brainflow_file_paths(eeg_fixture: Path) -> None:
    abs_path = resolve_brainflow_file(str(eeg_fixture))
    assert Path(abs_path).is_file()
    by_name = resolve_brainflow_file("synthetic_eeg.csv")
    assert Path(by_name).is_file()
    default = resolve_brainflow_file("")
    assert Path(default).is_file()


def test_doctor_brainflow_path() -> None:
    report = run_doctor(brainflow=True)
    names = {c.name: c for c in report.checks}
    assert "brainflow_fixture" in names
    assert names["brainflow_fixture"].ok
    assert names["brainflow_file_contract"].ok
    assert names["brainflow_latency_smoke"].ok
    assert names["brainflow_runtime_loop"].ok
    assert report.ok, [c for c in report.checks if not c.ok]


def test_npy_file_mode(tmp_path: Path) -> None:
    """BrainFlow adapter accepts channels×samples .npy files."""
    arr = np.random.randn(4, 512).astype(np.float64) * 10.0
    path = tmp_path / "synth.npy"
    np.save(path, arr)

    async def _run() -> None:
        ad = BrainFlowAdapter(file_path=str(path), chunk_samples=32, realtime=False)
        meta = await ad.connect()
        assert meta.n_channels == 4
        n = 0
        async for _frame in ad.stream():
            n += 1
            if n >= 2:
                break
        await ad.disconnect()
        assert n == 2

    import asyncio

    asyncio.run(_run())
