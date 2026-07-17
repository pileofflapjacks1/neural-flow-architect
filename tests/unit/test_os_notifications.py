"""OS notification backend tests."""

from neural_flow_architect.environment.os_notifications import (
    NullNotificationBackend,
    build_notification_backend,
)


def test_null_backend() -> None:
    b = NullNotificationBackend()
    assert b.suppress_noncritical()["ok"] is True
    assert b.suppressed is True
    assert b.restore()["ok"] is True
    assert b.suppressed is False


def test_build_disabled() -> None:
    b = build_notification_backend(enabled=False)
    assert b.name.startswith("null") or b.name == "null"
