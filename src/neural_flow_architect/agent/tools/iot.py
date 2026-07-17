"""Physical environment tools — gated and dry-run friendly."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from neural_flow_architect.core.types import ActionResult, ImpactLevel, WorldSnapshot
from neural_flow_architect.environment.physical import PhysicalOrchestrator


class DimLightsTool:
    id = "iot.lights.dim_for_focus"
    impact = ImpactLevel.MEDIUM
    description = "Dim lights to a focus scene"

    def __init__(self, orchestrator: PhysicalOrchestrator) -> None:
        self.orch = orchestrator

    async def run(
        self, snapshot: WorldSnapshot, params: dict[str, Any], *, dry_run: bool
    ) -> ActionResult:
        if not snapshot.preferences.allow_iot:
            return ActionResult(
                tool_id=self.id,
                success=False,
                message="IoT not permitted by user preferences",
                reversible=False,
            )
        if dry_run or not self.orch.enabled:
            return ActionResult(
                tool_id=self.id,
                success=True,
                message="[dry-run] dim lights for focus",
                dry_run=True,
                undo_token=str(uuid4()),
            )
        await self.orch.dim_for_focus()
        return ActionResult(
            tool_id=self.id,
            success=True,
            message="Lights dimmed for focus",
            undo_token=str(uuid4()),
        )


class RestoreLightsTool:
    id = "iot.lights.restore"
    impact = ImpactLevel.LOW
    description = "Restore previous lighting scene"

    def __init__(self, orchestrator: PhysicalOrchestrator) -> None:
        self.orch = orchestrator

    async def run(
        self, snapshot: WorldSnapshot, params: dict[str, Any], *, dry_run: bool
    ) -> ActionResult:
        if dry_run or not self.orch.enabled:
            return ActionResult(
                tool_id=self.id,
                success=True,
                message="[dry-run] restore lights",
                dry_run=True,
            )
        await self.orch.restore_lights()
        return ActionResult(
            tool_id=self.id,
            success=True,
            message="Lights restored",
            undo_token=str(uuid4()),
        )


def register_iot_tools(registry: Any, orchestrator: PhysicalOrchestrator) -> None:
    registry.register(DimLightsTool(orchestrator))
    registry.register(RestoreLightsTool(orchestrator))
