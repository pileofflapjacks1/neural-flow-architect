"""Deterministic protect / re-enter / transition policies."""

from __future__ import annotations

from neural_flow_architect.core.types import (
    ActionProposal,
    AgentMode,
    FlowState,
    ImpactLevel,
    WorldSnapshot,
)


def propose_actions(mode: AgentMode, snapshot: WorldSnapshot) -> list[ActionProposal]:
    if mode in {AgentMode.IDLE, AgentMode.IDLE_DEGRADED}:
        return []

    flow = snapshot.flow
    causes_base = [
        {"signal": "state", "value": flow.state.value},
        {"signal": "engagement", "value": round(flow.engagement, 3)},
        {"signal": "confidence", "value": round(flow.confidence, 3)},
        {"signal": "minutes_in_state", "value": round(flow.minutes_in_state, 2)},
    ]

    if mode == AgentMode.PROTECT:
        proposals = [
            ActionProposal(
                tool_id="ui.set_density",
                impact=ImpactLevel.LOW,
                params={"density": "minimal"},
                score=0.7,
                causes=causes_base
                + [{"signal": "reason", "value": "reduce UI chrome during engagement"}],
            ),
            ActionProposal(
                tool_id="notify.suppress_noncritical",
                impact=ImpactLevel.MEDIUM,
                params={},
                score=0.9 if flow.state in {FlowState.FLOW, FlowState.DEEP_FLOW} else 0.6,
                causes=causes_base
                + [{"signal": "reason", "value": "protect sustained engagement"}],
            ),
            ActionProposal(
                tool_id="focus.enable",
                impact=ImpactLevel.MEDIUM,
                params={},
                score=0.8,
                causes=causes_base + [{"signal": "reason", "value": "enter focus profile"}],
            ),
        ]
        if snapshot.preferences.allow_iot and snapshot.preferences.protect_style == "assertive":
            proposals.append(
                ActionProposal(
                    tool_id="iot.lights.dim_for_focus",
                    impact=ImpactLevel.MEDIUM,
                    params={},
                    score=0.55,
                    causes=causes_base
                    + [{"signal": "reason", "value": "supportive ambient lighting"}],
                )
            )
        return sorted(proposals, key=lambda p: p.score, reverse=True)

    if mode == AgentMode.RE_ENTER:
        return [
            ActionProposal(
                tool_id="ui.set_density",
                impact=ImpactLevel.LOW,
                params={"density": "calm"},
                score=0.5,
                causes=causes_base
                + [{"signal": "reason", "value": "gentle scaffold for re-entry"}],
            ),
            ActionProposal(
                tool_id="focus.enable",
                impact=ImpactLevel.MEDIUM,
                params={},
                score=0.45,
                causes=causes_base
                + [{"signal": "reason", "value": "optional focus frame for restart"}],
            ),
        ]

    if mode == AgentMode.TRANSITION:
        return [
            ActionProposal(
                tool_id="notify.allow_all",
                impact=ImpactLevel.LOW,
                params={},
                score=0.7,
                causes=causes_base
                + [{"signal": "reason", "value": "restore awareness after flow"}],
            ),
            ActionProposal(
                tool_id="focus.disable",
                impact=ImpactLevel.LOW,
                params={},
                score=0.65,
                causes=causes_base + [{"signal": "reason", "value": "graceful wind-down"}],
            ),
            ActionProposal(
                tool_id="ui.set_density",
                impact=ImpactLevel.LOW,
                params={"density": "normal"},
                score=0.5,
                causes=causes_base,
            ),
        ]

    return []
