"""Replay adapter — scripted synthetic trajectories (no real neural data)."""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator
from pathlib import Path

import numpy as np

from neural_flow_architect.core.types import (
    ChannelLayout,
    IntentEvent,
    NeuralFrame,
    QualityFlags,
    SourceKind,
    StreamMetadata,
)


def default_trajectory() -> list[dict[str, float]]:
    """Multi-minute-like script compressed for demos (seconds)."""
    return [
        {"t": 0.0, "engagement": 0.22},
        {"t": 8.0, "engagement": 0.35},
        {"t": 18.0, "engagement": 0.55},
        {"t": 28.0, "engagement": 0.72},
        {"t": 45.0, "engagement": 0.86},
        {"t": 60.0, "engagement": 0.88},
        {"t": 72.0, "engagement": 0.55},
        {"t": 85.0, "engagement": 0.30},
        {"t": 100.0, "engagement": 0.48},
        {"t": 115.0, "engagement": 0.70},
        {"t": 130.0, "engagement": 0.25},
    ]


def load_trajectory(path: Path | None) -> list[dict[str, float]]:
    if path is None or not path.exists():
        return default_trajectory()
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "trajectory" in data:
        traj = data["trajectory"]
    else:
        traj = data
    if not isinstance(traj, list) or not traj:
        return default_trajectory()
    return [{"t": float(p["t"]), "engagement": float(p["engagement"])} for p in traj]


def _interp_engagement(trajectory: list[dict[str, float]], t: float) -> float:
    if t <= trajectory[0]["t"]:
        return trajectory[0]["engagement"]
    if t >= trajectory[-1]["t"]:
        return trajectory[-1]["engagement"]
    for i in range(1, len(trajectory)):
        a, b = trajectory[i - 1], trajectory[i]
        if a["t"] <= t <= b["t"]:
            span = max(b["t"] - a["t"], 1e-9)
            w = (t - a["t"]) / span
            return float(a["engagement"] * (1 - w) + b["engagement"] * w)
    return trajectory[-1]["engagement"]


class ReplayAdapter:
    """
    Generates multichannel synthetic frames driven by a JSON trajectory.

    Never contains real human neural recordings — safe for public fixtures.
    """

    name = "replay"

    def __init__(
        self,
        trajectory_path: Path | str | None = None,
        n_channels: int = 8,
        sample_rate_hz: float = 250.0,
        chunk_samples: int = 64,
        seed: int = 99,
        loop: bool = True,
        realtime: bool = True,
    ) -> None:
        self.trajectory = load_trajectory(Path(trajectory_path) if trajectory_path else None)
        self.n_channels = n_channels
        self.sample_rate_hz = sample_rate_hz
        self.chunk_samples = chunk_samples
        self.loop = loop
        self.realtime = realtime
        self._rng = np.random.default_rng(seed)
        self._seq = 0
        self._connected = False
        self._t0 = 0.0
        self._meta = StreamMetadata(
            source_kind=SourceKind.REPLAY,
            sampling_rate_hz=sample_rate_hz,
            n_channels=n_channels,
            layout=ChannelLayout(
                names=[f"replay_{i}" for i in range(n_channels)],
                units="a.u.",
            ),
            vendor="nfa-replay",
            adapter_name=self.name,
        )
        self.duration = float(self.trajectory[-1]["t"])

    async def connect(self) -> StreamMetadata:
        self._connected = True
        self._t0 = time.time()
        self._seq = 0
        return self._meta

    async def disconnect(self) -> None:
        self._connected = False

    def metadata(self) -> StreamMetadata:
        return self._meta

    async def health(self) -> QualityFlags:
        return QualityFlags(overall=1.0)

    def capabilities(self) -> set[str]:
        return {"raw_frames", "replay", "scripted_latent"}

    def intents(self) -> AsyncIterator[IntentEvent] | None:
        return None

    def stream(self) -> AsyncIterator[NeuralFrame]:
        return self._stream()

    async def _stream(self) -> AsyncIterator[NeuralFrame]:
        if not self._connected:
            await self.connect()
        dt = self.chunk_samples / self.sample_rate_hz
        sim_t = 0.0
        while self._connected:
            if sim_t > self.duration:
                if not self.loop:
                    break
                sim_t = 0.0
            eng = float(np.clip(_interp_engagement(self.trajectory, sim_t), 0.0, 1.0))
            noise = self._rng.normal(0.0, 1.0, size=(self.n_channels, self.chunk_samples))
            t_axis = np.arange(self.chunk_samples) / self.sample_rate_hz
            beta = np.sin(2 * np.pi * (12 + 10 * eng) * t_axis) * (0.3 + 0.9 * eng)
            alpha = np.sin(2 * np.pi * 10 * t_axis) * (0.6 * (1.0 - eng))
            data = (noise * (0.4 + 0.2 * (1 - eng)) + beta + alpha).astype(np.float64)
            yield NeuralFrame(
                seq=self._seq,
                timestamp_ns=time.time_ns(),
                data=data,
                quality=QualityFlags(overall=1.0),
            )
            self._seq += 1
            sim_t += dt
            if self.realtime:
                await asyncio.sleep(dt)
            else:
                await asyncio.sleep(0)
