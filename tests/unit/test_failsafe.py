"""Fail-safe guard tests."""

from neural_flow_architect.core.failsafe import FailSafeGuard, FailSafeReason


def test_low_quality_trips() -> None:
    g = FailSafeGuard(low_quality_streak=3, low_quality_threshold=0.35)
    for _ in range(3):
        g.note_frame(0.1)
    assert g.state.active
    assert g.state.reason == FailSafeReason.LOW_QUALITY
    assert g.allow_tool("notify.suppress_noncritical", impact="medium") is False
    assert g.allow_tool("notify.allow_all", impact="low") is True


def test_user_pause() -> None:
    g = FailSafeGuard()
    g.note_user_pause(True)
    assert g.blocks_proactive
    g.note_user_pause(False)
    assert not g.blocks_proactive


def test_iot_blocked_in_failsafe() -> None:
    g = FailSafeGuard()
    g.trip(FailSafeReason.STREAM_STALL, "stall")
    assert g.allow_tool("iot.lights.dim_for_focus", impact="medium") is False
