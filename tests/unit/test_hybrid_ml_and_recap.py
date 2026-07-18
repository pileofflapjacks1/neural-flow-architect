"""Hybrid flow ML calibrator + post-session recap."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from neural_flow_architect.api.server import create_app
from neural_flow_architect.core.session import SessionController
from neural_flow_architect.core.settings import Settings
from neural_flow_architect.core.types import FeatureWindow, QualityFlags
from neural_flow_architect.flow.engine import FlowEngine
from neural_flow_architect.flow.ml_calibrator import FlowMLCalibrator, features_to_vector
from neural_flow_architect.insights.session_recap import build_session_recap


def test_features_to_vector_order() -> None:
    v = features_to_vector(
        {
            "engagement_proxy": 0.8,
            "arousal_proxy": 0.5,
            "self_ref_proxy": 0.2,
            "ease_proxy": 0.6,
        },
        quality_overall=0.9,
    )
    assert len(v) == 5
    assert v[0] == 0.8
    assert v[-1] == 0.9


def test_calibrator_trains_and_blends(tmp_path: Path) -> None:
    path = tmp_path / "samples.jsonl"
    cal = FlowMLCalibrator(samples_path=path, min_samples=8, blend_weight=0.5)
    # Balanced synthetic labels
    for i in range(10):
        eng = 0.8 if i % 2 == 0 else 0.25
        cal.append_sample(
            {
                "engagement_proxy": eng,
                "arousal_proxy": 0.5,
                "self_ref_proxy": 0.3 if eng > 0.5 else 0.7,
                "ease_proxy": eng,
                "quality_overall": 0.9,
            },
            felt_in_flow=eng > 0.5,
        )
    st = cal.retrain_from_disk()
    assert st.trained is True
    assert st.n_samples == 10
    p_hi = cal.predict_in_flow_proba(
        {
            "engagement_proxy": 0.85,
            "arousal_proxy": 0.5,
            "self_ref_proxy": 0.2,
            "ease_proxy": 0.7,
            "quality_overall": 0.9,
        }
    )
    p_lo = cal.predict_in_flow_proba(
        {
            "engagement_proxy": 0.2,
            "arousal_proxy": 0.5,
            "self_ref_proxy": 0.8,
            "ease_proxy": 0.2,
            "quality_overall": 0.9,
        }
    )
    assert p_hi is not None and p_lo is not None
    assert p_hi > p_lo

    blended, reasons = cal.blend_engagement(
        0.5,
        {
            "engagement_proxy": 0.85,
            "arousal_proxy": 0.5,
            "self_ref_proxy": 0.2,
            "ease_proxy": 0.7,
            "quality_overall": 0.9,
        },
    )
    assert 0.0 <= blended <= 1.0
    assert any("hybrid_ml" in r for r in reasons)


def test_flow_engine_with_calibrator(tmp_path: Path) -> None:
    path = tmp_path / "s.jsonl"
    cal = FlowMLCalibrator(samples_path=path, min_samples=8, blend_weight=0.4)
    for i in range(10):
        eng = 0.9 if i < 5 else 0.2
        cal.append_sample(
            {
                "engagement_proxy": eng,
                "arousal_proxy": 0.55,
                "self_ref_proxy": 0.3,
                "ease_proxy": 0.6,
                "quality_overall": 1.0,
            },
            felt_in_flow=i < 5,
        )
    cal.retrain_from_disk()
    eng = FlowEngine(calibrator=cal)
    fw = FeatureWindow(
        timestamp_ns=1,
        features={
            "engagement_proxy": 0.7,
            "arousal_proxy": 0.55,
            "self_ref_proxy": 0.25,
            "ease_proxy": 0.55,
            "variance": 1.0,
        },
        quality=QualityFlags(overall=0.95),
    )
    est = eng.update(fw)
    assert 0.0 <= est.engagement <= 1.0
    assert eng.last_feature_snapshot()


def test_session_recap_helped_hurt() -> None:
    recap = build_session_recap(
        {
            "session_id": "abc",
            "recipe": "study",
            "actions_count": 10,
            "undos_count": 4,
            "flow_minutes": 15.0,
            "peak_engagement": 0.8,
            "labels": [{"felt_in_flow": True}, {"felt_in_flow": False}],
            "block_review": {"helpful_block": True, "architect_helpful": False},
            "timeline": [
                {"kind": "action", "detail": {"tool_id": "focus.enable"}},
                {"kind": "action", "detail": {"tool_id": "focus.enable"}},
            ],
            "state_minutes": {"flow": 10.0, "fatigued": 2.0},
        }
    )
    assert recap["ok"] is True
    assert recap["helped"]
    assert recap["hurt"]
    assert recap["recommendations"]
    assert recap["totals"]["undo_rate"] == 0.4


@pytest.mark.asyncio
async def test_api_flow_ml_and_recap(tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    settings = Settings(
        adapter="simulator",
        data_dir=tmp_path,
        dry_run=True,
        hybrid_ml_enabled=True,
    )
    controller = SessionController(settings)
    app = create_app(settings, controller)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        ml = await client.get("/flow/ml")
        assert ml.status_code == 200
        assert ml.json()["hybrid_ml"]["enabled"] is True

        rec = await client.get("/session/recap")
        assert rec.status_code == 200
        assert "recap" in rec.json()
