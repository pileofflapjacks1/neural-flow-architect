"""Protector agent — reduce friction when flow is emerging or present."""

from __future__ import annotations

from typing import Any

from neural_flow_architect.core.types import (
    ActionProposal,
    FlowState,
    ImpactLevel,
    WorldSnapshot,
)
from neural_flow_architect.environment.recipes import recipe_protect_bonus


def propose_protect(snapshot: WorldSnapshot) -> list[ActionProposal]:
    flow = snapshot.flow
    recipe = snapshot.context.recipe or "study"
    app_cat = snapshot.context.app_category or "unknown"
    causes: list[dict[str, Any]] = [
        {"signal": "module", "value": "protector"},
        {"signal": "state", "value": flow.state.value},
        {"signal": "engagement", "value": round(flow.engagement, 3)},
        {"signal": "confidence", "value": round(flow.confidence, 3)},
        {"signal": "minutes_in_state", "value": round(flow.minutes_in_state, 2)},
        {"signal": "recipe", "value": recipe},
        {"signal": "app_category", "value": app_cat},
    ]
    bonus = recipe_protect_bonus(recipe)
    # Soft context: protect harder in study/create apps; gentler in social
    if app_cat in {"study", "create"}:
        bonus += 0.05
    elif app_cat == "social":
        bonus -= 0.15
    deep = flow.state == FlowState.DEEP_FLOW

    proposals = [
        ActionProposal(
            tool_id="ui.set_density",
            impact=ImpactLevel.LOW,
            params={"density": "minimal" if deep else "calm"},
            score=0.7 + bonus,
            causes=causes + [{"signal": "reason", "value": "reduce UI chrome during engagement"}],
        ),
        ActionProposal(
            tool_id="notify.suppress_noncritical",
            impact=ImpactLevel.MEDIUM,
            params={},
            score=(0.95 if deep else 0.85) + bonus + (0.0 if app_cat != "social" else -0.4),
            causes=causes + [{"signal": "reason", "value": "protect sustained engagement"}],
        ),
        ActionProposal(
            tool_id="focus.enable",
            impact=ImpactLevel.MEDIUM,
            params={},
            score=0.8 + bonus,
            causes=causes + [{"signal": "reason", "value": "enter focus profile"}],
        ),
        ActionProposal(
            tool_id="recipe.apply",
            impact=ImpactLevel.LOW,
            params={"recipe": recipe},
            score=0.55 + bonus,
            causes=causes + [{"signal": "reason", "value": f"apply {recipe} environment recipe"}],
        ),
    ]
    if snapshot.preferences.allow_iot and snapshot.preferences.protect_style == "assertive":
        proposals.append(
            ActionProposal(
                tool_id="iot.lights.dim_for_focus",
                impact=ImpactLevel.MEDIUM,
                params={},
                score=0.55 + bonus,
                causes=causes + [{"signal": "reason", "value": "supportive ambient lighting"}],
            )
        )
    return proposals
