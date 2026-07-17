"""Session controller — long-running loop with control plane for the local API."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime
from typing import Any

from neural_flow_architect.agent.undo import UndoStack
from neural_flow_architect.core.context import enrich_context
from neural_flow_architect.core.failsafe import FailSafeGuard, FailSafeReason
from neural_flow_architect.core.intents import IntentRouter
from neural_flow_architect.core.onboarding import OnboardingState
from neural_flow_architect.core.runtime import NeuralFlowRuntime, RuntimeTick
from neural_flow_architect.core.settings import Settings, get_settings
from neural_flow_architect.core.types import (
    AgentMode,
    ContextSnapshot,
    FlowState,
    IntentEvent,
    UserPreferences,
)
from neural_flow_architect.environment.recipes import apply_recipe, list_recipes
from neural_flow_architect.insights.coaching import build_coaching_notes
from neural_flow_architect.personalization.feedback import FeedbackStore
from neural_flow_architect.personalization.learning import (
    learn_from_session_summary,
    update_thresholds_from_label,
)
from neural_flow_architect.personalization.presets import get_preset, list_presets
from neural_flow_architect.personalization.profile import UserProfile
from neural_flow_architect.privacy.audit import AuditLog
from neural_flow_architect.privacy.consent import ConsentScope
from neural_flow_architect.core.quiet_hours import QuietHours
from neural_flow_architect.core.caregiver import CaregiverChecklist
from neural_flow_architect.personalization.signature import build_personal_signature


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
        self.onboarding = OnboardingState.load(
            self.settings.data_dir / "profiles" / "onboarding.json"
        )
        self.intent_router = IntentRouter(self, min_confidence=0.5)
        self.failsafe = FailSafeGuard(
            stall_sec=self.settings.failsafe_stall_sec,
            low_quality_threshold=self.settings.failsafe_low_quality,
            low_quality_streak=self.settings.failsafe_quality_streak,
        )
        self.feedback = FeedbackStore()
        self.audit = AuditLog(self.settings.data_dir / "audit")
        self.caregiver = CaregiverChecklist.load(
            self.settings.data_dir / "profiles" / "caregiver_checklist.json"
        )
        self._pending_block_review: dict[str, Any] | None = None
        self.runtime = self._new_runtime()
        self._task: asyncio.Task[list[RuntimeTick]] | None = None
        self._listeners: list[asyncio.Queue[dict[str, Any]]] = []
        self._latest: dict[str, Any] = self._idle_state()
        self._lock = asyncio.Lock()
        self._last_intent_result: dict[str, Any] | None = None
        self._tick_count = 0
        self._session_started_at: datetime | None = None
        self._last_checkpoint_at: datetime | None = None
        self.audit.record("session.init", "Session controller ready")

    def _new_runtime(self) -> NeuralFlowRuntime:
        rt = NeuralFlowRuntime(
            self.settings,
            undo_stack=self.undo_stack,
            preferences_provider=self.preferences_for_runtime,
            context_provider=self.context_for_runtime,
            intent_handler=self._on_intent_event,
            failsafe=self.failsafe,
            score_bonus_fn=self.feedback.score_bonus,
        )
        rt.flow.protect_t = self.profile.protect_engagement_threshold
        rt.flow.deep_t = self.profile.deep_flow_engagement_threshold
        return rt

    def _on_intent_event(self, event: IntentEvent) -> Any:
        """Called from runtime intent task — schedule async route safely."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return None

        async def _run() -> None:
            result = await self.intent_router.handle(event)
            self._last_intent_result = result.to_dict()
            state = self.get_state()
            state["last_intent"] = {
                "type": event.intent_type,
                "confidence": event.confidence,
                "result": self._last_intent_result,
            }
            self._publish(state)

        loop.create_task(_run())
        return None

    def context_for_runtime(self) -> ContextSnapshot:
        # Soft lock: if user set recipe manually, keep it; still attach app for policies
        return enrich_context(
            ContextSnapshot(
                recipe=self._recipe,
                user_goal=self._user_goal,
                active_app=self._active_app,
            ),
            active_app=self._active_app,
            user_goal=self._user_goal,
            recipe=self._recipe,
            detect_app=bool(self.settings.detect_active_app) and self._active_app is None,
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
            "simple_mode": self.profile.preferences.simple_mode,
            "active_preset": self.profile.preferences.active_preset,
            "onboarding_completed": self.onboarding.completed,
            "last_intent": None,
            "a11y": self._a11y_payload(),
            "session_health": {
                "tick_count": 0,
                "uptime_sec": 0.0,
                "heartbeat_ok": True,
            },
            "failsafe": self.failsafe.state.to_dict(),
            "recent_actions": [],
            "feedback": self.feedback.as_dict(),
            "quiet_hours": QuietHours(
                enabled=self.profile.preferences.quiet_hours_enabled,
                start_hour=self.profile.preferences.quiet_hours_start,
                end_hour=self.profile.preferences.quiet_hours_end,
            ).to_dict(),
            "recipe_suggestion": None,
            "audit_recent": self.audit.recent(10),
            "pending_block_review": self._pending_block_review,
            "caregiver_checklist": self.caregiver.to_dict(),
            "personal_signature": None,
            "scan_mode": bool(
                getattr(self.profile.preferences, "scan_mode", False)
            ),
            "shortcuts": [],
            "help": {
                "user_guide": "docs/ux/USER_GUIDE.md",
                "pause": "Pause always stops proactive actions",
                "undo": "Undo reverses the last environment change",
                "keyboard": "P pause · U undo · R rest · S start · Y/N labels",
            },
            "ts": datetime.utcnow().isoformat(),
        }

    def _a11y_payload(self) -> dict[str, Any]:
        p = self.profile.preferences
        return {
            "ui_scale": p.ui_scale,
            "high_contrast": p.high_contrast,
            "reduced_motion": p.reduced_motion,
            "dwell_ms": p.dwell_ms,
            "sticky_controls": p.sticky_controls,
            "keyboard_enabled": p.keyboard_enabled,
            "voice_command_bar": p.voice_command_bar,
            "auto_start_on_preset": p.auto_start_on_preset,
            "quiet_hours_enabled": p.quiet_hours_enabled,
            "quiet_hours_start": p.quiet_hours_start,
            "quiet_hours_end": p.quiet_hours_end,
            "suggest_recipe_from_app": p.suggest_recipe_from_app,
            "scan_mode": p.scan_mode,
            "scan_interval_ms": p.scan_interval_ms,
            "css": {
                "--nfa-scale": str(p.ui_scale),
                "--target-min": f"{int(64 * p.ui_scale)}px",
            },
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

            self._tick_count = 0
            self._session_started_at = datetime.utcnow()
            self._last_checkpoint_at = self._session_started_at
            if not self.profile.preferences.agent_paused:
                self.failsafe.clear(reason_ok="session_start")
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
                    # Prompt end-of-block review
                    self._pending_block_review = {
                        "session_id": summary.session_id,
                        "prompt": "Was this work block helpful?",
                        "flow_minutes": payload.get("flow_minutes"),
                        "actions_count": payload.get("actions_count"),
                        "undos_count": payload.get("undos_count"),
                    }
                    state["pending_block_review"] = self._pending_block_review
                    note = learn_from_session_summary(self.profile, payload)
                    if note:
                        state["learning_note"] = note
                        self.profile.save(self.settings.data_dir / "profiles")
                    self.caregiver.mark("start_session", True)
                    self.caregiver.save(
                        self.settings.data_dir / "profiles" / "caregiver_checklist.json"
                    )
                    state["caregiver_checklist"] = self.caregiver.to_dict()
                    self.audit.record(
                        "session.stop",
                        "Session ended — block review pending",
                        session_id=summary.session_id,
                    )
            self._publish(state)
            return {"ok": True, "message": "Session stopped", "state": self._latest}

    def _on_tick(self, tick: RuntimeTick) -> None:
        from neural_flow_architect.core.multimodal import keymap_for_ui

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
        self._tick_count += 1
        now = datetime.utcnow()
        uptime = (
            (now - self._session_started_at).total_seconds()
            if self._session_started_at
            else 0.0
        )
        # Periodic soft checkpoint of live session summary (still local)
        checkpoint_every = max(30.0, float(self.settings.session_checkpoint_sec))
        if (
            self._last_checkpoint_at is None
            or (now - self._last_checkpoint_at).total_seconds() >= checkpoint_every
        ):
            self._last_checkpoint_at = now
            # snapshot is already in-memory; also refresh profile mtime for crash recovery UX
            self.profile.save(self.settings.data_dir / "profiles")

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
            "simple_mode": self.profile.preferences.simple_mode,
            "active_preset": self.profile.preferences.active_preset,
            "onboarding_completed": self.onboarding.completed,
            "last_intent": self._latest.get("last_intent"),
            "a11y": self._a11y_payload(),
            "session_health": {
                "tick_count": self._tick_count,
                "uptime_sec": round(uptime, 1),
                "heartbeat_ok": not self.failsafe.state.active
                or self.failsafe.state.reason == FailSafeReason.USER_PAUSE,
                "last_checkpoint": self._last_checkpoint_at.isoformat()
                if self._last_checkpoint_at
                else None,
            },
            "failsafe": tick.failsafe or self.failsafe.state.to_dict(),
            "recent_actions": list(self.runtime.architect.last_actions[-5:]),
            "feedback": self.feedback.as_dict(),
            "quiet_hours": QuietHours(
                enabled=self.profile.preferences.quiet_hours_enabled,
                start_hour=self.profile.preferences.quiet_hours_start,
                end_hour=self.profile.preferences.quiet_hours_end,
            ).to_dict(),
            "recipe_suggestion": self._recipe_suggestion(),
            "audit_recent": self.audit.recent(10),
            "pending_block_review": self._pending_block_review,
            "caregiver_checklist": self.caregiver.to_dict(),
            "scan_mode": self.profile.preferences.scan_mode,
            "scan_interval_ms": self.profile.preferences.scan_interval_ms,
            "shortcuts": keymap_for_ui(),
            "help": self._idle_state()["help"],
            "ts": now.isoformat(),
        }
        # Audit new successful actions (no neural samples)
        for act in tick.decision.results:
            if act.success:
                self.audit.record(
                    "agent.action",
                    act.message or act.tool_id,
                    tool_id=act.tool_id,
                    mode=tick.decision.mode.value,
                )
        self._publish(state)

    def _recipe_suggestion(self) -> dict[str, Any] | None:
        from neural_flow_architect.core.active_app import recipe_suggestion

        ctx = self.context_for_runtime()
        return recipe_suggestion(
            current_recipe=self._recipe,
            app_category=ctx.app_category or "unknown",
            suggest_enabled=self.profile.preferences.suggest_recipe_from_app,
        )

    def set_simple_mode(self, enabled: bool) -> dict[str, Any]:
        self.profile.preferences.simple_mode = enabled
        self.profile.save(self.settings.data_dir / "profiles")
        self.onboarding.simple_mode = enabled
        self.onboarding.save(self.settings.data_dir / "profiles" / "onboarding.json")
        state = self.get_state()
        state["simple_mode"] = enabled
        self._publish(state)
        return {"ok": True, "simple_mode": enabled, "state": state}

    def apply_preset(self, preset_id: str) -> dict[str, Any]:
        custom = self.settings.data_dir / "presets"
        preset = get_preset(preset_id, custom)
        if preset is None:
            return {"ok": False, "message": f"Unknown preset {preset_id}", "presets": list_presets(custom)}
        self.set_recipe(preset.recipe)
        self._user_goal = preset.user_goal
        self.profile.preferences.active_preset = preset.id
        self.profile.preferences.simple_mode = preset.simple_mode
        self.profile.preferences.preferred_recipe = preset.recipe
        self.set_predictive(preset.predictive_enabled)
        if preset.agent_paused:
            self.set_paused(True)
        else:
            # Do not force-resume if user had paused for safety — only clear if preset says not paused
            if self.profile.preferences.agent_paused and not preset.agent_paused:
                self.set_paused(False)
        self.profile.save(self.settings.data_dir / "profiles")
        self.onboarding.chosen_preset = preset.id
        self.onboarding.simple_mode = preset.simple_mode
        self.onboarding.save(self.settings.data_dir / "profiles" / "onboarding.json")
        state = self.get_state()
        state["active_preset"] = preset.id
        state["simple_mode"] = preset.simple_mode
        state["context"] = self.context_for_runtime().model_dump()
        self._publish(state)
        result: dict[str, Any] = {"ok": True, "preset": preset.to_dict(), "state": state}
        if self.profile.preferences.auto_start_on_preset and not self.is_running:
            result["auto_start_suggested"] = True
        return result

    def update_a11y(self, **kwargs: Any) -> dict[str, Any]:
        prefs = self.profile.preferences
        allowed = {
            "ui_scale",
            "high_contrast",
            "reduced_motion",
            "dwell_ms",
            "sticky_controls",
            "keyboard_enabled",
            "voice_command_bar",
            "auto_start_on_preset",
            "suggest_recipe_from_app",
            "quiet_hours_enabled",
            "quiet_hours_start",
            "quiet_hours_end",
            "scan_mode",
            "scan_interval_ms",
        }
        for key, val in kwargs.items():
            if key in allowed and val is not None:
                setattr(prefs, key, val)
        self.profile.save(self.settings.data_dir / "profiles")
        state = self.get_state()
        state["a11y"] = self._a11y_payload()
        state["preferences"] = prefs.model_dump()
        self._publish(state)
        return {"ok": True, "a11y": state["a11y"], "state": state}

    def export_profile(self) -> dict[str, Any]:
        from neural_flow_architect.personalization.backup import (
            export_profile_bundle,
            write_export,
        )

        sessions = self.list_sessions()[:10]
        # Strip explanations to keep export small; keep labels/stats
        meta = [
            {
                "session_id": s.get("session_id"),
                "started_at": s.get("started_at"),
                "peak_engagement": s.get("peak_engagement"),
                "flow_minutes": s.get("flow_minutes"),
                "actions_count": s.get("actions_count"),
            }
            for s in sessions
        ]
        bundle = export_profile_bundle(
            self.profile,
            onboarding=self.onboarding.to_dict(),
            include_sessions_meta=meta,
        )
        path = (
            self.settings.data_dir
            / "exports"
            / f"profile_{self.profile.user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        )
        write_export(path, bundle)
        return {"ok": True, "path": str(path), "bundle": bundle}

    def import_profile(self, bundle: dict[str, Any]) -> dict[str, Any]:
        from neural_flow_architect.personalization.backup import import_profile_bundle

        self.profile = import_profile_bundle(
            self.settings.data_dir / "profiles", bundle
        )
        self._recipe = self.profile.preferences.preferred_recipe or "study"
        if bundle.get("onboarding"):
            from neural_flow_architect.core.onboarding import OnboardingState

            ob = bundle["onboarding"]
            self.onboarding = OnboardingState(
                completed=bool(ob.get("completed", False)),
                current_step=str(ob.get("current_step", "welcome")),
                completed_steps=list(ob.get("completed_steps") or []),
                simple_mode=bool(ob.get("simple_mode", True)),
                chosen_preset=ob.get("chosen_preset"),
                caregiver_assisted=bool(ob.get("caregiver_assisted", False)),
            )
            self.onboarding.save(self.settings.data_dir / "profiles" / "onboarding.json")
        self.runtime.flow.protect_t = self.profile.protect_engagement_threshold
        self.runtime.flow.deep_t = self.profile.deep_flow_engagement_threshold
        state = self.get_state()
        state["preferences"] = self.profile.preferences.model_dump()
        state["a11y"] = self._a11y_payload()
        state["simple_mode"] = self.profile.preferences.simple_mode
        self._publish(state)
        return {"ok": True, "state": state}

    async def multimodal_command(
        self,
        *,
        source: str,
        code: str | None = None,
        text: str | None = None,
    ) -> dict[str, Any]:
        from neural_flow_architect.core.multimodal import parse_keyboard, parse_voice_text

        parsed = None
        if source == "keyboard" and code:
            if not self.profile.preferences.keyboard_enabled:
                return {"ok": False, "message": "Keyboard control disabled in a11y settings"}
            parsed = parse_keyboard(code)
        elif source in {"voice", "text"} and text:
            parsed = parse_voice_text(text)
        if parsed is None:
            return {"ok": False, "message": "Unrecognized command", "source": source}
        result = await self.inject_intent(
            parsed.intent_type, confidence=parsed.confidence, payload={"source": parsed.source, "raw": parsed.raw}
        )
        result["parsed"] = {
            "intent": parsed.intent_type,
            "source": parsed.source,
            "raw": parsed.raw,
        }
        return result

    def get_onboarding(self) -> dict[str, Any]:
        return self.onboarding.copy_for_ui()

    def advance_onboarding(
        self,
        *,
        step: str | None = None,
        caregiver_assisted: bool | None = None,
        complete: bool = False,
    ) -> dict[str, Any]:
        if caregiver_assisted is not None:
            self.onboarding.caregiver_assisted = caregiver_assisted
        if complete:
            self.onboarding.current_step = "ready"
            self.onboarding.completed = True
            if "ready" not in self.onboarding.completed_steps:
                self.onboarding.completed_steps.append("ready")
        else:
            self.onboarding.advance(step)
        self.onboarding.simple_mode = self.profile.preferences.simple_mode
        self.onboarding.save(self.settings.data_dir / "profiles" / "onboarding.json")
        state = self.get_state()
        state["onboarding_completed"] = self.onboarding.completed
        self._publish(state)
        return {"ok": True, "onboarding": self.onboarding.copy_for_ui(), "state": state}

    async def inject_intent(
        self, intent_type: str, confidence: float = 1.0, payload: dict | None = None
    ) -> dict[str, Any]:
        """Test / accessibility path: fire an intent without hardware."""
        result = await self.intent_router.handle_raw(intent_type, confidence, payload)
        self._last_intent_result = result.to_dict()
        state = self.get_state()
        state["last_intent"] = {
            "type": intent_type,
            "confidence": confidence,
            "result": self._last_intent_result,
        }
        self._publish(state)
        return {"ok": result.ok, "result": result.to_dict(), "state": state}

    def set_predictive(self, enabled: bool) -> dict[str, Any]:
        self.settings.predictive_enabled = enabled
        self.runtime.architect.precursors.enabled = enabled
        state = self.get_state()
        state["predictive_enabled"] = enabled
        self._publish(state)
        return {"ok": True, "predictive_enabled": enabled, "state": state}

    def set_paused(self, paused: bool) -> dict[str, Any]:
        """Fail-safe override — always works, even when the agent is degraded."""
        self.profile.preferences.agent_paused = paused
        self.profile.save(self.settings.data_dir / "profiles")
        self.failsafe.note_user_pause(paused)
        # Kill physical actuators immediately on pause
        if paused:
            self.runtime.physical.enabled = False
            self.runtime.architect.force_idle = True
            self.audit.record("override.pause", "User paused Architect")
            self.caregiver.mark("pause", True)
            self.caregiver.save(
                self.settings.data_dir / "profiles" / "caregiver_checklist.json"
            )
        else:
            self.runtime.physical.enabled = self.settings.iot_enabled
            if self.failsafe.state.reason in {
                FailSafeReason.NONE,
                FailSafeReason.USER_PAUSE,
            }:
                self.runtime.architect.force_idle = False
            self.audit.record("override.resume", "User resumed Architect")
        state = self.get_state()
        state["agent_paused"] = paused
        state["preferences"] = self.profile.preferences.model_dump()
        state["failsafe"] = self.failsafe.state.to_dict()
        state["audit_recent"] = self.audit.recent(10)
        if paused:
            state["mode"] = AgentMode.IDLE.value
            state["signal"] = state.get("signal") or "good"
        self._publish(state)
        return {
            "ok": True,
            "agent_paused": paused,
            "failsafe": self.failsafe.state.to_dict(),
            "state": state,
        }

    def clear_failsafe(self) -> dict[str, Any]:
        """Manual clear after signal recovery (does not un-pause user pause)."""
        if self.profile.preferences.agent_paused:
            return {
                "ok": False,
                "message": "Architect is user-paused — Resume first",
                "failsafe": self.failsafe.state.to_dict(),
            }
        self.failsafe.clear(reason_ok="manual_clear")
        self.runtime.architect.force_idle = False
        self.runtime.physical.enabled = self.settings.iot_enabled
        state = self.get_state()
        state["failsafe"] = self.failsafe.state.to_dict()
        self._publish(state)
        return {"ok": True, "failsafe": state["failsafe"], "state": state}

    def undo(self) -> dict[str, Any]:
        # Capture tool before undo for feedback learning
        peek = self.undo_stack.peek()
        result = self.runtime.architect.undo_last()
        if result.success:
            self.runtime.insights.observe_undo()
            if peek is not None:
                self.record_feedback(peek.tool_id, "unhelpful", note="auto:undo")
            self.caregiver.mark("undo", True)
            self.caregiver.save(
                self.settings.data_dir / "profiles" / "caregiver_checklist.json"
            )
        state = self.get_state()
        state["can_undo"] = self.undo_stack.can_undo
        state["digital"] = self.runtime.digital.snapshot()
        state["last_undo"] = result.model_dump(mode="json")
        state["caregiver_checklist"] = self.caregiver.to_dict()
        self._publish(state)
        return {"ok": result.success, "result": result.model_dump(mode="json"), "state": state}

    def record_feedback(
        self,
        tool_id: str,
        rating: str,
        *,
        note: str = "",
    ) -> dict[str, Any]:
        if rating not in {"helpful", "unhelpful", "never"}:
            return {"ok": False, "message": "rating must be helpful|unhelpful|never"}
        flow = self._latest.get("flow") or {}
        mode = str(self._latest.get("mode") or "")
        out = self.feedback.record(
            tool_id,
            rating,  # type: ignore[arg-type]
            note=note,
            mode=mode,
            engagement=float(flow.get("engagement") or 0.0),
            denied_tools=list(self.profile.preferences.denied_tools),
            granted_tools=list(self.profile.preferences.granted_tools),
        )
        self.profile.preferences.denied_tools = out["denied_tools"]
        self.profile.preferences.granted_tools = out["granted_tools"]
        if rating == "unhelpful":
            self.runtime.architect.governor.penalize_cooldown(tool_id, 120.0)
        self.profile.save(self.settings.data_dir / "profiles")
        self.audit.record(
            "feedback",
            out.get("message", rating),
            tool_id=tool_id,
            rating=rating,
        )
        self.caregiver.mark("label_or_review", True)
        self.caregiver.save(
            self.settings.data_dir / "profiles" / "caregiver_checklist.json"
        )
        state = self.get_state()
        state["preferences"] = self.profile.preferences.model_dump()
        state["feedback"] = self.feedback.as_dict()
        state["last_feedback"] = out
        state["audit_recent"] = self.audit.recent(10)
        state["caregiver_checklist"] = self.caregiver.to_dict()
        self._publish(state)
        return {"ok": True, **out, "state": state}

    def submit_block_review(
        self,
        *,
        helpful_block: bool | None,
        architect_helpful: bool | None = None,
        note: str = "",
        skip: bool = False,
    ) -> dict[str, Any]:
        """End-of-block review after session stop."""
        if skip:
            self._pending_block_review = None
            self.audit.record("block_review.skip", "Block review skipped")
            state = self.get_state()
            state["pending_block_review"] = None
            self._publish(state)
            return {"ok": True, "skipped": True, "state": state}

        # Attach to last session file if current already ended
        sessions = self.list_sessions(limit=1)
        review_payload = {
            "helpful_block": helpful_block,
            "architect_helpful": architect_helpful,
            "note": note,
        }
        if self.runtime.insights.current is not None:
            self.runtime.insights.set_block_review(
                helpful_block=helpful_block,
                architect_helpful=architect_helpful,
                note=note,
            )
            self.runtime.insights.save_current_if_any()
        elif sessions:
            import json
            from pathlib import Path

            sid = sessions[0].get("session_id")
            path = self.settings.data_dir / "sessions" / f"{sid}.json"
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                from datetime import datetime as _dt

                data["block_review"] = {
                    **review_payload,
                    "timestamp": _dt.utcnow().isoformat(),
                }
                path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        self.caregiver.mark("label_or_review", True)
        self.caregiver.save(
            self.settings.data_dir / "profiles" / "caregiver_checklist.json"
        )
        self.audit.record(
            "block_review",
            "End-of-block review submitted",
            **{k: v for k, v in review_payload.items() if v is not None},
        )
        self._pending_block_review = None
        state = self.get_state()
        state["pending_block_review"] = None
        state["last_block_review"] = review_payload
        state["caregiver_checklist"] = self.caregiver.to_dict()
        state["personal_signature"] = self.personal_signature()
        self._publish(state)
        return {"ok": True, "review": review_payload, "state": state}

    def personal_signature(self) -> dict[str, Any]:
        sessions = self.list_sessions(limit=50)
        return build_personal_signature(sessions).to_dict()

    def caregiver_checklist(self) -> dict[str, Any]:
        return self.caregiver.to_dict()

    def mark_caregiver_item(self, item_id: str, done: bool = True) -> dict[str, Any]:
        self.caregiver.mark(item_id, done)
        if item_id == "helper_leaves" and done:
            self.audit.record("caregiver.complete", "Helper marked setup complete")
        self.caregiver.save(
            self.settings.data_dir / "profiles" / "caregiver_checklist.json"
        )
        state = self.get_state()
        state["caregiver_checklist"] = self.caregiver.to_dict()
        self._publish(state)
        return {"ok": True, "checklist": self.caregiver.to_dict(), "state": state}

    def set_quiet_hours(
        self,
        *,
        enabled: bool | None = None,
        start_hour: int | None = None,
        end_hour: int | None = None,
    ) -> dict[str, Any]:
        prefs = self.profile.preferences
        if enabled is not None:
            prefs.quiet_hours_enabled = enabled
        if start_hour is not None:
            prefs.quiet_hours_start = int(start_hour) % 24
        if end_hour is not None:
            prefs.quiet_hours_end = int(end_hour) % 24
        self.profile.save(self.settings.data_dir / "profiles")
        qh = QuietHours(
            enabled=prefs.quiet_hours_enabled,
            start_hour=prefs.quiet_hours_start,
            end_hour=prefs.quiet_hours_end,
        )
        self.audit.record(
            "prefs.quiet_hours",
            f"quiet_hours enabled={qh.enabled} {qh.start_hour}-{qh.end_hour}",
        )
        state = self.get_state()
        state["quiet_hours"] = qh.to_dict()
        state["preferences"] = prefs.model_dump()
        self._publish(state)
        return {"ok": True, "quiet_hours": qh.to_dict(), "state": state}

    def accept_recipe_suggestion(self) -> dict[str, Any]:
        sug = self._recipe_suggestion()
        if not sug:
            return {"ok": False, "message": "No suggestion active"}
        recipe = str(sug["suggested_recipe"])
        self.audit.record("recipe.accept_suggestion", f"Accepted {recipe}", **sug)
        return self.set_recipe(recipe)

    def get_audit(self, limit: int = 50) -> dict[str, Any]:
        return {"ok": True, "events": self.audit.recent(limit)}

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
        self.caregiver.mark("rest", True)
        self.caregiver.save(
            self.settings.data_dir / "profiles" / "caregiver_checklist.json"
        )
        state = self.get_state()
        state["agent_paused"] = True
        state["digital"] = self.runtime.digital.snapshot()
        state["mode"] = AgentMode.TRANSITION.value
        state["caregiver_checklist"] = self.caregiver.to_dict()
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
        detect_active_app: bool | None = None,
    ) -> dict[str, Any]:
        if active_app is not None:
            self._active_app = active_app or None
        if user_goal is not None:
            self._user_goal = user_goal or None
        if detect_active_app is not None:
            self.settings.detect_active_app = detect_active_app
        # One-shot detect if enabled and no manual app
        if self.settings.detect_active_app and not self._active_app:
            from neural_flow_architect.core.active_app import detect_active_app as _detect

            det = _detect(enabled=True)
            if det.app_name:
                self._active_app = det.app_name
        state = self.get_state()
        state["context"] = self.context_for_runtime().model_dump()
        state["detect_active_app"] = self.settings.detect_active_app
        self._publish(state)
        return {"ok": True, "context": state["context"], "state": state}

    def trust_metrics(self) -> dict[str, Any]:
        from neural_flow_architect.insights.trust import compute_trust_metrics

        session = self.runtime.insights.snapshot_current() or {}
        # Merge last persisted if no live session
        if not session:
            sessions = self.list_sessions()
            session = sessions[0] if sessions else {}
        fb_hist = self.feedback.as_dict().get("history") or []
        uptime = float((self.get_state().get("session_health") or {}).get("uptime_sec") or 0)
        fs = self.failsafe.state.to_dict()
        fs_sec = float(fs.get("seconds_active") or 0)
        metrics = compute_trust_metrics(
            actions_count=int(session.get("actions_count") or 0),
            undos_count=int(session.get("undos_count") or 0),
            feedback_history=fb_hist,
            denied_tools=list(self.profile.preferences.denied_tools),
            failsafe_active_seconds=fs_sec,
            session_uptime_sec=uptime,
        )
        return {
            "ok": True,
            "trust": metrics,
            "session_id": session.get("session_id"),
            "iot": self.runtime.physical.status(),
        }

    def environment_status(self) -> dict[str, Any]:
        return {
            "ok": True,
            "iot": self.runtime.physical.status(),
            "agent_dry_run": self.runtime.architect.dry_run,
            "iot_force_dry_run": self.runtime.physical.force_dry_run,
            "detect_active_app": self.settings.detect_active_app,
        }

    def set_iot_dry_run(self, force_dry_run: bool) -> dict[str, Any]:
        self.settings.iot_force_dry_run = force_dry_run
        self.runtime.physical.force_dry_run = force_dry_run
        return {"ok": True, "iot": self.runtime.physical.status()}

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

    def list_sessions(self, limit: int = 20) -> list[dict[str, Any]]:
        return self.runtime.insights.list_sessions(limit=limit)

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
