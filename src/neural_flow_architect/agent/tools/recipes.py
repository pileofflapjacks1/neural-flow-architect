"""Recipe application tool for the Architect."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from neural_flow_architect.core.types import ActionResult, ImpactLevel, WorldSnapshot
from neural_flow_architect.environment.digital import DigitalOrchestrator
from neural_flow_architect.environment.recipes import apply_recipe


class ApplyRecipeTool:
    id = "recipe.apply"
    impact = ImpactLevel.LOW
    description = "Apply a named environment recipe (study/create/rest/social)"

    def __init__(self, orchestrator: DigitalOrchestrator) -> None:
        self.orch = orchestrator

    async def run(
        self, snapshot: WorldSnapshot, params: dict[str, Any], *, dry_run: bool
    ) -> ActionResult:
        recipe = str(params.get("recipe", snapshot.context.recipe or "study"))
        if dry_run:
            return ActionResult(
                tool_id=self.id,
                success=True,
                message=f"[dry-run] apply recipe={recipe}",
                dry_run=True,
            )
        result = apply_recipe(self.orch, recipe)
        return ActionResult(
            tool_id=self.id,
            success=True,
            message=f"Applied recipe {result['recipe']}",
            undo_token=str(uuid4()),
        )


def register_recipe_tools(registry: Any, orchestrator: DigitalOrchestrator) -> None:
    registry.register(ApplyRecipeTool(orchestrator))
