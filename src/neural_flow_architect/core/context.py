"""Non-neural context enrichment for WorldSnapshot."""

from __future__ import annotations

from datetime import datetime

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
    user_goal: str | None = None,
    recipe: str | None = None,
) -> ContextSnapshot:
    now = now or datetime.now()
    ctx = base.model_copy(deep=True) if base is not None else ContextSnapshot()
    ctx.hour = now.hour
    ctx.time_of_day = time_of_day_bucket(now.hour)
    if active_app is not None:
        ctx.active_app = active_app
    if user_goal is not None:
        ctx.user_goal = user_goal
    if recipe is not None:
        ctx.recipe = recipe
    elif not ctx.recipe:
        ctx.recipe = "study"
    # Soft default goal from recipe
    if not ctx.user_goal:
        ctx.user_goal = {
            "study": "deep work",
            "create": "creative focus",
            "rest": "recovery",
            "social": "communication",
        }.get(ctx.recipe, "deep work")
    return ctx
