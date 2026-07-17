"""Adapter factory."""

from __future__ import annotations

from pathlib import Path

from neural_flow_architect.adapters.base import AdapterError, BCIAdapter
from neural_flow_architect.adapters.simulator import SimulatorAdapter
from neural_flow_architect.core.settings import Settings


def _default_fixture_path() -> Path:
    """Locate shipped synthetic trajectory; fall back to CWD for editable installs."""
    here = Path(__file__).resolve()
    candidates = [
        here.parents[3] / "tests" / "fixtures" / "demo_trajectory.json",  # repo root via src/
        here.parents[2] / "tests" / "fixtures" / "demo_trajectory.json",
        Path.cwd() / "tests" / "fixtures" / "demo_trajectory.json",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]



def build_adapter(settings: Settings) -> BCIAdapter:
    name = settings.adapter
    if name == "simulator":
        return SimulatorAdapter(
            n_channels=settings.channels,
            sample_rate_hz=settings.sample_rate_hz,
            seed=settings.simulator_seed,
        )
    if name == "neuralink_stub":
        from neural_flow_architect.adapters.neuralink_stub import NeuralinkStubAdapter

        return NeuralinkStubAdapter(
            n_channels=max(settings.channels, 64),
            sample_rate_hz=settings.sample_rate_hz,
        )
    if name == "brainflow":
        from neural_flow_architect.adapters.brainflow_adapter import BrainFlowAdapter

        return BrainFlowAdapter(
            board_id=settings.brainflow_board_id,
            serial_port=settings.brainflow_serial_port,
        )
    if name == "replay":
        from neural_flow_architect.adapters.replay import ReplayAdapter

        path = settings.replay_path or str(_default_fixture_path())
        return ReplayAdapter(
            trajectory_path=path,
            n_channels=settings.channels,
            sample_rate_hz=settings.sample_rate_hz,
            loop=settings.replay_loop,
        )
    raise AdapterError(f"Unknown adapter: {name}")
