"""Stub adapter sketching a future high-bandwidth / intent API path.

This does **not** integrate with any proprietary Neuralink SDK.
It exists so the core can be developed against high-channel semantics today.
"""

from __future__ import annotations

import asyncio
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


class NeuralinkStubAdapter:
    """High-channel synthetic feature frames + occasional intent events."""

    name = "neuralink_stub"

    def __init__(
        self,
        n_channels: int = 1024,
        sample_rate_hz: float = 200.0,
        chunk_samples: int = 20,
        seed: int = 7,
    ) -> None:
        self.n_channels = n_channels
        self.sample_rate_hz = sample_rate_hz
        self.chunk_samples = chunk_samples
        self._rng = np.random.default_rng(seed)
        self._seq = 0
        self._intent_seq = 0
        self._connected = False
        self._meta = StreamMetadata(
            source_kind=SourceKind.INTRACORTICAL,
            sampling_rate_hz=sample_rate_hz,
            n_channels=n_channels,
            layout=ChannelLayout(
                names=[f"unit_{i}" for i in range(n_channels)],
                units="a.u.",
            ),
            vendor="stub",
            adapter_name=self.name,
        )

    async def connect(self) -> StreamMetadata:
        self._connected = True
        self._seq = 0
        return self._meta

    async def disconnect(self) -> None:
        self._connected = False

    def metadata(self) -> StreamMetadata:
        return self._meta

    async def health(self) -> QualityFlags:
        return QualityFlags(overall=0.95)

    def capabilities(self) -> set[str]:
        return {"raw_frames", "intents", "high_channel"}

    def intents(self) -> AsyncIterator[IntentEvent] | None:
        return self._intent_stream()

    async def _intent_stream(self) -> AsyncIterator[IntentEvent]:
        while self._connected:
            await asyncio.sleep(15.0)
            self._intent_seq += 1
            yield IntentEvent(
                seq=self._intent_seq,
                timestamp_ns=time.time_ns(),
                intent_type="pause_agent",
                payload={"source": "stub_demo"},
                confidence=0.4,
            )

    def stream(self) -> AsyncIterator[NeuralFrame]:
        return self._stream()

    async def _stream(self) -> AsyncIterator[NeuralFrame]:
        if not self._connected:
            await self.connect()
        dt = self.chunk_samples / self.sample_rate_hz
        while self._connected:
            # Sparse-ish population activity proxy
            data = self._rng.normal(0.0, 0.1, size=(self.n_channels, self.chunk_samples))
            active = self._rng.random(self.n_channels) < 0.05
            data[active] += self._rng.normal(0.0, 1.0, size=(active.sum(), self.chunk_samples))
            frame = NeuralFrame(
                seq=self._seq,
                timestamp_ns=time.time_ns(),
                data=data.astype(np.float64),
                quality=QualityFlags(overall=0.95),
            )
            self._seq += 1
            yield frame
            await asyncio.sleep(dt)
