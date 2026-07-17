"""Architect policy and governor tests."""

from __future__ import annotations

from datetime import datetime

import pytest

from neural_flow_architect.agent.architect import Architect
from neural_flow_architect.agent.policies.modes import select_mode
from neural_flow_architect.agent.policies.rules import propose_actions
from neural_flow_architect.core.types import (
    AgentMode,
    ContextSnapshot,
    FlowEstimate,
    FlowState,
    QualityFlags,
    UserPreferences,
    WorldSnapshot,
)


def _snap(
    state: FlowState,
    engagement: float = 0.8,
    *,
    paused: bool = False,
    allow_iot: bool = False,
) -> WorldSnapshot:
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
        context=ContextSnapshot(user_goal="study"),
        preferences=UserPreferences(agent_paused=paused, allow_iot=allow_iot),
    )


def test_protect_mode_on_flow() -> None:
    assert select_mode(_snap(FlowState.FLOW)) == AgentMode.PROTECT
    assert select_mode(_snap(FlowState.DEEP_FLOW)) == AgentMode.PROTECT


def test_paused_is_idle() -> None:
    assert select_mode(_snap(FlowState.FLOW, paused=True)) == AgentMode.IDLE


def test_degraded_quality_idle() -> None:
    s = _snap(FlowState.FLOW)
    s.quality.overall = 0.1
    s.flow.confidence = 0.2
    assert select_mode(s) == AgentMode.IDLE_DEGRADED


def test_protect_proposals_include_notification_suppress() -> None:
    props = propose_actions(AgentMode.PROTECT, _snap(FlowState.FLOW))
    ids = {p.tool_id for p in props}
    assert "notify.suppress_noncritical" in ids
    assert "focus.enable" in ids


@pytest.mark.asyncio
async def test_architect_step_emits_explanation() -> None:
    arch = Architect(dry_run=True)
    decision = await arch.step(_snap(FlowState.FLOW, engagement=0.85))
    assert decision.mode == AgentMode.PROTECT
    assert decision.explanations or decision.results
    if decision.explanations:
        assert "engagement" in decision.explanations[0].text.lower() or "flow" in decision.explanations[0].text.lower()
