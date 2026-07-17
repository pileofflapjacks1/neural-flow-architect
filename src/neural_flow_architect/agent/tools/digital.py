"""Digital environment tools (UI / focus / notifications)."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from neural_flow_architect.core.types import ActionResult, ImpactLevel, WorldSnapshot
from neural_flow_architect.environment.digital import DigitalOrchestrator


class _BaseDigitalTool:
    def __init__(self, orchestrator: DigitalOrchestrator) -> None:
        self.orch = orchestrator


class SetUIDensityTool(_BaseDigitalTool):
    id = "ui.set_density"
    impact = ImpactLevel.LOW
    description = "Simplify or restore companion UI density"

    async def run(
        self, snapshot: WorldSnapshot, params: dict[str, Any], *, dry_run: bool
    ) -> ActionResult:
        density = str(params.get("density", "minimal"))
        if dry_run:
            return ActionResult(
                tool_id=self.id,
                success=True,
                message=f"[dry-run] set UI density={density}",
                dry_run=True,
            )
        self.orch.set_density(density)
        return ActionResult(
            tool_id=self.id,
            success=True,
            message=f"UI density set to {density}",
            undo_token=str(uuid4()),
        )


class SuppressNotificationsTool(_BaseDigitalTool):
    id = "notify.suppress_noncritical"
    impact = ImpactLevel.MEDIUM
    description = "Suppress non-critical notifications during flow"

    async def run(
        self, snapshot: WorldSnapshot, params: dict[str, Any], *, dry_run: bool
    ) -> ActionResult:
        if dry_run:
            return ActionResult(
                tool_id=self.id,
                success=True,
                message="[dry-run] suppress non-critical notifications",
                dry_run=True,
            )
        self.orch.suppress_noncritical(True)
        return ActionResult(
            tool_id=self.id,
            success=True,
            message="Non-critical notifications suppressed",
            undo_token=str(uuid4()),
        )


class AllowNotificationsTool(_BaseDigitalTool):
    id = "notify.allow_all"
    impact = ImpactLevel.LOW
    description = "Restore all notifications"

    async def run(
        self, snapshot: WorldSnapshot, params: dict[str, Any], *, dry_run: bool
    ) -> ActionResult:
        if dry_run:
            return ActionResult(
                tool_id=self.id,
                success=True,
                message="[dry-run] allow all notifications",
                dry_run=True,
            )
        self.orch.suppress_noncritical(False)
        return ActionResult(
            tool_id=self.id,
            success=True,
            message="Notifications restored",
            undo_token=str(uuid4()),
        )


class EnableFocusTool(_BaseDigitalTool):
    id = "focus.enable"
    impact = ImpactLevel.MEDIUM
    description = "Enable focus session profile"

    async def run(
        self, snapshot: WorldSnapshot, params: dict[str, Any], *, dry_run: bool
    ) -> ActionResult:
        if dry_run:
            return ActionResult(
                tool_id=self.id,
                success=True,
                message="[dry-run] enable focus mode",
                dry_run=True,
            )
        self.orch.set_focus(True)
        return ActionResult(
            tool_id=self.id,
            success=True,
            message="Focus mode enabled",
            undo_token=str(uuid4()),
        )


class DisableFocusTool(_BaseDigitalTool):
    id = "focus.disable"
    impact = ImpactLevel.LOW
    description = "Disable focus session profile"

    async def run(
        self, snapshot: WorldSnapshot, params: dict[str, Any], *, dry_run: bool
    ) -> ActionResult:
        if dry_run:
            return ActionResult(
                tool_id=self.id,
                success=True,
                message="[dry-run] disable focus mode",
                dry_run=True,
            )
        self.orch.set_focus(False)
        return ActionResult(
            tool_id=self.id,
            success=True,
            message="Focus mode disabled",
            undo_token=str(uuid4()),
        )


def register_digital_tools(registry: Any, orchestrator: DigitalOrchestrator) -> None:
    for tool in (
        SetUIDensityTool(orchestrator),
        SuppressNotificationsTool(orchestrator),
        AllowNotificationsTool(orchestrator),
        EnableFocusTool(orchestrator),
        DisableFocusTool(orchestrator),
    ):
        registry.register(tool)
