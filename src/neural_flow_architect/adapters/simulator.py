"""Synthetic multichannel source with latent engagement dynamics."""

from __future__ import annotations

import asyncio
import math
import time
from collections.abc import AsyncIterator

import numpy as np

from neural_flow_architect.core.types import (
    ChannelLayout,
    IntentEvent,
    NeuralFrame,
    QualityFlags,
    SourceKind,
    StreamMetadata,
)


class SimulatorAdapter:
    """Generates deterministic-ish EEG-like noise driven by a latent flow trajectory."""

    name = "simulator"

    def __init__(
        self,
        n_channels: int = 8,
        sample_rate_hz: float = 250.0,
        chunk_samples: int = 64,
        seed: int = 42,
        scripted: bool = True,
    ) -> None:
        self.n_channels = n_channels
        self.sample_rate_hz = sample_rate_hz
        self.chunk_samples = chunk_samples
        self.seed = seed
        self.scripted = scripted
        self._rng = np.random.default_rng(seed)
        self._seq = 0
        self._t0 = time.time()
        self._connected = False
        self._meta = StreamMetadata(
            source_kind=SourceKind.SIMULATOR,
            sampling_rate_hz=sample_rate_hz,
            n_channels=n_channels,
            layout=ChannelLayout(
                names=[f"sim_{i}" for i in range(n_channels)],
                units="a.u.",
            ),
            vendor="nfa-simulator",
            adapter_name=self.name,
        )

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
        return {"raw_frames", "scripted_latent"}

    def intents(self) -> AsyncIterator[IntentEvent] | None:
        return None

    def _latent_engagement(self, t: float) -> float:
        """Smooth script: low → rise → flow plateau → dip → recovery."""
        if not self.scripted:
            return 0.5 + 0.2 * math.sin(t / 12.0)
        cycle = t % 120.0
        if cycle < 15:
            return 0.25 + cycle / 60.0
        if cycle < 45:
            return 0.55 + (cycle - 15) / 60.0
        if cycle < 75:
            return 0.85
        if cycle < 90:
            return 0.85 - (cycle - 75) / 30.0
        if cycle < 105:
            return 0.35
        return 0.35 + (cycle - 105) / 40.0

    def stream(self) -> AsyncIterator[NeuralFrame]:
        return self._stream()

    async def _stream(self) -> AsyncIterator[NeuralFrame]:
        if not self._connected:
            await self.connect()
        dt = self.chunk_samples / self.sample_rate_hz
        while self._connected:
            t = time.time() - self._t0
            eng = float(np.clip(self._latent_engagement(t), 0.0, 1.0))
            # Band-limited-ish noise: stronger beta-like component when engaged
            noise = self._rng.normal(0.0, 1.0, size=(self.n_channels, self.chunk_samples))
            t_axis = np.arange(self.chunk_samples) / self.sample_rate_hz
            beta = np.sin(2 * np.pi * (12 + 10 * eng) * t_axis) * (0.3 + 0.9 * eng)
            alpha = np.sin(2 * np.pi * 10 * t_axis) * (0.6 * (1.0 - eng))
            data = noise * (0.4 + 0.2 * (1 - eng)) + beta + alpha
            data = data.astype(np.float64)
            frame = NeuralFrame(
                seq=self._seq,
                timestamp_ns=time.time_ns(),
                data=data,
                quality=QualityFlags(overall=1.0),
            )
            self._seq += 1
            yield frame
            await asyncio.sleep(dt)
