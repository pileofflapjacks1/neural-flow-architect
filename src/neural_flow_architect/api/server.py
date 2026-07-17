"""Local-first REST + WebSocket API for the companion UI."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from neural_flow_architect import __version__
from neural_flow_architect.core.session import SessionController
from neural_flow_architect.core.settings import Settings, get_settings


class PauseBody(BaseModel):
    paused: bool = True


class ToolPrefBody(BaseModel):
    tool_id: str
    action: str = Field(description="never | always | clear")


class LabelBody(BaseModel):
    felt_in_flow: bool
    note: str = ""


class StartBody(BaseModel):
    duration_sec: float | None = None
    adapter: str | None = None


class RecipeBody(BaseModel):
    recipe: str = "study"


class ContextBody(BaseModel):
    active_app: str | None = None
    user_goal: str | None = None
    detect_active_app: bool | None = None


class IotDryRunBody(BaseModel):
    force_dry_run: bool = True


class PredictiveBody(BaseModel):
    enabled: bool = True


class SimpleModeBody(BaseModel):
    enabled: bool = True


class PresetBody(BaseModel):
    preset_id: str


class OnboardingBody(BaseModel):
    step: str | None = None
    caregiver_assisted: bool | None = None
    complete: bool = False


class IntentBody(BaseModel):
    intent_type: str
    confidence: float = 1.0
    payload: dict[str, Any] = Field(default_factory=dict)


class A11yBody(BaseModel):
    ui_scale: float | None = None
    high_contrast: bool | None = None
    reduced_motion: bool | None = None
    dwell_ms: int | None = None
    sticky_controls: bool | None = None
    keyboard_enabled: bool | None = None
    voice_command_bar: bool | None = None
    auto_start_on_preset: bool | None = None


class MultimodalBody(BaseModel):
    source: str = Field(description="keyboard | voice | text")
    code: str | None = None  # KeyboardEvent.code
    text: str | None = None


class ImportBody(BaseModel):
    bundle: dict[str, Any]


class FeedbackBody(BaseModel):
    tool_id: str
    rating: str = Field(description="helpful | unhelpful | never")
    note: str = ""


class QuietHoursBody(BaseModel):
    enabled: bool | None = None
    start_hour: int | None = None
    end_hour: int | None = None


class BlockReviewBody(BaseModel):
    helpful_block: bool | None = None
    architect_helpful: bool | None = None
    note: str = ""
    skip: bool = False


class CaregiverItemBody(BaseModel):
    item_id: str
    done: bool = True


def create_app(
    settings: Settings | None = None,
    controller: SessionController | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    session = controller or SessionController(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
        app.state.session = session
        app.state.settings = settings
        yield
        if session.is_running:
            await session.stop()

    app = FastAPI(
        title="Neural Flow Architect",
        version=__version__,
        description="Local-only companion API. Not a medical device.",
        lifespan=lifespan,
    )

    # Localhost companion UI (Vite default)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://127.0.0.1:4173",
            "http://localhost:4173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "ok": True,
            "version": __version__,
            "local_only": settings.local_only,
            "disclaimer": "Research / assistive software — not a medical device",
        }

    @app.get("/state")
    async def get_state() -> dict[str, Any]:
        return session.get_state()

    @app.post("/session/start")
    async def start_session(body: StartBody | None = None) -> dict[str, Any]:
        body = body or StartBody()
        if body.adapter:
            settings.adapter = body.adapter  # type: ignore[assignment]
            session.settings.adapter = body.adapter  # type: ignore[assignment]
        return await session.start(duration_sec=body.duration_sec)

    @app.post("/session/stop")
    async def stop_session() -> dict[str, Any]:
        return await session.stop()

    @app.post("/agent/pause")
    async def pause_agent(body: PauseBody) -> dict[str, Any]:
        """Fail-safe override — always available."""
        return session.set_paused(body.paused)

    @app.post("/agent/failsafe/clear")
    async def clear_failsafe() -> dict[str, Any]:
        return session.clear_failsafe()

    @app.get("/agent/failsafe")
    async def get_failsafe() -> dict[str, Any]:
        return {"failsafe": session.failsafe.state.to_dict()}

    @app.post("/agent/undo")
    async def undo_agent() -> dict[str, Any]:
        return session.undo()

    @app.post("/agent/feedback")
    async def agent_feedback(body: FeedbackBody) -> dict[str, Any]:
        return session.record_feedback(body.tool_id, body.rating, note=body.note)

    @app.post("/agent/rest")
    async def rest_mode() -> dict[str, Any]:
        return session.rest_mode()

    @app.post("/prefs/tool")
    async def tool_pref(body: ToolPrefBody) -> dict[str, Any]:
        return session.set_tool_preference(body.tool_id, body.action)

    @app.post("/session/label")
    async def label_session(body: LabelBody) -> dict[str, Any]:
        return session.label_flow(body.felt_in_flow, body.note)

    @app.get("/sessions")
    async def list_sessions() -> dict[str, Any]:
        return {"sessions": session.list_sessions()}

    @app.get("/session/export")
    async def export_session() -> dict[str, Any]:
        return session.export_current()

    @app.get("/recipes")
    async def recipes() -> dict[str, Any]:
        from neural_flow_architect.environment.recipes import list_recipes

        return {"recipes": list_recipes()}

    @app.post("/recipe")
    async def set_recipe(body: RecipeBody) -> dict[str, Any]:
        return session.set_recipe(body.recipe)

    @app.post("/context")
    async def set_context(body: ContextBody) -> dict[str, Any]:
        return session.set_context(
            active_app=body.active_app,
            user_goal=body.user_goal,
            detect_active_app=body.detect_active_app,
        )

    @app.get("/trust")
    async def trust() -> dict[str, Any]:
        return session.trust_metrics()

    @app.get("/audit")
    async def audit(limit: int = 50) -> dict[str, Any]:
        return session.get_audit(limit=min(limit, 200))

    @app.get("/quiet_hours")
    async def get_quiet_hours() -> dict[str, Any]:
        from neural_flow_architect.core.quiet_hours import QuietHours

        prefs = session.profile.preferences
        qh = QuietHours(
            enabled=prefs.quiet_hours_enabled,
            start_hour=prefs.quiet_hours_start,
            end_hour=prefs.quiet_hours_end,
        )
        return {"quiet_hours": qh.to_dict()}

    @app.post("/quiet_hours")
    async def post_quiet_hours(body: QuietHoursBody) -> dict[str, Any]:
        return session.set_quiet_hours(
            enabled=body.enabled,
            start_hour=body.start_hour,
            end_hour=body.end_hour,
        )

    @app.post("/recipe/accept_suggestion")
    async def accept_recipe_suggestion() -> dict[str, Any]:
        return session.accept_recipe_suggestion()

    @app.post("/session/block_review")
    async def block_review(body: BlockReviewBody) -> dict[str, Any]:
        return session.submit_block_review(
            helpful_block=body.helpful_block,
            architect_helpful=body.architect_helpful,
            note=body.note,
            skip=body.skip,
        )

    @app.get("/signature")
    async def signature() -> dict[str, Any]:
        return {"ok": True, "signature": session.personal_signature()}

    @app.get("/caregiver")
    async def caregiver_get() -> dict[str, Any]:
        return {"ok": True, "checklist": session.caregiver_checklist()}

    @app.post("/caregiver")
    async def caregiver_post(body: CaregiverItemBody) -> dict[str, Any]:
        return session.mark_caregiver_item(body.item_id, body.done)

    @app.get("/environment")
    async def environment() -> dict[str, Any]:
        return session.environment_status()

    @app.post("/environment/iot_dry_run")
    async def iot_dry_run(body: IotDryRunBody) -> dict[str, Any]:
        return session.set_iot_dry_run(body.force_dry_run)

    @app.get("/coaching")
    async def coaching() -> dict[str, Any]:
        return session.coaching()

    @app.get("/profile")
    async def profile() -> dict[str, Any]:
        return {
            "preferences": session.profile.preferences.model_dump(),
            "thresholds": {
                "protect": session.profile.protect_engagement_threshold,
                "deep": session.profile.deep_flow_engagement_threshold,
            },
            "recipe": session._recipe,
            "predictive_enabled": settings.predictive_enabled,
            "llm_enabled": settings.llm_enabled or settings.agent_mode == "llm_local",
        }

    @app.post("/agent/predictive")
    async def set_predictive(body: PredictiveBody) -> dict[str, Any]:
        return session.set_predictive(body.enabled)

    @app.post("/ui/simple_mode")
    async def simple_mode(body: SimpleModeBody) -> dict[str, Any]:
        return session.set_simple_mode(body.enabled)

    @app.get("/presets")
    async def presets() -> dict[str, Any]:
        from neural_flow_architect.personalization.presets import list_presets

        return {"presets": list_presets(settings.data_dir / "presets")}

    @app.post("/presets/apply")
    async def apply_preset(body: PresetBody) -> dict[str, Any]:
        return session.apply_preset(body.preset_id)

    @app.get("/onboarding")
    async def get_onboarding() -> dict[str, Any]:
        return session.get_onboarding()

    @app.post("/onboarding")
    async def post_onboarding(body: OnboardingBody) -> dict[str, Any]:
        return session.advance_onboarding(
            step=body.step,
            caregiver_assisted=body.caregiver_assisted,
            complete=body.complete,
        )

    @app.post("/intent")
    async def post_intent(body: IntentBody) -> dict[str, Any]:
        """Inject a discrete BCI-style intent (also used for accessibility testing)."""
        return await session.inject_intent(
            body.intent_type, body.confidence, body.payload
        )

    @app.get("/intents/vocabulary")
    async def intent_vocab() -> dict[str, Any]:
        from neural_flow_architect.core.intents import KNOWN_INTENTS
        from neural_flow_architect.core.multimodal import keymap_for_ui

        return {
            "intents": sorted(KNOWN_INTENTS),
            "shortcuts": keymap_for_ui(),
            "note": "Stable control vocabulary for future implant intent APIs",
        }

    @app.post("/input/command")
    async def multimodal_command(body: MultimodalBody) -> dict[str, Any]:
        return await session.multimodal_command(
            source=body.source, code=body.code, text=body.text
        )

    @app.get("/a11y")
    async def get_a11y() -> dict[str, Any]:
        return {"a11y": session._a11y_payload()}

    @app.post("/a11y")
    async def post_a11y(body: A11yBody) -> dict[str, Any]:
        return session.update_a11y(**body.model_dump(exclude_none=True))

    @app.get("/profile/export")
    async def export_profile() -> dict[str, Any]:
        return session.export_profile()

    @app.post("/profile/import")
    async def import_profile(body: ImportBody) -> dict[str, Any]:
        return session.import_profile(body.bundle)

    @app.get("/features")
    async def feature_flags() -> dict[str, Any]:
        return {
            "predictive_enabled": settings.predictive_enabled,
            "llm_enabled": settings.llm_enabled or settings.agent_mode == "llm_local",
            "os_notifications": settings.os_notifications,
            "iot_enabled": settings.iot_enabled,
            "local_only": settings.local_only,
            "allow_cloud_llm": settings.allow_cloud_llm,
            "simple_mode": session.profile.preferences.simple_mode,
            "intent_control": True,
        }

    @app.websocket("/ws/state")
    async def ws_state(ws: WebSocket) -> None:
        await ws.accept()
        queue = session.subscribe()
        try:
            while True:
                # Also accept client pings / commands lightly
                get_state_task = asyncio.create_task(queue.get())
                recv_task = asyncio.create_task(ws.receive_text())
                done, pending = await asyncio.wait(
                    {get_state_task, recv_task},
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for t in pending:
                    t.cancel()
                if get_state_task in done:
                    state = get_state_task.result()
                    await ws.send_json(state)
                if recv_task in done:
                    try:
                        msg = recv_task.result()
                    except Exception:
                        break
                    if msg in {"ping", "hello"}:
                        await ws.send_json({"type": "pong", "state": session.get_state()})
        except WebSocketDisconnect:
            pass
        finally:
            session.unsubscribe(queue)

    return app


def run_server(settings: Settings | None = None) -> None:
    import uvicorn

    settings = settings or get_settings()
    app = create_app(settings)
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )
