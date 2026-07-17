"""BrainFlow adapter — live boards, synthetic board, and CSV/numpy file replay.

Install optional extra: ``pip install -e ".[brainflow]"``

Common board IDs (see BrainFlow docs):
  -1  synthetic board (no hardware; great for demos/CI if BrainFlow installed)
   0  Cyton
  2  Ganglion
  …
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from pathlib import Path

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
    Streams EEG samples from a BrainFlow board.

    Parameters
    ----------
    board_id:
        BrainFlow board id. Default -1 = synthetic (no hardware).
    serial_port:
        Device serial port when required by the board.
    file_path:
        Optional path to a CSV/NPY recording for offline replay
        (used when ``playback`` is True or file_path is set with board synthetic).
    stall_timeout_sec:
        If no samples arrive for this long, emit a dropout quality frame and
        attempt soft recovery (fail-safe signal for the runtime watchdog).
    """

    name = "brainflow"

    def __init__(
        self,
        board_id: int = -1,
        serial_port: str = "",
        chunk_samples: int = 64,
        file_path: str = "",
        stall_timeout_sec: float = 3.0,
        max_reconnects: int = 3,
    ) -> None:
        self.board_id = board_id
        self.serial_port = serial_port
        self.chunk_samples = chunk_samples
        self.file_path = file_path.strip()
        self.stall_timeout_sec = stall_timeout_sec
        self.max_reconnects = max_reconnects
        self._board = None
        self._meta: StreamMetadata | None = None
        self._seq = 0
        self._connected = False
        self._eeg_channels: list[int] = []
        self._sample_rate = 250.0
        self._last_sample_mono = 0.0
        self._reconnects = 0
        # File replay path (no BrainFlow required if only numpy/csv)
        self._file_mode = bool(self.file_path)
        self._file_data: np.ndarray | None = None
        self._file_pos = 0

    def _import_brainflow(self) -> tuple[object, object]:
        try:
            from brainflow.board_shim import BoardShim, BrainFlowInputParams
        except ImportError as exc:  # pragma: no cover - optional dep
            raise AdapterError(
                "BrainFlow is not installed. Run: pip install -e '.[brainflow]'\n"
                "Or use adapter=simulator / adapter=replay without BrainFlow."
            ) from exc
        return BoardShim, BrainFlowInputParams

    def _load_file(self) -> None:
        path = Path(self.file_path)
        if not path.exists():
            raise AdapterError(f"BrainFlow file not found: {path}")
        if path.suffix.lower() == ".npy":
            arr = np.load(path)
        else:
            # CSV: rows = samples, cols = channels (or transpose if needed)
            arr = np.loadtxt(path, delimiter=",")
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        # Prefer (channels, samples)
        if arr.shape[0] > arr.shape[1]:
            arr = arr.T
        self._file_data = arr.astype(np.float64)
        self._file_pos = 0
        self._sample_rate = 250.0
        n_ch = self._file_data.shape[0]
        self._meta = StreamMetadata(
            source_kind=SourceKind.REPLAY,
            sampling_rate_hz=self._sample_rate,
            n_channels=n_ch,
            layout=ChannelLayout(names=[f"ch{i}" for i in range(n_ch)], units="uV"),
            vendor="brainflow-file",
            adapter_name=self.name,
        )

    async def connect(self) -> StreamMetadata:
        if self._file_mode:
            self._load_file()
            self._connected = True
            self._seq = 0
            self._last_sample_mono = time.monotonic()
            assert self._meta is not None
            return self._meta

        BoardShim, BrainFlowInputParams = self._import_brainflow()
        params = BrainFlowInputParams()
        if self.serial_port:
            params.serial_port = self.serial_port
        if self.file_path:
            # Some BrainFlow versions support file as playback via params.file
            try:
                params.file = self.file_path
            except Exception:
                pass

        try:
            board = BoardShim(self.board_id, params)
            board.prepare_session()
            board.start_stream()
        except Exception as exc:
            raise AdapterError(
                f"BrainFlow failed to start board_id={self.board_id}: {exc}\n"
                "Tip: board_id=-1 is synthetic (no hardware)."
            ) from exc

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
        self._last_sample_mono = time.monotonic()
        self._reconnects = 0
        return self._meta

    async def disconnect(self) -> None:
        self._connected = False
        if self._board is not None:
            try:
                self._board.stop_stream()
                self._board.release_session()
            except Exception:
                pass
            finally:
                self._board = None
        self._file_data = None

    def metadata(self) -> StreamMetadata:
        if self._meta is None:
            raise AdapterError("Not connected")
        return self._meta

    async def health(self) -> QualityFlags:
        if not self._connected:
            return QualityFlags(dropout=True, overall=0.0)
        stall = time.monotonic() - self._last_sample_mono
        if stall > self.stall_timeout_sec:
            return QualityFlags(dropout=True, overall=0.1, high_noise=True)
        return QualityFlags(overall=0.9)

    def capabilities(self) -> set[str]:
        caps = {"raw_frames", "open_eeg", "brainflow"}
        if self._file_mode:
            caps.add("file_replay")
        return caps

    def intents(self) -> AsyncIterator[IntentEvent] | None:
        return None

    def stream(self) -> AsyncIterator[NeuralFrame]:
        return self._stream()

    async def _stream(self) -> AsyncIterator[NeuralFrame]:
        if not self._connected:
            await self.connect()
        if self._file_mode:
            async for frame in self._stream_file():
                yield frame
            return
        assert self._board is not None
        assert self._meta is not None
        empty_streak = 0
        while self._connected:
            try:
                data = self._board.get_current_board_data(self.chunk_samples)
            except Exception:
                empty_streak += 1
                data = None
            if data is None or getattr(data, "size", 0) == 0 or data.shape[1] == 0:
                empty_streak += 1
                # Stall / dropout signal for fail-safe watchdog
                if empty_streak > 25:
                    self._last_sample_mono = time.monotonic() - self.stall_timeout_sec - 0.1
                    yield NeuralFrame(
                        seq=self._seq,
                        timestamp_ns=time.time_ns(),
                        data=np.zeros((self._meta.n_channels, self.chunk_samples)),
                        quality=QualityFlags(dropout=True, overall=0.05),
                    )
                    self._seq += 1
                    empty_streak = 0
                    await self._try_reconnect()
                await asyncio.sleep(0.02)
                continue
            empty_streak = 0
            eeg = data[self._eeg_channels, :].astype(np.float64)
            quality = _estimate_quality(eeg)
            self._last_sample_mono = time.monotonic()
            frame = NeuralFrame(
                seq=self._seq,
                timestamp_ns=time.time_ns(),
                data=eeg,
                quality=quality,
            )
            self._seq += 1
            yield frame
            await asyncio.sleep(max(self.chunk_samples / self._sample_rate / 2, 0.01))

    async def _stream_file(self) -> AsyncIterator[NeuralFrame]:
        assert self._file_data is not None
        assert self._meta is not None
        n_ch, n_samp = self._file_data.shape
        dt = self.chunk_samples / self._sample_rate
        while self._connected:
            if self._file_pos >= n_samp:
                self._file_pos = 0  # loop
            end = min(self._file_pos + self.chunk_samples, n_samp)
            chunk = self._file_data[:, self._file_pos : end]
            if chunk.shape[1] < self.chunk_samples:
                pad = np.zeros((n_ch, self.chunk_samples - chunk.shape[1]))
                chunk = np.concatenate([chunk, pad], axis=1)
            self._file_pos = end
            quality = _estimate_quality(chunk)
            self._last_sample_mono = time.monotonic()
            yield NeuralFrame(
                seq=self._seq,
                timestamp_ns=time.time_ns(),
                data=chunk,
                quality=quality,
            )
            self._seq += 1
            await asyncio.sleep(dt)

    async def _try_reconnect(self) -> None:
        if self._reconnects >= self.max_reconnects or self._file_mode:
            return
        self._reconnects += 1
        try:
            await self.disconnect()
            await asyncio.sleep(0.5)
            await self.connect()
        except Exception:
            self._connected = False


def _estimate_quality(eeg: np.ndarray) -> QualityFlags:
    if eeg.size == 0:
        return QualityFlags(dropout=True, overall=0.0)
    ch_std = np.std(eeg, axis=1)
    flat = bool(np.mean(ch_std) < 1e-6)
    clip = bool(np.max(np.abs(eeg)) > 500.0)
    dead = bool(np.mean(np.mean(np.abs(eeg), axis=1) < 1e-8) > 0.5)
    high_noise = bool(np.median(ch_std) > 80.0)
    overall = 1.0
    if flat:
        overall -= 0.5
    if clip:
        overall -= 0.3
    if dead:
        overall -= 0.4
    if high_noise:
        overall -= 0.2
    return QualityFlags(
        flatline=flat,
        clipping=clip,
        dropout=dead,
        high_noise=high_noise,
        overall=float(max(0.0, min(1.0, overall))),
    )
