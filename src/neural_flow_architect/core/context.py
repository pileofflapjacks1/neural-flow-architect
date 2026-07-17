"""Non-neural context enrichment for WorldSnapshot."""

from __future__ import annotations

from datetime import datetime

from neural_flow_architect.core.active_app import (
    categorize_app,
    detect_active_app,
    recipe_hint_for_category,
    _USER_MAP,
)
from neural_flow_architect.core.types import ContextSnapshot


def time_of_day_bucket(hour: int) -> str:
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 21:
        return "evening"
    return "night"


def enrich_context(
    base: ContextSnapshot | None = None,
    *,
    now: datetime | None = None,
    active_app: str | None = None,
    app_category: str | None = None,
    user_goal: str | None = None,
    recipe: str | None = None,
    detect_app: bool = False,
) -> ContextSnapshot:
    now = now or datetime.now()
    ctx = base.model_copy(deep=True) if base is not None else ContextSnapshot()
    ctx.hour = now.hour
    ctx.time_of_day = time_of_day_bucket(now.hour)

    if detect_app and active_app is None:
        detected = detect_active_app(enabled=True)
        if detected.app_name:
            ctx.active_app = detected.app_name
            ctx.app_category = detected.category
    if active_app is not None:
        ctx.active_app = active_app
        ctx.app_category = app_category or categorize_app(
            active_app, user_map=_USER_MAP
        )
    elif app_category is not None:
        ctx.app_category = app_category

    if user_goal is not None:
        ctx.user_goal = user_goal
    if recipe is not None:
        ctx.recipe = recipe
    elif not ctx.recipe:
        # Soft recipe from app category when user hasn't locked one
        hint = recipe_hint_for_category(ctx.app_category)
        ctx.recipe = hint or "study"
    # Soft default goal from recipe
    if not ctx.user_goal:
        ctx.user_goal = {
            "study": "deep work",
            "create": "creative focus",
            "rest": "recovery",
            "social": "communication",
        }.get(ctx.recipe, "deep work")
    return ctx
