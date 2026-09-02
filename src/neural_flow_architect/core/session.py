"""Session controller — long-running loop with control plane for the local API."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime
from typing import Any

from neural_flow_architect.agent.undo import UndoStack
from neural_flow_architect.core.active_app import set_user_category_map
from neural_flow_architect.core.app_map import AppCategoryMap
from neural_flow_architect.core.caregiver import CaregiverChecklist
from neural_flow_architect.core.context import enrich_context
from neural_flow_architect.core.failsafe import FailSafeGuard, FailSafeReason
from neural_flow_architect.core.intents import IntentRouter
from neural_flow_architect.core.onboarding import OnboardingState
from neural_flow_architect.core.quiet_hours import QuietHours
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
from neural_flow_architect.insights.scoreboard import (
    build_policy_scoreboard,
    build_weekly_recap,
)
from neural_flow_architect.insights.session_recap import build_session_recap
from neural_flow_architect.personalization.feedback import FeedbackStore
from neural_flow_architect.personalization.learning import (
    learn_from_block_review,
    learn_from_session_summary,
    update_thresholds_from_label,
)
from neural_flow_architect.personalization.presets import get_preset, list_presets
from neural_flow_architect.personalization.profile import UserProfile
from neural_flow_architect.personalization.signature import build_personal_signature
from neural_flow_architect.privacy.audit import AuditLog
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
        self.app_map = AppCategoryMap.load(
            self.settings.data_dir / "profiles" / "app_categories.json"
        )
        set_user_category_map(self.app_map)
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
