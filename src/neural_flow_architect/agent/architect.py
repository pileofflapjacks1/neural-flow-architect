"""The Architect — proactive co-pilot orchestrator."""

from __future__ import annotations

from dataclasses import dataclass, field

from neural_flow_architect.agent.explainer import Explainer
from neural_flow_architect.agent.governor import Governor
from neural_flow_architect.agent.policies.modes import select_mode
from neural_flow_architect.agent.policies.rules import propose_actions
from neural_flow_architect.agent.tools.base import ToolRegistry
from neural_flow_architect.agent.tools.digital import register_digital_tools
from neural_flow_architect.agent.tools.iot import register_iot_tools
from neural_flow_architect.core.types import (
    ActionResult,
    AgentMode,
    Explanation,
    WorldSnapshot,
)
from neural_flow_architect.environment.digital import DigitalOrchestrator
from neural_flow_architect.environment.physical import PhysicalOrchestrator


@dataclass
class ArchitectDecision:
    mode: AgentMode
    results: list[ActionResult] = field(default_factory=list)
    explanations: list[Explanation] = field(default_factory=list)


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
    ) -> None:
        self.digital = digital or DigitalOrchestrator()
        self.physical = physical or PhysicalOrchestrator(enabled=False)
        self.dry_run = dry_run
        self.min_confidence = min_confidence
        self.min_quality = min_quality
        self.max_actions_per_tick = max_actions_per_tick
        self.registry = ToolRegistry()
        register_digital_tools(self.registry, self.digital)
        register_iot_tools(self.registry, self.physical)
        self.governor = Governor()
        self.explainer = Explainer()

    def pause(self) -> None:
        # Caller should also flip preferences.agent_paused; this is a convenience hook.
        pass

    async def step(self, snapshot: WorldSnapshot) -> ArchitectDecision:
        mode = select_mode(
            snapshot,
            min_confidence=self.min_confidence,
            min_quality=self.min_quality,
        )
        proposals = propose_actions(mode, snapshot)
        allowed = self.governor.filter(proposals, snapshot)[: self.max_actions_per_tick]

        results: list[ActionResult] = []
        explanations: list[Explanation] = []
        for prop in allowed:
            spec = self.registry.get(prop.tool_id)
            if spec is None:
                continue
            explanation = self.explainer.render(prop, snapshot)
            explanations.append(explanation)
            result = await spec.handler.run(snapshot, prop.params, dry_run=self.dry_run)
            results.append(result)
            if result.success:
                self.governor.record(prop.tool_id, prop.impact)

        return ArchitectDecision(mode=mode, results=results, explanations=explanations)
