"""Insights and self-report tests."""

from __future__ import annotations

from pathlib import Path

from neural_flow_architect.core.types import FlowEstimate, FlowState
from neural_flow_architect.insights.store import InsightsStore


def test_label_and_persist(tmp_path: Path) -> None:
    store = InsightsStore(tmp_path)
    store.start_session(adapter="simulator")
    est = FlowEstimate(
        timestamp_ns=1,
        engagement=0.8,
        arousal_balance=0.5,
        self_ref_proxy=0.2,
        effort_ease=0.6,
        confidence=0.9,
        state=FlowState.FLOW,
        minutes_in_state=1.0,
    )
    store.observe_flow(est)
    store.observe_action("test explanation")
    store.add_label(True, note="deep work", state="flow", engagement=0.8)
    summary = store.end_session(persist=True)
    assert summary is not None
    assert summary.labels[0].felt_in_flow is True
    assert summary.actions_count == 1
    listed = store.list_sessions()
    assert len(listed) == 1
    assert listed[0]["labels"][0]["felt_in_flow"] is True
