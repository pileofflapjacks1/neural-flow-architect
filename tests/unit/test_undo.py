"""Undo stack and Architect undo tests."""

from __future__ import annotations

from datetime import datetime

import pytest

from neural_flow_architect.agent.architect import Architect
from neural_flow_architect.core.types import (
    FlowEstimate,
    FlowState,
    QualityFlags,
    UserPreferences,
    WorldSnapshot,
)
from neural_flow_architect.environment.digital import DigitalOrchestrator


def _snap(state: FlowState = FlowState.FLOW, engagement: float = 0.85) -> WorldSnapshot:
    return WorldSnapshot(
        time=datetime.utcnow(),
        flow=FlowEstimate(
            timestamp_ns=1,
            engagement=engagement,
            arousal_balance=0.6,
            self_ref_proxy=0.3,
            effort_ease=0.6,
            confidence=0.9,
            state=state,
            minutes_in_state=5.0,
        ),
        quality=QualityFlags(overall=0.9),
        preferences=UserPreferences(),
    )


@pytest.mark.asyncio
async def test_undo_restores_digital_state() -> None:
    digital = DigitalOrchestrator()
    arch = Architect(digital=digital, dry_run=False)
    assert digital.density == "normal"
    decision = await arch.step(_snap())
    assert decision.results
    assert arch.undo_stack.can_undo
    # Something should have changed for protect mode
    assert digital.density != "normal" or digital.focus_enabled or digital.notifications_suppressed
    result = arch.undo_last()
    assert result.success
    # After undoing last action, earlier actions may still apply
    while arch.undo_stack.can_undo:
        arch.undo_last()
    assert digital.density == "normal"
    assert digital.focus_enabled is False
    assert digital.notifications_suppressed is False


def test_digital_restore() -> None:
    d = DigitalOrchestrator()
    d.set_focus(True)
    d.set_density("minimal")
    snap = d.snapshot()
    d.set_focus(False)
    d.set_density("normal")
    d.restore(snap)
    assert d.focus_enabled is True
    assert d.density == "minimal"
