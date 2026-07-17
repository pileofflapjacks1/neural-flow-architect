"""Adapter contract checks — golden suite for all BCI sources."""

from __future__ import annotations

import inspect
from typing import Any

from neural_flow_architect.adapters.base import BCIAdapter
from neural_flow_architect.core.types import NeuralFrame, StreamMetadata


REQUIRED_METHODS = (
    "connect",
    "disconnect",
    "metadata",
    "health",
    "stream",
    "capabilities",
    "intents",
)


def assert_adapter_interface(adapter: BCIAdapter) -> None:
    assert hasattr(adapter, "name") and isinstance(adapter.name, str)
    for method in REQUIRED_METHODS:
        assert hasattr(adapter, method), f"missing {method}"
        assert callable(getattr(adapter, method)), f"{method} not callable"


async def run_adapter_contract(
    adapter: BCIAdapter,
    *,
    max_frames: int = 3,
    timeout_sec: float = 10.0,
) -> dict[str, Any]:
    """
    Connect → read a few frames → disconnect.

    Returns a report dict; raises AssertionError on contract violations.
    """
    import asyncio

    assert_adapter_interface(adapter)
    meta = await asyncio.wait_for(adapter.connect(), timeout=timeout_sec)
    assert isinstance(meta, StreamMetadata)
    assert meta.n_channels >= 1
    assert meta.sampling_rate_hz > 0
    assert meta.adapter_name or adapter.name

    caps = adapter.capabilities()
    assert isinstance(caps, set)

    frames: list[NeuralFrame] = []
    stream = adapter.stream()
    assert inspect.isasyncgen(stream) or hasattr(stream, "__aiter__")

    async def _read() -> None:
        async for frame in stream:
            assert isinstance(frame, NeuralFrame)
            assert frame.data.ndim == 2
            assert frame.data.shape[0] == meta.n_channels or frame.data.shape[0] >= 1
            assert 0.0 <= frame.quality.overall <= 1.0
            frames.append(frame)
            if len(frames) >= max_frames:
                break

    await asyncio.wait_for(_read(), timeout=timeout_sec)
    assert len(frames) >= 1, "adapter produced no frames"

    # intents() may be None or async iterator
    intents = adapter.intents()
    if intents is not None:
        assert hasattr(intents, "__aiter__")

    health = await adapter.health()
    assert 0.0 <= health.overall <= 1.0

    await adapter.disconnect()
    return {
        "adapter": adapter.name,
        "n_channels": meta.n_channels,
        "sample_rate_hz": meta.sampling_rate_hz,
        "frames": len(frames),
        "capabilities": sorted(caps),
        "source_kind": meta.source_kind.value,
        "ok": True,
    }
