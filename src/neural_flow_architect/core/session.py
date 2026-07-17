"""Session controller — long-running loop with control plane for the local API."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime
from typing import Any

from neural_flow_architect.agent.undo import UndoStack
from neural_flow_architect.core.context import enrich_context
from neural_flow_architect.core.runtime import NeuralFlowRuntime, RuntimeTick
from neural_flow_architect.core.settings import Settings, get_settings
from neural_flow_architect.core.types import (
    AgentMode,
    ContextSnapshot,
    FlowState,
    UserPreferences,
)
from neural_flow_architect.environment.recipes import apply_recipe, list_recipes
from neural_flow_architect.insights.coaching import build_coaching_notes
from neural_flow_architect.personalization.learning import (
    learn_from_session_summary,
    update_thresholds_from_label,
)
from neural_flow_architect.personalization.profile import UserProfile
from neural_flow_architect.privacy.consent import ConsentScope


StateListener = Callable[[dict[str, Any]], None]


class SessionController:
    """
    Owns a NeuralFlowRuntime, user profile, and broadcast of live state.

    Used by the local API (`nfa serve`) and can be driven from tests.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.settings.ensure_data_dirs()
        self.profile = UserProfile.load(self.settings.data_dir / "profiles", "local")
        self.undo_stack = UndoStack()
        self._recipe = self.profile.preferences.preferred_recipe or "study"
        self._active_app: str | None = None
        self._user_goal: str | None = None
        self.runtime = self._new_runtime()
        self._task: asyncio.Task[list[RuntimeTick]] | None = None
        self._listeners: list[asyncio.Queue[dict[str, Any]]] = []
        self._latest: dict[str, Any] = self._idle_state()
        self._lock = asyncio.Lock()

    def _new_runtime(self) -> NeuralFlowRuntime:
        rt = NeuralFlowRuntime(
            self.settings,
            undo_stack=self.undo_stack,
            preferences_provider=self.preferences_for_runtime,
            context_provider=self.context_for_runtime,
        )
        rt.flow.protect_t = self.profile.protect_engagement_threshold
        rt.flow.deep_t = self.profile.deep_flow_engagement_threshold
        return rt

    def context_for_runtime(self) -> ContextSnapshot:
        return enrich_context(
            ContextSnapshot(
                recipe=self._recipe,
                user_goal=self._user_goal,
                active_app=self._active_app,
            ),
            active_app=self._active_app,
            user_goal=self._user_goal,
            recipe=self._recipe,
        )

    def _idle_state(self) -> dict[str, Any]:
        return {
            "running": False,
            "agent_paused": self.profile.preferences.agent_paused,
            "can_undo": self.undo_stack.can_undo,
            "mode": AgentMode.IDLE.value,
            "flow": {
                "state": FlowState.UNKNOWN.value,
                "engagement": 0.0,
                "arousal_balance": 0.0,
                "self_ref_proxy": 0.0,
                "effort_ease": 0.0,
                "confidence": 0.0,
                "minutes_in_state": 0.0,
                "reasons": [],
            },
            "quality": {"overall": 1.0},
            "digital": self.runtime.digital.snapshot(),
            "explanation": None,
            "explanations": [],
            "actions": [],
            "session": None,
            "adapter": self.settings.adapter,
            "signal": "idle",
            "consent": self.runtime.consent.as_dict(),
            "preferences": self.profile.preferences.model_dump(),
            "recipe": self._recipe,
            "context": self.context_for_runtime().model_dump(),
            "thresholds": {
                "protect": self.profile.protect_engagement_threshold,
                "deep": self.profile.deep_flow_engagement_threshold,
            },
            "precursors": [],
            "predictive_enabled": self.settings.predictive_enabled,
            "llm_enabled": self.settings.llm_enabled
            or self.settings.agent_mode == "llm_local",
            "ts": datetime.utcnow().isoformat(),
        }

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=8)
        self._listeners.append(q)
        q.put_nowait(self._latest)
        return q

    def unsubscribe(self, q: asyncio.Queue[dict[str, Any]]) -> None:
        if q in self._listeners:
            self._listeners.remove(q)

    def _publish(self, state: dict[str, Any]) -> None:
        self._latest = state
        dead: list[asyncio.Queue[dict[str, Any]]] = []
        for q in self._listeners:
            try:
                if q.full():
                    try:
                        q.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                q.put_nowait(state)
            except Exception:
                dead.append(q)
        for q in dead:
            self.unsubscribe(q)

    def get_state(self) -> dict[str, Any]:
        return dict(self._latest)

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self, duration_sec: float | None = None) -> dict[str, Any]:
        async with self._lock:
            if self.is_running:
                return {"ok": False, "message": "Session already running", "state": self._latest}

            self.undo_stack.clear()
            self.runtime = self._new_runtime()
            if not self.runtime.consent.allows(ConsentScope.PERSIST_FEATURES):
                self.runtime.consent.set(ConsentScope.PERSIST_FEATURES, True, note="serve_default")

            def on_tick(tick: RuntimeTick) -> None:
                self._on_tick(tick)

            self._task = asyncio.create_task(
                self.runtime.run(duration_sec=duration_sec, on_tick=on_tick),
                name="nfa-session-loop",
            )

            def _done(task: asyncio.Task[list[RuntimeTick]]) -> None:
                state = self.get_state()
                state["running"] = False
                try:
                    if task.cancelled():
                        state.pop("error", None)
                    else:
                        exc = task.exception()
                        if exc is not None:
                            state["error"] = f"{type(exc).__name__}: {exc}"
                except Exception as exc:  # noqa: BLE001
                    state["error"] = str(exc)

                if self.runtime.insights.current is not None:
                    state["session"] = self.runtime.insights.snapshot_current()
                else:
                    sessions = self.runtime.insights.list_sessions(limit=1)
                    if sessions:
                        state["session"] = sessions[0]
                        note = learn_from_session_summary(self.profile, sessions[0])
                        if note:
                            state["learning_note"] = note
                            self.profile.save(self.settings.data_dir / "profiles")
                self._publish(state)

            self._task.add_done_callback(_done)
            state = self.get_state()
            state["running"] = True
            state["signal"] = "good"
            state["recipe"] = self._recipe
            self._publish(state)
            return {"ok": True, "message": "Session started", "state": self._latest}

    async def stop(self) -> dict[str, Any]:
        async with self._lock:
            if not self.is_running:
                return {"ok": True, "message": "Not running", "state": self._latest}
            self.runtime.stop()
            assert self._task is not None
            try:
                await asyncio.wait_for(asyncio.shield(self._task), timeout=5.0)
            except TimeoutError:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            except asyncio.CancelledError:
                pass
            self._task = None
            state = self.get_state()
            state["running"] = False
            if self.runtime.insights.current is not None:
                persist = self.runtime.consent.allows(ConsentScope.PERSIST_FEATURES)
                summary = self.runtime.insights.end_session(persist=persist)
                if summary is not None:
                    payload = summary.to_dict()
                    state["session"] = payload
                    note = learn_from_session_summary(self.profile, payload)
                    if note:
                        state["learning_note"] = note
                        self.profile.save(self.settings.data_dir / "profiles")
            self._publish(state)
            return {"ok": True, "message": "Session stopped", "state": self._latest}

    def _on_tick(self, tick: RuntimeTick) -> None:
        explanation = None
        explanations = []
        if tick.decision.explanations:
            explanation = tick.decision.explanations[-1].model_dump(mode="json")
            explanations = [e.model_dump(mode="json") for e in tick.decision.explanations]
        actions = [r.model_dump(mode="json") for r in tick.decision.results]
        conf = tick.flow.confidence
        q = tick.quality_overall
        if q < 0.35 or conf < 0.35:
            signal = "poor"
        elif q < 0.6 or conf < 0.6:
            signal = "degraded"
        else:
            signal = "good"
        state = {
            "running": True,
            "agent_paused": self.profile.preferences.agent_paused,
            "can_undo": self.undo_stack.can_undo,
            "mode": tick.decision.mode.value,
            "flow": tick.flow.model_dump(mode="json"),
            "quality": {"overall": q},
            "digital": tick.digital,
            "explanation": explanation,
            "explanations": explanations,
            "actions": actions,
            "session": self.runtime.insights.snapshot_current(),
            "adapter": self.settings.adapter,
            "signal": signal,
            "consent": self.runtime.consent.as_dict(),
            "preferences": self.profile.preferences.model_dump(),
            "recipe": self._recipe,
            "context": self.context_for_runtime().model_dump(),
            "thresholds": {
                "protect": self.profile.protect_engagement_threshold,
                "deep": self.profile.deep_flow_engagement_threshold,
            },
            "precursors": tick.precursors,
            "predictive_enabled": self.settings.predictive_enabled,
            "llm_enabled": self.settings.llm_enabled
            or self.settings.agent_mode == "llm_local",
            "ts": datetime.utcnow().isoformat(),
        }
        self._publish(state)

    def set_predictive(self, enabled: bool) -> dict[str, Any]:
        self.settings.predictive_enabled = enabled
        self.runtime.architect.precursors.enabled = enabled
        state = self.get_state()
        state["predictive_enabled"] = enabled
        self._publish(state)
        return {"ok": True, "predictive_enabled": enabled, "state": state}

    def set_paused(self, paused: bool) -> dict[str, Any]:
        self.profile.preferences.agent_paused = paused
        self.profile.save(self.settings.data_dir / "profiles")
        state = self.get_state()
        state["agent_paused"] = paused
        state["preferences"] = self.profile.preferences.model_dump()
        if paused:
            state["mode"] = AgentMode.IDLE.value
        self._publish(state)
        return {"ok": True, "agent_paused": paused, "state": state}

    def undo(self) -> dict[str, Any]:
        result = self.runtime.architect.undo_last()
        if result.success:
            self.runtime.insights.observe_undo()
        state = self.get_state()
        state["can_undo"] = self.undo_stack.can_undo
        state["digital"] = self.runtime.digital.snapshot()
        state["last_undo"] = result.model_dump(mode="json")
        self._publish(state)
        return {"ok": result.success, "result": result.model_dump(mode="json"), "state": state}

    def set_tool_preference(self, tool_id: str, action: str) -> dict[str, Any]:
        prefs = self.profile.preferences
        denied = set(prefs.denied_tools)
        granted = set(prefs.granted_tools)
        if action == "never":
            denied.add(tool_id)
            granted.discard(tool_id)
        elif action == "always":
            granted.add(tool_id)
            denied.discard(tool_id)
        elif action == "clear":
            denied.discard(tool_id)
            granted.discard(tool_id)
        else:
            return {"ok": False, "message": f"Unknown action {action}"}
        prefs.denied_tools = sorted(denied)
        prefs.granted_tools = sorted(granted)
        self.profile.save(self.settings.data_dir / "profiles")
        state = self.get_state()
        state["preferences"] = prefs.model_dump()
        self._publish(state)
        return {"ok": True, "preferences": prefs.model_dump(), "state": state}

    def rest_mode(self) -> dict[str, Any]:
        self.set_recipe("rest")
        self.runtime.digital.set_rest_mode(True)
        self.profile.preferences.agent_paused = True
        self.profile.save(self.settings.data_dir / "profiles")
        state = self.get_state()
        state["agent_paused"] = True
        state["digital"] = self.runtime.digital.snapshot()
        state["mode"] = AgentMode.TRANSITION.value
        state["recipe"] = "rest"
        self._publish(state)
        return {"ok": True, "state": state}

    def set_recipe(self, recipe: str) -> dict[str, Any]:
        allowed = {r["name"] for r in list_recipes()}
        if recipe not in allowed:
            return {"ok": False, "message": f"Unknown recipe {recipe}", "recipes": list_recipes()}
        self._recipe = recipe
        self.profile.preferences.preferred_recipe = recipe
        apply_recipe(self.runtime.digital, recipe)
        if recipe != "rest":
            # Rest sets pause separately via rest_mode
            pass
        self.profile.save(self.settings.data_dir / "profiles")
        state = self.get_state()
        state["recipe"] = recipe
        state["digital"] = self.runtime.digital.snapshot()
        state["context"] = self.context_for_runtime().model_dump()
        state["preferences"] = self.profile.preferences.model_dump()
        self._publish(state)
        return {"ok": True, "recipe": recipe, "state": state}

    def set_context(
        self,
        *,
        active_app: str | None = None,
        user_goal: str | None = None,
    ) -> dict[str, Any]:
        if active_app is not None:
            self._active_app = active_app or None
        if user_goal is not None:
            self._user_goal = user_goal or None
        state = self.get_state()
        state["context"] = self.context_for_runtime().model_dump()
        self._publish(state)
        return {"ok": True, "context": state["context"], "state": state}

    def label_flow(self, felt_in_flow: bool, note: str = "") -> dict[str, Any]:
        flow = self._latest.get("flow") or {}
        eng = float(flow.get("engagement", 0.0))
        label = self.runtime.insights.add_label(
            felt_in_flow,
            note=note,
            state=str(flow.get("state", "")),
            engagement=eng,
        )
        update = update_thresholds_from_label(
            self.profile,
            felt_in_flow=felt_in_flow,
            engagement_at_label=eng,
        )
        self.runtime.flow.protect_t = self.profile.protect_engagement_threshold
        self.runtime.flow.deep_t = self.profile.deep_flow_engagement_threshold
        self.profile.save(self.settings.data_dir / "profiles")
        state = self.get_state()
        state["session"] = self.runtime.insights.snapshot_current()
        state["last_label"] = label.to_dict()
        state["learning"] = {
            "message": update.message,
            "protect": update.protect_engagement_threshold,
            "deep": update.deep_flow_engagement_threshold,
        }
        state["thresholds"] = {
            "protect": self.profile.protect_engagement_threshold,
            "deep": self.profile.deep_flow_engagement_threshold,
        }
        state["preferences"] = self.profile.preferences.model_dump()
        self._publish(state)
        return {
            "ok": True,
            "label": label.to_dict(),
            "learning": state["learning"],
            "state": state,
        }

    def list_sessions(self) -> list[dict[str, Any]]:
        return self.runtime.insights.list_sessions()

    def coaching(self) -> dict[str, Any]:
        sessions = self.runtime.insights.list_sessions(limit=30)
        notes = build_coaching_notes(sessions)
        return {"ok": True, "notes": notes, "sessions_considered": len(sessions)}

    def export_current(self) -> dict[str, Any]:
        snap = self.runtime.insights.snapshot_current()
        if snap is None:
            sessions = self.list_sessions()
            if not sessions:
                return {"ok": False, "message": "No session to export"}
            return {"ok": True, "session": sessions[0], "persisted": True}
        return {"ok": True, "session": snap, "persisted": True}

    def preferences_for_runtime(self) -> UserPreferences:
        prefs = self.profile.preferences.model_copy(deep=True)
        prefs.allow_iot = (
            self.runtime.consent.allows(ConsentScope.IOT_CONTROL) and self.settings.iot_enabled
        )
        prefs.require_confirm_high_impact = self.settings.require_confirm_for_high_impact
        prefs.preferred_recipe = self._recipe
        return prefs
