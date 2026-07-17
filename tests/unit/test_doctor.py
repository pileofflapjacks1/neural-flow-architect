"""Doctor health check tests."""

from neural_flow_architect.core.doctor import run_doctor


def test_doctor_runs() -> None:
    report = run_doctor()
    assert report.version
    assert len(report.checks) >= 5
    names = {c.name for c in report.checks}
    assert "python" in names
    assert "local_only_default" in names
