"""Signal quality metrics for graceful degradation."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from neural_flow_architect.core.types import QualityFlags


def assess_window_quality(
    window: NDArray[np.float64],
    *,
    frame_quality: QualityFlags | None = None,
    clip_threshold: float = 200.0,
    flat_std: float = 1e-6,
    noise_std: float = 50.0,
) -> QualityFlags:
    """
    Heuristic quality from a (channels, samples) window.

    Combines adapter frame flags with window statistics. Not a clinical metric.
    """
    base = frame_quality or QualityFlags()
    if window.size == 0:
        return QualityFlags(dropout=True, overall=0.0)

    ch_std = np.std(window, axis=1)
    ch_mean_abs = np.mean(np.abs(window), axis=1)
    flat_ratio = float(np.mean(ch_std < flat_std))
    clip_ratio = float(np.mean(np.max(np.abs(window), axis=1) > clip_threshold))
    high_noise = bool(np.median(ch_std) > noise_std)
    # Channel dropout: near-zero energy channels
    dead_ratio = float(np.mean(ch_mean_abs < 1e-8))

    flatline = flat_ratio > 0.5 or base.flatline
    clipping = clip_ratio > 0.25 or base.clipping
    dropout = dead_ratio > 0.5 or base.dropout
    high_noise = high_noise or base.high_noise

    overall = float(base.overall)
    overall *= 1.0 - 0.5 * flat_ratio
    overall *= 1.0 - 0.4 * clip_ratio
    overall *= 1.0 - 0.6 * dead_ratio
    if high_noise:
        overall *= 0.75
    if dropout:
        overall = min(overall, 0.2)
    overall = float(np.clip(overall, 0.0, 1.0))

    return QualityFlags(
        clipping=clipping,
        flatline=flatline,
        high_noise=high_noise,
        dropout=dropout,
        overall=overall,
    )


def merge_quality(a: QualityFlags, b: QualityFlags) -> QualityFlags:
    return QualityFlags(
        clipping=a.clipping or b.clipping,
        flatline=a.flatline or b.flatline,
        high_noise=a.high_noise or b.high_noise,
        dropout=a.dropout or b.dropout,
        overall=min(a.overall, b.overall),
    )
