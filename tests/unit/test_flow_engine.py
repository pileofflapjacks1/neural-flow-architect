"""Flow state machine unit tests."""

from __future__ import annotations

from neural_flow_architect.core.types import FeatureWindow, FlowState, QualityFlags
from neural_flow_architect.flow.engine import FlowEngine


def _window(engagement: float, **kwargs: float) -> FeatureWindow:
    features = {
        "engagement_proxy": engagement,
        "arousal_proxy": kwargs.get("arousal_proxy", 0.5),
        "self_ref_proxy": kwargs.get("self_ref_proxy", 0.3),
        "ease_proxy": kwargs.get("ease_proxy", 0.6),
        "variance": 1.0,
    }
    return FeatureWindow(
        timestamp_ns=1_000_000_000,
        features=features,
        quality=QualityFlags(overall=1.0),
    )


def test_low_to_flow_progression() -> None:
    engine = FlowEngine(protect_engagement_threshold=0.6, deep_flow_engagement_threshold=0.8)
    # Warm EMA with low
    for _ in range(5):
        est = engine.update(_window(0.2))
    assert est.state in {FlowState.LOW, FlowState.FATIGUED, FlowState.UNKNOWN}

    for _ in range(20):
        est = engine.update(_window(0.75, ease_proxy=0.7))
    assert est.state in {FlowState.PRE_FLOW, FlowState.FLOW, FlowState.DEEP_FLOW}

    for _ in range(20):
        est = engine.update(_window(0.92, ease_proxy=0.8))
    assert est.state in {FlowState.FLOW, FlowState.DEEP_FLOW}


def test_low_confidence_unknown() -> None:
    engine = FlowEngine()
    w = FeatureWindow(
        timestamp_ns=1,
        features={"engagement_proxy": 0.9, "variance": 1.0},
        quality=QualityFlags(overall=0.1, dropout=True),
    )
    est = engine.update(w)
    assert est.state == FlowState.UNKNOWN
    assert est.confidence < 0.35
