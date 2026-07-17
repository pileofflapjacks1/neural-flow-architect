"""BCI adapter protocol and shared helpers."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from neural_flow_architect.core.types import (
    IntentEvent,
    NeuralFrame,
    QualityFlags,
    StreamMetadata,
)


@runtime_checkable
class BCIAdapter(Protocol):
    """Stable contract between hardware/SDKs and the NFA core."""

    name: str

    async def connect(self) -> StreamMetadata: ...

    async def disconnect(self) -> None: ...

    def metadata(self) -> StreamMetadata: ...

    async def health(self) -> QualityFlags: ...

    def stream(self) -> AsyncIterator[NeuralFrame]: ...

    def capabilities(self) -> set[str]: ...

    def intents(self) -> AsyncIterator[IntentEvent] | None: ...


class AdapterError(RuntimeError):
    """Raised when an adapter fails to connect or stream."""
