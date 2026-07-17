"""Feature extractor tests."""

from __future__ import annotations

import numpy as np

from neural_flow_architect.core.types import NeuralFrame, QualityFlags
from neural_flow_architect.signal.features import FeatureExtractor


def test_feature_window_emitted() -> None:
    fx = FeatureExtractor(sample_rate_hz=250, window_sec=0.2, hop_sec=0.1)
    # 0.2s at 250Hz = 50 samples
    produced = []
    for i in range(10):
        data = np.random.randn(4, 25).astype(np.float64)
        frame = NeuralFrame(seq=i, timestamp_ns=i * 1000, data=data, quality=QualityFlags())
        produced.extend(fx.push(frame))
    assert len(produced) >= 1
    assert "engagement_proxy" in produced[0].features
    assert 0.0 <= produced[0].features["engagement_proxy"] <= 1.0
