"""Active app categorization and trust metrics tests."""

from neural_flow_architect.core.active_app import categorize_app, recipe_hint_for_category
from neural_flow_architect.core.context import enrich_context
from neural_flow_architect.insights.trust import compute_trust_metrics


def test_categorize_apps() -> None:
    assert categorize_app("Visual Studio Code") == "study"
    assert categorize_app("Slack") == "social"
    assert categorize_app("Figma") == "create"


def test_enrich_with_app() -> None:
    ctx = enrich_context(active_app="Obsidian", recipe="study")
    assert ctx.app_category == "study"
    assert recipe_hint_for_category("social") == "social"


def test_trust_metrics_high_with_helpful() -> None:
    m = compute_trust_metrics(
        actions_count=10,
        undos_count=0,
        feedback_history=[
            {"rating": "helpful"},
            {"rating": "helpful"},
            {"rating": "helpful"},
        ],
    )
    assert m["trust_score"] >= 0.7


def test_trust_metrics_low_with_undos() -> None:
    m = compute_trust_metrics(actions_count=10, undos_count=8, feedback_history=[])
    assert m["undo_rate"] == 0.8
    assert m["trust_score"] < 0.6
