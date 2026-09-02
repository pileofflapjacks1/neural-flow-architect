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
