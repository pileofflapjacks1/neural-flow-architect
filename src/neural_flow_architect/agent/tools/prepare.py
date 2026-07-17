"""Preparatory / predictive tools — low impact, non-modal."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from neural_flow_architect.core.types import ActionResult, ImpactLevel, WorldSnapshot
from neural_flow_architect.environment.digital import DigitalOrchestrator


class PrepareContextTool:
    id = "prepare.context"
    impact = ImpactLevel.LOW
    description = "Prepare digital context for predicted state change (non-modal)"

    def __init__(self, orchestrator: DigitalOrchestrator) -> None:
        self.orch = orchestrator
        self.last_hint: str | None = None

    async def run(
        self, snapshot: WorldSnapshot, params: dict[str, Any], *, dry_run: bool
    ) -> ActionResult:
        hint = str(params.get("hint", "generic"))
        recipe = params.get("recipe")
        if dry_run:
            return ActionResult(
                tool_id=self.id,
                success=True,
                message=f"[dry-run] prepare context hint={hint}",
                dry_run=True,
            )
        self.last_hint = hint
        # Mild, reversible prep — never aggressive
        if hint == "rising_flow":
            if self.orch.density == "normal":
                self.orch.set_density("calm")
        elif hint in {"breaking_flow", "fatigue"}:
            if recipe == "rest" or hint == "fatigue":
                self.orch.set_density("normal")
        self.orch.history.append(f"prepare.context={hint}")
        return ActionResult(
            tool_id=self.id,
            success=True,
            message=f"Prepared context for {hint}",
            undo_token=str(uuid4()),
        )


class QueueNextTaskTool:
    id = "tasks.queue_next"
    impact = ImpactLevel.LOW
    description = "Queue a non-modal micro-task suggestion"

    def __init__(self, orchestrator: DigitalOrchestrator) -> None:
        self.orch = orchestrator
        self.suggestions: list[str] = []

    async def run(
        self, snapshot: WorldSnapshot, params: dict[str, Any], *, dry_run: bool
    ) -> ActionResult:
        suggestion = str(params.get("suggestion", "Review next micro-step"))
        if dry_run:
            return ActionResult(
                tool_id=self.id,
                success=True,
                message=f"[dry-run] queue suggestion: {suggestion}",
                dry_run=True,
            )
        self.suggestions.append(suggestion)
        if len(self.suggestions) > 10:
            self.suggestions = self.suggestions[-10:]
        self.orch.history.append(f"tasks.queue_next={suggestion}")
        return ActionResult(
            tool_id=self.id,
            success=True,
            message=f"Queued suggestion: {suggestion}",
            undo_token=str(uuid4()),
        )


def register_prepare_tools(registry: Any, orchestrator: DigitalOrchestrator) -> None:
    registry.register(PrepareContextTool(orchestrator))
    registry.register(QueueNextTaskTool(orchestrator))
