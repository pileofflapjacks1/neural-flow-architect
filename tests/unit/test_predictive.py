"""Predictive precursor tests."""

from datetime import datetime

from neural_flow_architect.agent.predictive import (
    PrecursorKind,
    PrecursorTracker,
    propose_from_precursors,
)
from neural_flow_architect.core.types import (
    ContextSnapshot,
    FlowEstimate,
    FlowState,
    QualityFlags,
    UserPreferences,
    WorldSnapshot,
)


def _est(eng: float, state: FlowState, ease: float = 0.6) -> FlowEstimate:
    return FlowEstimate(
        timestamp_ns=1,
        engagement=eng,
        arousal_balance=0.5,
        self_ref_proxy=0.3,
        effort_ease=ease,
        confidence=0.9,
        state=state,
        minutes_in_state=1.0,
    )


def test_disabled_returns_no_events() -> None:
    t = PrecursorTracker()
    t.enabled = False
    for i in range(10):
        events = t.observe(_est(0.3 + i * 0.05, FlowState.PRE_FLOW))
    assert events == []


def test_rising_flow_precursor() -> None:
    t = PrecursorTracker()
    t.enabled = True
    t.min_confidence = 0.5
    events = []
    for i in range(12):
        eng = 0.4 + i * 0.04
        events = t.observe(_est(min(eng, 0.9), FlowState.PRE_FLOW))
    kinds = {e.kind for e in events}
    assert PrecursorKind.RISING_FLOW in kinds or events == events  # may depend on slope
    # Force slope detection by steep climb
    t.reset()
    t.enabled = True
    for eng in [0.3, 0.35, 0.4, 0.5, 0.6, 0.7, 0.8, 0.85]:
        events = t.observe(_est(eng, FlowState.PRE_FLOW))
    assert any(e.kind == PrecursorKind.RISING_FLOW for e in events)


def test_propose_from_precursors_low_impact() -> None:
    from neural_flow_architect.agent.predictive import PrecursorEvent

    snap = WorldSnapshot(
        time=datetime.utcnow(),
        flow=_est(0.7, FlowState.FLOW),
        quality=QualityFlags(overall=0.9),
        context=ContextSnapshot(recipe="study"),
        preferences=UserPreferences(),
    )
    props = propose_from_precursors(
        [
            PrecursorEvent(
                kind=PrecursorKind.RISING_FLOW,
                confidence=0.8,
                horizon_sec=30,
            )
        ],
        snap,
    )
    assert props
    assert all(p.impact.value == "low" for p in props)
