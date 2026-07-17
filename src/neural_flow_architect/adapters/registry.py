"""Adapter factory."""

from __future__ import annotations

from pathlib import Path

from neural_flow_architect.adapters.base import AdapterError, BCIAdapter
from neural_flow_architect.adapters.simulator import SimulatorAdapter
from neural_flow_architect.core.settings import Settings


def _repo_fixture(*parts: str) -> Path:
    """Locate a shipped test fixture under tests/fixtures/."""
    here = Path(__file__).resolve()
    candidates = [
        here.parents[3].joinpath(*parts),  # repo root via src/layout
        here.parents[2].joinpath(*parts),
        Path.cwd().joinpath(*parts),
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def _default_fixture_path() -> Path:
    """Locate shipped synthetic trajectory; fall back to CWD for editable installs."""
    return _repo_fixture("tests", "fixtures", "demo_trajectory.json")


def default_brainflow_fixture() -> Path:
    """Shipped synthetic EEG CSV for BrainFlow file mode (no real neural data)."""
    return _repo_fixture("tests", "fixtures", "synthetic_eeg.csv")


def resolve_brainflow_file(path: str) -> str:
    """Expand relative BrainFlow file paths against CWD and known fixture locations."""
    raw = (path or "").strip()
    if not raw:
        return str(default_brainflow_fixture())
    p = Path(raw).expanduser()
    if p.is_file():
        return str(p.resolve())
    # Common relative paths from docs / contract CLI
    for candidate in (
        Path.cwd() / raw,
        default_brainflow_fixture().parent / Path(raw).name,
        _repo_fixture(*Path(raw).parts) if not Path(raw).is_absolute() else p,
    ):
        if candidate.is_file():
            return str(candidate.resolve())
    return str(p)


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

        file_path = resolve_brainflow_file(getattr(settings, "brainflow_file", "") or "")
        # File mode when path set; otherwise live/synthetic board (needs brainflow package)
        use_file = bool(getattr(settings, "brainflow_file", "") or "")
        return BrainFlowAdapter(
            board_id=settings.brainflow_board_id,
            serial_port=settings.brainflow_serial_port,
            file_path=file_path if use_file else "",
            sample_rate_hz=settings.sample_rate_hz,
            realtime=True,
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
