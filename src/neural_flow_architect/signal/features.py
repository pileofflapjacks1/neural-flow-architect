"""Feature extraction from neural frames (prototype heuristics)."""

from __future__ import annotations

from collections import deque

import numpy as np
from numpy.typing import NDArray

from neural_flow_architect.core.types import FeatureWindow, NeuralFrame, QualityFlags


class FeatureExtractor:
    """
    Sliding-window band-power style features.

    These are **prototype proxies** for engagement-related signal structure,
    not clinical biomarkers. Suitable for simulator + open EEG demos.
    """

    def __init__(
        self,
        sample_rate_hz: float = 250.0,
        window_sec: float = 1.0,
        hop_sec: float = 0.25,
    ) -> None:
        self.sample_rate_hz = sample_rate_hz
        self.window_samples = max(int(window_sec * sample_rate_hz), 8)
        self.hop_samples = max(int(hop_sec * sample_rate_hz), 1)
        self._buffer: deque[NDArray[np.float64]] = deque()
        self._buffered_samples = 0
        self._last_quality = QualityFlags()

    def reset(self) -> None:
        self._buffer.clear()
        self._buffered_samples = 0

    def push(self, frame: NeuralFrame) -> list[FeatureWindow]:
        self._last_quality = frame.quality
        self._buffer.append(frame.data)
        self._buffered_samples += frame.data.shape[1]
        windows: list[FeatureWindow] = []
        while self._buffered_samples >= self.window_samples:
            window = self._assemble_window()
            features = self._compute(window)
            windows.append(
                FeatureWindow(
                    timestamp_ns=frame.timestamp_ns,
                    features=features,
                    quality=self._last_quality,
                )
            )
            self._consume(self.hop_samples)
        return windows

    def _assemble_window(self) -> NDArray[np.float64]:
        chunks = list(self._buffer)
        joined = np.concatenate(chunks, axis=1)
        return joined[:, : self.window_samples]

    def _consume(self, n: int) -> None:
        remaining = n
        while remaining > 0 and self._buffer:
            head = self._buffer[0]
            if head.shape[1] <= remaining:
                remaining -= head.shape[1]
                self._buffer.popleft()
            else:
                self._buffer[0] = head[:, remaining:]
                remaining = 0
        self._buffered_samples = sum(c.shape[1] for c in self._buffer)

    def _compute(self, window: NDArray[np.float64]) -> dict[str, float]:
        # window: (channels, samples)
        # Use FFT band powers as coarse proxies
        freqs = np.fft.rfftfreq(window.shape[1], d=1.0 / self.sample_rate_hz)
        spec = np.abs(np.fft.rfft(window, axis=1)) ** 2
        def band_power(lo: float, hi: float) -> float:
            mask = (freqs >= lo) & (freqs < hi)
            if not np.any(mask):
                return 0.0
            return float(np.mean(spec[:, mask]))

        theta = band_power(4, 8)
        alpha = band_power(8, 13)
        beta = band_power(13, 30)
        gamma = band_power(30, 45)
        total = theta + alpha + beta + gamma + 1e-9
        variance = float(np.mean(np.var(window, axis=1)))
        return {
            "theta_rel": theta / total,
            "alpha_rel": alpha / total,
            "beta_rel": beta / total,
            "gamma_rel": gamma / total,
            "beta_alpha_ratio": beta / (alpha + 1e-9),
            "variance": variance,
            "engagement_proxy": float(
                np.clip(0.55 * (beta / total) + 0.25 * (gamma / total) + 0.2 * (1 - alpha / total), 0, 1)
            ),
            "arousal_proxy": float(np.clip(beta / total + 0.3 * (gamma / total), 0, 1)),
            "self_ref_proxy": float(np.clip(alpha / total, 0, 1)),  # crude inverse-of-engagement stand-in
            "ease_proxy": float(np.clip(1.0 - abs((beta / total) - 0.35), 0, 1)),
        }
