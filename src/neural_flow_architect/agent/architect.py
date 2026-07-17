"""The Architect — proactive co-pilot orchestrator."""

from __future__ import annotations

from dataclasses import dataclass, field

from neural_flow_architect.agent.explainer import Explainer
from neural_flow_architect.agent.governor import Governor
from neural_flow_architect.agent.llm_explainer import LocalLLMExplainer, maybe_llm_explain
from neural_flow_architect.agent.policies.modes import select_mode
from neural_flow_architect.agent.policies.rules import propose_actions
from neural_flow_architect.agent.predictive import PrecursorTracker, propose_from_precursors
from neural_flow_architect.agent.tools.base import ToolRegistry
from neural_flow_architect.agent.tools.digital import register_digital_tools
from neural_flow_architect.agent.tools.iot import register_iot_tools
from neural_flow_architect.agent.tools.prepare import register_prepare_tools
from neural_flow_architect.agent.tools.recipes import register_recipe_tools
from neural_flow_architect.agent.undo import UndoRecord, UndoStack
from neural_flow_architect.core.types import (
    ActionResult,
    AgentMode,
    Explanation,
    WorldSnapshot,
)
from neural_flow_architect.environment.digital import DigitalOrchestrator
from neural_flow_architect.environment.os_notifications import (
    NotificationBackend,
    build_notification_backend,
)
from neural_flow_architect.environment.physical import PhysicalOrchestrator


@dataclass
class ArchitectDecision:
    mode: AgentMode
    results: list[ActionResult] = field(default_factory=list)
    explanations: list[Explanation] = field(default_factory=list)
    precursors: list[dict] = field(default_factory=list)


class Architect:
    def __init__(
        self,
        digital: DigitalOrchestrator | None = None,
        physical: PhysicalOrchestrator | None = None,
        *,
        dry_run: bool = False,
        min_confidence: float = 0.45,
        min_quality: float = 0.35,
        max_actions_per_tick: int = 2,
        undo_stack: UndoStack | None = None,
        predictive_enabled: bool = False,
        llm: LocalLLMExplainer | None = None,
        notifications: NotificationBackend | None = None,
        score_bonus_fn=None,  # type: ignore[no-untyped-def]
        failsafe_allow_fn=None,  # type: ignore[no-untyped-def]
        on_agent_error=None,  # type: ignore[no-untyped-def]
        force_idle: bool = False,
    ) -> None:
        self.digital = digital or DigitalOrchestrator()
        self.physical = physical or PhysicalOrchestrator(enabled=False)
        self.notifications = notifications or build_notification_backend(enabled=False)
        self.dry_run = dry_run
        self.min_confidence = min_confidence
        self.min_quality = min_quality
        self.max_actions_per_tick = max_actions_per_tick
        self.force_idle = force_idle
        self.on_agent_error = on_agent_error
        self.registry = ToolRegistry()
        register_digital_tools(self.registry, self.digital, self.notifications)
        register_iot_tools(self.registry, self.physical)
        register_recipe_tools(self.registry, self.digital)
        register_prepare_tools(self.registry, self.digital)
        self.governor = Governor(
            score_bonus_fn=score_bonus_fn,
            failsafe_allow_fn=failsafe_allow_fn,
        )
        self.explainer = Explainer()
        self.llm = llm
        self.undo_stack = undo_stack or UndoStack()
        self.precursors = PrecursorTracker()
        self.precursors.enabled = predictive_enabled
        self.last_actions: list[dict] = []

    async def step(self, snapshot: WorldSnapshot) -> ArchitectDecision:
        if self.force_idle or snapshot.preferences.agent_paused:
            return ArchitectDecision(mode=AgentMode.IDLE, precursors=[])

        try:
            mode = select_mode(
                snapshot,
                min_confidence=self.min_confidence,
                min_quality=self.min_quality,
            )
            proposals = propose_actions(mode, snapshot)

            precursor_events = self.precursors.observe(snapshot.flow)
            precursor_dicts = [e.to_dict() for e in precursor_events]
            if self.precursors.enabled and precursor_events:
                proposals = propose_from_precursors(precursor_events, snapshot) + proposals
                proposals = sorted(proposals, key=lambda p: p.score, reverse=True)

            allowed = self.governor.filter(proposals, snapshot)[: self.max_actions_per_tick]

            results: list[ActionResult] = []
            explanations: list[Explanation] = []
            for prop in allowed:
                spec = self.registry.get(prop.tool_id)
                if spec is None:
                    continue
                explanation = self.explainer.render(prop, snapshot)
                explanation = await maybe_llm_explain(self.llm, prop, snapshot, explanation)
                explanations.append(explanation)
                previous = self.digital.snapshot()
                try:
                    result = await spec.handler.run(snapshot, prop.params, dry_run=self.dry_run)
                except Exception as exc:  # noqa: BLE001
                    if self.on_agent_error is not None:
                        self.on_agent_error(exc)
                    result = ActionResult(
                        tool_id=prop.tool_id,
                        success=False,
                        message=f"Tool error (fail-safe): {type(exc).__name__}",
                        reversible=False,
                    )
                results.append(result)
                if result.success:
                    self.governor.record(prop.tool_id, prop.impact)
                    self.last_actions.append(
                        {
                            "tool_id": prop.tool_id,
                            "explanation": explanation.text,
                            "mode": mode.value,
                            "engagement": snapshot.flow.engagement,
                        }
                    )
                    if len(self.last_actions) > 20:
                        self.last_actions = self.last_actions[-20:]
                    if result.reversible and not result.dry_run:
                        self.undo_stack.push(
                            UndoRecord(
                                tool_id=prop.tool_id,
                                previous_digital=previous,
                                explanation=explanation.text,
                                undo_token=result.undo_token or "",
                                params=dict(prop.params),
                            )
                        )

            return ArchitectDecision(
                mode=mode,
                results=results,
                explanations=explanations,
                precursors=precursor_dicts,
            )
        except Exception as exc:  # noqa: BLE001
            if self.on_agent_error is not None:
                self.on_agent_error(exc)
            return ArchitectDecision(mode=AgentMode.IDLE_DEGRADED, precursors=[])

    def undo_last(self) -> ActionResult:
        record = self.undo_stack.pop()
        if record is None:
            return ActionResult(
                tool_id="agent.undo",
                success=False,
                message="Nothing to undo",
                reversible=False,
            )
        self.digital.restore(record.previous_digital)
        if record.tool_id in {
            "notify.suppress_noncritical",
            "focus.enable",
            "recipe.apply",
            "prepare.context",
        }:
            self.governor._active_tools.discard(record.tool_id)
            if record.tool_id == "notify.suppress_noncritical":
                self.notifications.restore()
        return ActionResult(
            tool_id="agent.undo",
            success=True,
            message=f"Undid {record.tool_id}",
            reversible=False,
            undo_token=record.undo_token,
        )
