"""Closed-loop runtime: adapter → features → flow → architect."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from datetime import datetime

from neural_flow_architect.adapters.base import BCIAdapter
from neural_flow_architect.adapters.registry import build_adapter
from neural_flow_architect.agent.architect import Architect, ArchitectDecision
from neural_flow_architect.core.settings import Settings, get_settings
from neural_flow_architect.core.types import (
    AgentMode,
    ContextSnapshot,
    FlowEstimate,
    QualityFlags,
    UserPreferences,
    WorldSnapshot,
)
from neural_flow_architect.environment.digital import DigitalOrchestrator
from neural_flow_architect.environment.physical import PhysicalOrchestrator
from neural_flow_architect.flow.engine import FlowEngine
from neural_flow_architect.insights.store import InsightsStore
from neural_flow_architect.privacy.consent import ConsentManager, ConsentScope
from neural_flow_architect.signal.features import FeatureExtractor


@dataclass
class RuntimeTick:
    flow: FlowEstimate
    decision: ArchitectDecision
    digital: dict[str, object] = field(default_factory=dict)


OnTick = Callable[[RuntimeTick], None]


class NeuralFlowRuntime:
    """Main closed-loop controller for local single-user sessions."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.settings.ensure_data_dirs()
        self.consent = ConsentManager()
        self.adapter: BCIAdapter = build_adapter(self.settings)
        self.features = FeatureExtractor(
            sample_rate_hz=self.settings.sample_rate_hz,
            window_sec=self.settings.window_sec,
            hop_sec=self.settings.hop_sec,
        )
        self.flow = FlowEngine(
            protect_engagement_threshold=self.settings.protect_engagement_threshold,
            deep_flow_engagement_threshold=self.settings.deep_flow_engagement_threshold,
        )
        self.digital = DigitalOrchestrator()
        self.physical = PhysicalOrchestrator(enabled=self.settings.iot_enabled)
        self.architect = Architect(
            digital=self.digital,
            physical=self.physical,
            dry_run=self.settings.dry_run,
            min_confidence=self.settings.agent_min_confidence,
            min_quality=self.settings.agent_min_quality,
        )
        self.insights = InsightsStore(self.settings.data_dir / "sessions")
        self._running = False
        self.last_flow: FlowEstimate | None = None
        self.last_decision: ArchitectDecision | None = None
        self.context = ContextSnapshot(user_goal="deep work")

    async def run(
        self,
        duration_sec: float | None = None,
        on_tick: OnTick | None = None,
    ) -> list[RuntimeTick]:
        if not self.consent.allows(ConsentScope.ACQUIRE):
            raise RuntimeError("Consent scope 'acquire' is not granted")
        if not self.consent.allows(ConsentScope.PROCESS_REALTIME):
            raise RuntimeError("Consent scope 'process_realtime' is not granted")

        await self.adapter.connect()
        self.insights.start_session()
        self._running = True
        ticks: list[RuntimeTick] = []
        loop = asyncio.get_running_loop()
        started = loop.time()

        try:
            async for frame in self.adapter.stream():
                if not self._running:
                    break
                if duration_sec is not None and (loop.time() - started) >= duration_sec:
                    break

                for window in self.features.push(frame):
                    estimate = self.flow.update(window)
                    self.last_flow = estimate
                    self.insights.observe_flow(estimate)
                    decision = await self._maybe_act(estimate)
                    self.last_decision = decision
                    tick = RuntimeTick(
                        flow=estimate,
                        decision=decision,
                        digital=self.digital.snapshot(),
                    )
                    ticks.append(tick)
                    if on_tick is not None:
                        on_tick(tick)
        finally:
            self._running = False
            await self.adapter.disconnect()
            if self.consent.allows(ConsentScope.PERSIST_FEATURES):
                self.insights.end_session()
            else:
                self.insights._current = None

        return ticks

    async def _maybe_act(self, estimate: FlowEstimate) -> ArchitectDecision:
        if not self.consent.allows(ConsentScope.AGENT_ACT):
            return ArchitectDecision(mode=AgentMode.IDLE)

        prefs = UserPreferences(
            allow_iot=self.consent.allows(ConsentScope.IOT_CONTROL) and self.settings.iot_enabled,
            require_confirm_high_impact=self.settings.require_confirm_for_high_impact,
        )
        snapshot = WorldSnapshot(
            time=datetime.utcnow(),
            flow=estimate,
            quality=QualityFlags(overall=estimate.confidence),
            context=self.context,
            preferences=prefs,
        )
        decision = await self.architect.step(snapshot)
        for exp in decision.explanations:
            self.insights.observe_action(exp.text)
        return decision

    def stop(self) -> None:
        self._running = False

    async def ticks(self, duration_sec: float | None = None) -> AsyncIterator[RuntimeTick]:
        """Async generator variant for streaming UIs."""
        queue: asyncio.Queue[RuntimeTick] = asyncio.Queue()

        def _on_tick(tick: RuntimeTick) -> None:
            queue.put_nowait(tick)

        task = asyncio.create_task(self.run(duration_sec=duration_sec, on_tick=_on_tick))
        try:
            while True:
                if task.done() and queue.empty():
                    break
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=0.5)
                except TimeoutError:
                    if task.done():
                        break
                    continue
                yield item
        finally:
            self.stop()
            await task
