"""Policy router — multi-agent modules coordinated by mode."""

from __future__ import annotations

from neural_flow_architect.agent.policies.protector import propose_protect
from neural_flow_architect.agent.policies.reentry import propose_reentry
from neural_flow_architect.agent.policies.transition import propose_transition
from neural_flow_architect.core.types import ActionProposal, AgentMode, WorldSnapshot


def propose_actions(mode: AgentMode, snapshot: WorldSnapshot) -> list[ActionProposal]:
    """Route to the active specialist module; returns score-sorted proposals."""
    if mode in {AgentMode.IDLE, AgentMode.IDLE_DEGRADED}:
        return []

    if mode == AgentMode.PROTECT:
        proposals = propose_protect(snapshot)
    elif mode == AgentMode.RE_ENTER:
        proposals = propose_reentry(snapshot)
    elif mode == AgentMode.TRANSITION:
        proposals = propose_transition(snapshot)
    else:
        proposals = []

    # Hard gate: never propose medium+ IoT when quality is poor (extra safety)
    if snapshot.quality.overall < 0.4:
        proposals = [p for p in proposals if not p.tool_id.startswith("iot.")]

    return sorted(proposals, key=lambda p: p.score, reverse=True)
