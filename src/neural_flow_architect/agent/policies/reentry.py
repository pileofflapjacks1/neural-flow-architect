"""ReEntry agent — gentle scaffold when flow has broken but goal remains."""

from __future__ import annotations

from neural_flow_architect.core.types import ActionProposal, ImpactLevel, WorldSnapshot
from neural_flow_architect.environment.recipes import recipe_reentry_bonus


def propose_reentry(snapshot: WorldSnapshot) -> list[ActionProposal]:
    flow = snapshot.flow
    recipe = snapshot.context.recipe or "study"
    causes = [
        {"signal": "module", "value": "reentry"},
        {"signal": "state", "value": flow.state.value},
        {"signal": "engagement", "value": round(flow.engagement, 3)},
        {"signal": "user_goal", "value": snapshot.context.user_goal or ""},
        {"signal": "recipe", "value": recipe},
    ]
    bonus = recipe_reentry_bonus(recipe)
    return [
        ActionProposal(
            tool_id="ui.set_density",
            impact=ImpactLevel.LOW,
            params={"density": "calm"},
            score=0.55 + bonus,
            causes=causes
            + [{"signal": "reason", "value": "gentle scaffold for re-entry"}],
        ),
        ActionProposal(
            tool_id="focus.enable",
            impact=ImpactLevel.MEDIUM,
            params={},
            score=0.45 + bonus,
            causes=causes
            + [{"signal": "reason", "value": "optional focus frame for restart"}],
        ),
        ActionProposal(
            tool_id="recipe.apply",
            impact=ImpactLevel.LOW,
            params={"recipe": recipe},
            score=0.4 + bonus,
            causes=causes
            + [{"signal": "reason", "value": "re-apply supportive environment recipe"}],
        ),
    ]
