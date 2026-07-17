"""Quiet hours and audit log tests."""

from pathlib import Path
from datetime import datetime

from neural_flow_architect.core.quiet_hours import QuietHours
from neural_flow_architect.core.session import SessionController
from neural_flow_architect.core.settings import Settings
from neural_flow_architect.privacy.audit import AuditLog
from neural_flow_architect.core.active_app import recipe_suggestion


def test_quiet_hours_wrap_midnight() -> None:
    qh = QuietHours(enabled=True, start_hour=22, end_hour=7)
    assert qh.is_quiet(datetime(2026, 1, 1, 23, 0))
    assert qh.is_quiet(datetime(2026, 1, 1, 3, 0))
    assert not qh.is_quiet(datetime(2026, 1, 1, 12, 0))


def test_audit_log(tmp_path: Path) -> None:
    log = AuditLog(tmp_path)
    log.record("test", "hello", tool_id="x")
    recent = log.recent(5)
    assert recent
    assert recent[-1]["message"] == "hello"
    assert "data" not in recent[-1].get("detail", {})


def test_recipe_suggestion() -> None:
    sug = recipe_suggestion(
        current_recipe="study", app_category="social", suggest_enabled=True
    )
    assert sug is not None
    assert sug["suggested_recipe"] == "social"
    assert recipe_suggestion(
        current_recipe="study", app_category="study", suggest_enabled=True
    ) is None


def test_session_quiet_hours(tmp_path: Path) -> None:
    session = SessionController(Settings(adapter="simulator", data_dir=tmp_path))
    out = session.set_quiet_hours(enabled=True, start_hour=22, end_hour=7)
    assert out["ok"]
    assert out["quiet_hours"]["enabled"] is True
