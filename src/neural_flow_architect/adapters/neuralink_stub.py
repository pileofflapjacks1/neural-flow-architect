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

# Demo cycle of control intents a future implant user might trigger
_DEMO_INTENT_CYCLE = (
    "pause_agent",
    "resume_agent",
    "recipe_study",
    "undo",
    "rest_mode",
    "label_flow_yes",
)


class NeuralinkStubAdapter:
    """High-channel synthetic feature frames + cycling control intents."""

    name = "neuralink_stub"

    def __init__(
        self,
        n_channels: int = 1024,
        sample_rate_hz: float = 200.0,
        chunk_samples: int = 20,
        seed: int = 7,
        intent_interval_sec: float = 12.0,
        intent_confidence: float = 0.85,
    ) -> None:
        self.n_channels = n_channels
        self.sample_rate_hz = sample_rate_hz
        self.chunk_samples = chunk_samples
        self.intent_interval_sec = intent_interval_sec
        self.intent_confidence = intent_confidence
        self._rng = np.random.default_rng(seed)
        self._seq = 0
        self._intent_seq = 0
        self._intent_idx = 0
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
            await asyncio.sleep(self.intent_interval_sec)
            if not self._connected:
                break
            intent_type = _DEMO_INTENT_CYCLE[self._intent_idx % len(_DEMO_INTENT_CYCLE)]
            self._intent_idx += 1
            self._intent_seq += 1
            yield IntentEvent(
                seq=self._intent_seq,
                timestamp_ns=time.time_ns(),
                intent_type=intent_type,
                payload={"source": "neuralink_stub_demo"},
                confidence=self.intent_confidence,
            )

    def stream(self) -> AsyncIterator[NeuralFrame]:
        return self._stream()

    async def _stream(self) -> AsyncIterator[NeuralFrame]:
        if not self._connected:
            await self.connect()
        dt = self.chunk_samples / self.sample_rate_hz
        while self._connected:
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
