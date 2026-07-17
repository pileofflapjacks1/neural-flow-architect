"""BrainFlow file-mode tests (no BrainFlow package required)."""

from __future__ import annotations

from pathlib import Path

import pytest

from neural_flow_architect.adapters.brainflow_adapter import BrainFlowAdapter


@pytest.mark.asyncio
async def test_brainflow_csv_file_stream() -> None:
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "synthetic_eeg.csv"
    assert fixture.exists()
    adapter = BrainFlowAdapter(file_path=str(fixture), chunk_samples=32)
    meta = await adapter.connect()
    assert meta.n_channels == 4
    frames = []
    async for frame in adapter.stream():
        frames.append(frame)
        if len(frames) >= 3:
            break
    await adapter.disconnect()
    assert len(frames) == 3
    assert frames[0].data.shape[0] == 4
