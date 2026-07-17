"""Multi-agent policy module tests."""

from datetime import datetime

from neural_flow_architect.agent.policies.rules import propose_actions
from neural_flow_architect.core.types import (
    AgentMode,
    ContextSnapshot,
    FlowEstimate,
    FlowState,
    QualityFlags,
    UserPreferences,
    WorldSnapshot,
)


def _snap(state: FlowState, recipe: str = "study") -> WorldSnapshot:
    return WorldSnapshot(
        time=datetime.utcnow(),
        flow=FlowEstimate(
            timestamp_ns=1,
            engagement=0.8,
            arousal_balance=0.6,
            self_ref_proxy=0.3,
            effort_ease=0.6,
            confidence=0.9,
            state=state,
            minutes_in_state=3.0,
        ),
        quality=QualityFlags(overall=0.9),
        context=ContextSnapshot(recipe=recipe, user_goal="deep work"),
        preferences=UserPreferences(),
    )


def test_protect_includes_recipe_and_module_cause() -> None:
    props = propose_actions(AgentMode.PROTECT, _snap(FlowState.FLOW))
    ids = {p.tool_id for p in props}
    assert "notify.suppress_noncritical" in ids
    assert "recipe.apply" in ids
    assert any(c.get("value") == "protector" for p in props for c in p.causes)


def test_transition_suggests_rest_recipe() -> None:
    props = propose_actions(AgentMode.TRANSITION, _snap(FlowState.FATIGUED))
    recipe_props = [p for p in props if p.tool_id == "recipe.apply"]
    assert recipe_props
    assert recipe_props[0].params.get("recipe") == "rest"


def test_low_quality_strips_iot() -> None:
    snap = _snap(FlowState.FLOW)
    snap.preferences.allow_iot = True
    snap.preferences.protect_style = "assertive"
    snap.quality.overall = 0.2
    props = propose_actions(AgentMode.PROTECT, snap)
    assert all(not p.tool_id.startswith("iot.") for p in props)
