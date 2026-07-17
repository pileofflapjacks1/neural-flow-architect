"""Environment recipes — named focus profiles for digital (and later physical) context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from neural_flow_architect.environment.digital import DigitalOrchestrator

RECIPES = ("study", "create", "rest", "social")


@dataclass(frozen=True)
class RecipeSpec:
    name: str
    density: str
    focus: bool
    suppress_notifications: bool
    description: str


RECIPE_SPECS: dict[str, RecipeSpec] = {
    "study": RecipeSpec(
        name="study",
        density="minimal",
        focus=True,
        suppress_notifications=True,
        description="Deep study — quiet UI, focus on, non-critical notices off",
    ),
    "create": RecipeSpec(
        name="create",
        density="calm",
        focus=True,
        suppress_notifications=True,
        description="Creative work — calm chrome, protect attention",
    ),
    "rest": RecipeSpec(
        name="rest",
        density="normal",
        focus=False,
        suppress_notifications=False,
        description="Rest / recovery — restore awareness, no focus pressure",
    ),
    "social": RecipeSpec(
        name="social",
        density="normal",
        focus=False,
        suppress_notifications=False,
        description="Social / communication — full notifications",
    ),
}


def recipe_protect_bonus(recipe: str) -> float:
    return {"study": 0.08, "create": 0.06, "rest": -0.2, "social": -0.15}.get(recipe, 0.0)


def recipe_reentry_bonus(recipe: str) -> float:
    return {"study": 0.05, "create": 0.05, "rest": -0.1, "social": 0.0}.get(recipe, 0.0)


def apply_recipe(digital: DigitalOrchestrator, recipe: str) -> dict[str, Any]:
    spec = RECIPE_SPECS.get(recipe, RECIPE_SPECS["study"])
    digital.set_density(spec.density)
    digital.set_focus(spec.focus)
    digital.suppress_noncritical(spec.suppress_notifications)
    if recipe == "rest":
        digital.set_rest_mode(True)
    else:
        digital.rest_mode = False
    digital.history.append(f"recipe={spec.name}")
    return {
        "recipe": spec.name,
        "description": spec.description,
        "digital": digital.snapshot(),
    }


def list_recipes() -> list[dict[str, str]]:
    return [{"name": s.name, "description": s.description} for s in RECIPE_SPECS.values()]
