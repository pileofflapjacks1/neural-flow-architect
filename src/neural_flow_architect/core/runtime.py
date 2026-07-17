"""Closed-loop runtime: adapter → features → flow → architect (+ intents)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from datetime import datetime

from neural_flow_architect.adapters.base import BCIAdapter
from neural_flow_architect.adapters.registry import build_adapter
from neural_flow_architect.agent.architect import Architect, ArchitectDecision
from neural_flow_architect.agent.llm_explainer import LocalLLMExplainer
from neural_flow_architect.agent.undo import UndoStack
from neural_flow_architect.core.context import enrich_context
from neural_flow_architect.core.settings import Settings, get_settings
from neural_flow_architect.core.types import (
    AgentMode,
    ContextSnapshot,
    FlowEstimate,
    IntentEvent,
    UserPreferences,
    WorldSnapshot,
)
from neural_flow_architect.environment.digital import DigitalOrchestrator
from neural_flow_architect.environment.os_notifications import build_notification_backend
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
    quality_overall: float = 1.0
    precursors: list[dict] = field(default_factory=list)


OnTick = Callable[[RuntimeTick], None]
OnIntent = Callable[[IntentEvent], None]


class NeuralFlowRuntime:
    """Main closed-loop controller for local single-user sessions."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        undo_stack: UndoStack | None = None,
        preferences_provider: Callable[[], UserPreferences] | None = None,
        context_provider: Callable[[], ContextSnapshot] | None = None,
        intent_handler: Callable[[IntentEvent], None] | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.settings.ensure_data_dirs()
        self.consent = ConsentManager()
        self.adapter: BCIAdapter = build_adapter(self.settings)
        self.features = FeatureExtractor(
            sample_rate_hz=self.settings.sample_rate_hz,
            window_sec=self.settings.window_sec,
            hop_sec=self.settings.hop_sec,
            include_connectivity=getattr(self.settings, "include_connectivity", False),
        )
        self.flow = FlowEngine(
            protect_engagement_threshold=self.settings.protect_engagement_threshold,
            deep_flow_engagement_threshold=self.settings.deep_flow_engagement_threshold,
        )
        self.digital = DigitalOrchestrator()
        self.physical = PhysicalOrchestrator(
            enabled=self.settings.iot_enabled,
            base_url=self.settings.home_assistant_url,
            token=self.settings.home_assistant_token,
        )
        self.notifications = build_notification_backend(
            enabled=self.settings.os_notifications,
            announce=self.settings.os_notifications_announce,
        )
        self.undo_stack = undo_stack or UndoStack()
        llm = None
        if self.settings.llm_enabled or self.settings.agent_mode == "llm_local":
            llm = LocalLLMExplainer(
                enabled=True,
                base_url=self.settings.llm_base_url,
                model=self.settings.llm_model,
                allow_cloud=self.settings.allow_cloud_llm,
                timeout_sec=self.settings.llm_timeout_sec,
            )
        self.architect = Architect(
            digital=self.digital,
            physical=self.physical,
            dry_run=self.settings.dry_run,
            min_confidence=self.settings.agent_min_confidence,
            min_quality=self.settings.agent_min_quality,
            undo_stack=self.undo_stack,
            predictive_enabled=self.settings.predictive_enabled,
            llm=llm,
            notifications=self.notifications,
        )
        self.architect.precursors.min_confidence = self.settings.predictive_min_confidence
        self.insights = InsightsStore(self.settings.data_dir / "sessions")
        self.preferences_provider = preferences_provider
        self.context_provider = context_provider
        self.intent_handler = intent_handler
        self._running = False
        self._intent_task: asyncio.Task[None] | None = None
        self.last_flow: FlowEstimate | None = None
        self.last_decision: ArchitectDecision | None = None
        self.last_quality_overall: float = 1.0
        self.last_intent: IntentEvent | None = None
        self.context = ContextSnapshot(user_goal="deep work", recipe="study")

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
        self.insights.start_session(adapter=self.settings.adapter)
        self._running = True
        ticks: list[RuntimeTick] = []
        loop = asyncio.get_running_loop()
        started = loop.time()

        # Parallel intent stream (Neuralink-ready control path)
        intent_iter = None
        try:
            intent_iter = self.adapter.intents()
        except Exception:
            intent_iter = None
        if intent_iter is not None:
            self._intent_task = asyncio.create_task(
                self._consume_intents(intent_iter), name="nfa-intents"
            )

        try:
            async for frame in self.adapter.stream():
                if not self._running:
                    break
                if duration_sec is not None and (loop.time() - started) >= duration_sec:
                    break

                for window in self.features.push(frame):
                    estimate = self.flow.update(window)
                    self.last_flow = estimate
                    self.last_quality_overall = window.quality.overall
                    self.insights.observe_flow(estimate)
                    decision = await self._maybe_act(estimate, window.quality)
                    self.last_decision = decision
                    tick = RuntimeTick(
                        flow=estimate,
                        decision=decision,
                        digital=self.digital.snapshot(),
                        quality_overall=window.quality.overall,
                        precursors=list(decision.precursors),
                    )
                    ticks.append(tick)
                    if on_tick is not None:
                        on_tick(tick)
        finally:
            self._running = False
            if self._intent_task is not None:
                self._intent_task.cancel()
                try:
                    await self._intent_task
                except asyncio.CancelledError:
                    pass
                self._intent_task = None
            await self.adapter.disconnect()
            persist = self.consent.allows(ConsentScope.PERSIST_FEATURES)
            self.insights.end_session(persist=persist)

        return ticks

    async def _consume_intents(self, intent_iter: AsyncIterator[IntentEvent]) -> None:
        try:
            async for event in intent_iter:
                if not self._running:
                    break
                self.last_intent = event
                if self.intent_handler is not None:
                    try:
                        result = self.intent_handler(event)
                        if asyncio.iscoroutine(result):
                            await result  # type: ignore[misc]
                    except Exception:
                        # Intent handling must never kill the signal loop
                        pass
        except asyncio.CancelledError:
            raise
        except Exception:
            return

    def _current_preferences(self) -> UserPreferences:
        if self.preferences_provider is not None:
            return self.preferences_provider()
        return UserPreferences(
            allow_iot=self.consent.allows(ConsentScope.IOT_CONTROL) and self.settings.iot_enabled,
            require_confirm_high_impact=self.settings.require_confirm_for_high_impact,
        )

    def _current_context(self) -> ContextSnapshot:
        if self.context_provider is not None:
            return self.context_provider()
        return enrich_context(self.context)

    async def _maybe_act(self, estimate: FlowEstimate, quality) -> ArchitectDecision:  # type: ignore[no-untyped-def]
        if not self.consent.allows(ConsentScope.AGENT_ACT):
            return ArchitectDecision(mode=AgentMode.IDLE)

        prefs = self._current_preferences()
        ctx = self._current_context()
        self.context = ctx
        snapshot = WorldSnapshot(
            time=datetime.utcnow(),
            flow=estimate,
            quality=quality,
            context=ctx,
            preferences=prefs,
        )
        decision = await self.architect.step(snapshot)
        for exp in decision.explanations:
            self.insights.observe_action(exp.text)
        return decision

    def stop(self) -> None:
        self._running = False

    async def ticks(self, duration_sec: float | None = None) -> AsyncIterator[RuntimeTick]:
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
