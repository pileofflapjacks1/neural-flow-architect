"""Adapter factory."""

from __future__ import annotations

from neural_flow_architect.adapters.base import AdapterError, BCIAdapter
from neural_flow_architect.adapters.simulator import SimulatorAdapter
from neural_flow_architect.core.settings import Settings


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
        # Replay can be added as a dedicated adapter; fall back to simulator messaging.
        raise AdapterError(
            "Replay adapter not yet implemented — use simulator or provide fixtures path in Phase 1."
        )
    raise AdapterError(f"Unknown adapter: {name}")
