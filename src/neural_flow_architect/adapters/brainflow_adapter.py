"""BrainFlow adapter — optional dependency for open EEG boards."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator

import numpy as np

from neural_flow_architect.adapters.base import AdapterError
from neural_flow_architect.core.types import (
    ChannelLayout,
    IntentEvent,
    NeuralFrame,
    QualityFlags,
    SourceKind,
    StreamMetadata,
)


class BrainFlowAdapter:
    """
    Streams samples from a BrainFlow board.

    Install optional extra: ``pip install -e ".[brainflow]"``
    """

    name = "brainflow"

    def __init__(
        self,
        board_id: int = -1,
        serial_port: str = "",
        chunk_samples: int = 64,
    ) -> None:
        self.board_id = board_id
        self.serial_port = serial_port
        self.chunk_samples = chunk_samples
        self._board = None
        self._meta: StreamMetadata | None = None
        self._seq = 0
        self._connected = False
        self._eeg_channels: list[int] = []
        self._sample_rate = 250.0

    def _import_brainflow(self) -> tuple[object, object]:
        try:
            from brainflow.board_shim import BoardShim, BrainFlowInputParams
        except ImportError as exc:  # pragma: no cover - optional dep
            raise AdapterError(
                "BrainFlow is not installed. Run: pip install -e '.[brainflow]'"
            ) from exc
        return BoardShim, BrainFlowInputParams

    async def connect(self) -> StreamMetadata:
        BoardShim, BrainFlowInputParams = self._import_brainflow()
        params = BrainFlowInputParams()
        if self.serial_port:
            params.serial_port = self.serial_port

        board = BoardShim(self.board_id, params)
        board.prepare_session()
        board.start_stream()
        self._board = board
        self._sample_rate = float(BoardShim.get_sampling_rate(self.board_id))
        self._eeg_channels = list(BoardShim.get_eeg_channels(self.board_id))
        n_ch = len(self._eeg_channels) or 1
        self._meta = StreamMetadata(
            source_kind=SourceKind.OPEN_EEG,
            sampling_rate_hz=self._sample_rate,
            n_channels=n_ch,
            layout=ChannelLayout(
                names=[f"ch{c}" for c in self._eeg_channels],
                units="uV",
            ),
            vendor="brainflow",
            adapter_name=self.name,
        )
        self._connected = True
        self._seq = 0
        return self._meta

    async def disconnect(self) -> None:
        self._connected = False
        if self._board is not None:
            try:
                self._board.stop_stream()
                self._board.release_session()
            finally:
                self._board = None

    def metadata(self) -> StreamMetadata:
        if self._meta is None:
            raise AdapterError("Not connected")
        return self._meta

    async def health(self) -> QualityFlags:
        return QualityFlags(overall=1.0 if self._connected else 0.0)

    def capabilities(self) -> set[str]:
        return {"raw_frames", "open_eeg"}

    def intents(self) -> AsyncIterator[IntentEvent] | None:
        return None

    def stream(self) -> AsyncIterator[NeuralFrame]:
        return self._stream()

    async def _stream(self) -> AsyncIterator[NeuralFrame]:
        if not self._connected or self._board is None:
            await self.connect()
        assert self._board is not None
        assert self._meta is not None
        while self._connected:
            data = self._board.get_current_board_data(self.chunk_samples)
            if data is None or data.size == 0 or data.shape[1] == 0:
                await asyncio.sleep(0.02)
                continue
            eeg = data[self._eeg_channels, :].astype(np.float64)
            quality = _estimate_quality(eeg)
            frame = NeuralFrame(
                seq=self._seq,
                timestamp_ns=time.time_ns(),
                data=eeg,
                quality=quality,
            )
            self._seq += 1
            yield frame
            await asyncio.sleep(max(self.chunk_samples / self._sample_rate / 2, 0.01))


def _estimate_quality(eeg: np.ndarray) -> QualityFlags:
    if eeg.size == 0:
        return QualityFlags(dropout=True, overall=0.0)
    flat = bool(np.mean(np.std(eeg, axis=1)) < 1e-6)
    clip = bool(np.max(np.abs(eeg)) > 500.0)  # heuristic µV-ish
    overall = 1.0
    if flat:
        overall -= 0.5
    if clip:
        overall -= 0.3
    return QualityFlags(
        flatline=flat,
        clipping=clip,
        overall=float(max(0.0, min(1.0, overall))),
    )
