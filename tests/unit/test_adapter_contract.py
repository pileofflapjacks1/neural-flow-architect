"""Golden contract suite for BCI adapters."""

from __future__ import annotations

from pathlib import Path

import pytest

from neural_flow_architect.adapters.brainflow_adapter import BrainFlowAdapter
from neural_flow_architect.adapters.contract import run_adapter_contract
from neural_flow_architect.adapters.neuralink_stub import NeuralinkStubAdapter
from neural_flow_architect.adapters.replay import ReplayAdapter
from neural_flow_architect.adapters.simulator import SimulatorAdapter


@pytest.mark.asyncio
async def test_simulator_contract() -> None:
    report = await run_adapter_contract(
        SimulatorAdapter(n_channels=4, sample_rate_hz=128), max_frames=2
    )
    assert report["ok"]
    assert report["frames"] >= 1


@pytest.mark.asyncio
async def test_replay_contract() -> None:
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "demo_trajectory.json"
    ad = ReplayAdapter(trajectory_path=fixture, n_channels=4, sample_rate_hz=128, realtime=False)
    report = await run_adapter_contract(ad, max_frames=2)
    assert report["ok"]


@pytest.mark.asyncio
async def test_neuralink_stub_contract() -> None:
    ad = NeuralinkStubAdapter(n_channels=32, sample_rate_hz=100, chunk_samples=10)
    report = await run_adapter_contract(ad, max_frames=2)
    assert report["ok"]
    assert "high_channel" in report["capabilities"] or report["n_channels"] >= 32


@pytest.mark.asyncio
async def test_brainflow_file_contract() -> None:
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "synthetic_eeg.csv"
    ad = BrainFlowAdapter(file_path=str(fixture), chunk_samples=32)
    report = await run_adapter_contract(ad, max_frames=2)
    assert report["ok"]
