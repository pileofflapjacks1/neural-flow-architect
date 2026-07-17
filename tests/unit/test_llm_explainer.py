"""Local LLM explainer safety tests (no network required)."""

from datetime import datetime

import pytest

from neural_flow_architect.agent.llm_explainer import LocalLLMExplainer, maybe_llm_explain
from neural_flow_architect.core.types import (
    ActionProposal,
    ContextSnapshot,
    Explanation,
    FlowEstimate,
    FlowState,
    ImpactLevel,
    QualityFlags,
    UserPreferences,
    WorldSnapshot,
)


def _snap() -> WorldSnapshot:
    return WorldSnapshot(
        time=datetime.utcnow(),
        flow=FlowEstimate(
            timestamp_ns=1,
            engagement=0.8,
            arousal_balance=0.5,
            self_ref_proxy=0.2,
            effort_ease=0.6,
            confidence=0.9,
            state=FlowState.FLOW,
            minutes_in_state=2.0,
        ),
        quality=QualityFlags(overall=0.9),
        context=ContextSnapshot(recipe="study"),
        preferences=UserPreferences(),
    )


def test_summary_payload_has_no_raw_fields() -> None:
    llm = LocalLLMExplainer(enabled=True)
    prop = ActionProposal(
        tool_id="focus.enable",
        impact=ImpactLevel.MEDIUM,
        score=0.8,
    )
    payload = llm.build_summary_payload(prop, _snap(), "template text")
    blob = str(payload)
    assert "raw" not in blob.lower()
    assert "samples" not in blob.lower()
    assert payload["flow"]["state"] == "flow"
    assert "template_explanation" in payload


@pytest.mark.asyncio
async def test_cloud_blocked_without_allow() -> None:
    llm = LocalLLMExplainer(
        enabled=True,
        base_url="https://api.example.com",
        allow_cloud=False,
    )
    result = await llm.rephrase(
        ActionProposal(tool_id="x", impact=ImpactLevel.LOW),
        _snap(),
        "hello",
    )
    assert result is None
    assert llm.last_error is not None


@pytest.mark.asyncio
async def test_maybe_llm_disabled_returns_template() -> None:
    template = Explanation(action="focus.enable", text="template")
    out = await maybe_llm_explain(
        LocalLLMExplainer(enabled=False),
        ActionProposal(tool_id="focus.enable", impact=ImpactLevel.MEDIUM),
        _snap(),
        template,
    )
    assert out.text == "template"
