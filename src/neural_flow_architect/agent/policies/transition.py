"""Transition agent — wind-down when leaving flow or fatigued."""

from __future__ import annotations

from typing import Any

from neural_flow_architect.core.types import ActionProposal, FlowState, ImpactLevel, WorldSnapshot


def propose_transition(snapshot: WorldSnapshot) -> list[ActionProposal]:
    flow = snapshot.flow
    causes: list[dict[str, Any]] = [
        {"signal": "module", "value": "transition"},
        {"signal": "state", "value": flow.state.value},
        {"signal": "engagement", "value": round(flow.engagement, 3)},
    ]
    proposals = [
        ActionProposal(
            tool_id="notify.allow_all",
            impact=ImpactLevel.LOW,
            params={},
            score=0.75,
            causes=causes + [{"signal": "reason", "value": "restore awareness after flow"}],
        ),
        ActionProposal(
            tool_id="focus.disable",
            impact=ImpactLevel.LOW,
            params={},
            score=0.7,
            causes=causes + [{"signal": "reason", "value": "graceful wind-down"}],
        ),
        ActionProposal(
            tool_id="ui.set_density",
            impact=ImpactLevel.LOW,
            params={"density": "normal"},
            score=0.55,
            causes=causes,
        ),
        ActionProposal(
            tool_id="recipe.apply",
            impact=ImpactLevel.LOW,
            params={"recipe": "rest"},
            score=0.65 if flow.state == FlowState.FATIGUED else 0.5,
            causes=causes + [{"signal": "reason", "value": "shift to rest recipe"}],
        ),
    ]
    if snapshot.preferences.allow_iot:
        proposals.append(
            ActionProposal(
                tool_id="iot.lights.restore",
                impact=ImpactLevel.LOW,
                params={},
                score=0.5,
                causes=causes + [{"signal": "reason", "value": "restore lighting"}],
            )
        )
    return proposals
