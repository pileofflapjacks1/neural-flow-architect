"""Signal quality assessment tests."""

from __future__ import annotations

import numpy as np

from neural_flow_architect.signal.quality import assess_window_quality


def test_clean_signal_high_quality() -> None:
    rng = np.random.default_rng(0)
    window = rng.normal(0, 1.0, size=(4, 128))
    q = assess_window_quality(window)
    assert q.overall > 0.5
    assert not q.dropout


def test_flatline_low_quality() -> None:
    window = np.zeros((4, 128))
    q = assess_window_quality(window)
    assert q.flatline or q.dropout
    assert q.overall < 0.5
