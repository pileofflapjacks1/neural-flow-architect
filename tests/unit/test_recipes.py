"""Environment recipe tests."""

from neural_flow_architect.environment.digital import DigitalOrchestrator
from neural_flow_architect.environment.recipes import apply_recipe, list_recipes


def test_list_recipes() -> None:
    names = {r["name"] for r in list_recipes()}
    assert names == {"study", "create", "rest", "social"}


def test_apply_study_recipe() -> None:
    d = DigitalOrchestrator()
    out = apply_recipe(d, "study")
    assert out["recipe"] == "study"
    assert d.focus_enabled is True
    assert d.notifications_suppressed is True


def test_apply_rest_recipe() -> None:
    d = DigitalOrchestrator()
    apply_recipe(d, "study")
    apply_recipe(d, "rest")
    assert d.focus_enabled is False
    assert d.rest_mode is True
