"""Agent mode selection."""

from __future__ import annotations

from neural_flow_architect.core.quiet_hours import QuietHours
from neural_flow_architect.core.types import AgentMode, FlowState, WorldSnapshot


def select_mode(
    snapshot: WorldSnapshot,
    *,
    min_confidence: float = 0.45,
    min_quality: float = 0.35,
) -> AgentMode:
    if snapshot.preferences.agent_paused:
        return AgentMode.IDLE

    if snapshot.quality.overall < min_quality or snapshot.flow.confidence < min_confidence:
        return AgentMode.IDLE_DEGRADED

    state = snapshot.flow.state
    eng = snapshot.flow.engagement

    # Quiet hours: avoid aggressive protect; still allow transition/rest
    qh = QuietHours(
        enabled=snapshot.preferences.quiet_hours_enabled,
        start_hour=snapshot.preferences.quiet_hours_start,
        end_hour=snapshot.preferences.quiet_hours_end,
    )
    quiet = qh.is_quiet(snapshot.time)

    if state in {FlowState.FLOW, FlowState.DEEP_FLOW}:
        if quiet:
            # Gentle only — transition tools for wind-down rather than deep protect
            return AgentMode.TRANSITION if eng < 0.75 else AgentMode.IDLE
        return AgentMode.PROTECT
    if state == FlowState.PRE_FLOW and eng >= 0.5:
        return AgentMode.IDLE if quiet else AgentMode.PROTECT
    if state == FlowState.FATIGUED:
        return AgentMode.TRANSITION
    if state == FlowState.POST_FLOW:
        return AgentMode.TRANSITION if eng < 0.45 else AgentMode.RE_ENTER
    if state == FlowState.LOW and snapshot.context.user_goal:
        return AgentMode.IDLE if quiet else AgentMode.RE_ENTER
    if state == FlowState.LOW:
        return AgentMode.IDLE
    return AgentMode.IDLE
