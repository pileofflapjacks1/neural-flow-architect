"""IoT dry-run safety pack tests."""

import pytest

from neural_flow_architect.environment.physical import PhysicalOrchestrator


@pytest.mark.asyncio
async def test_force_dry_run_never_errors_without_url() -> None:
    orch = PhysicalOrchestrator(enabled=True, force_dry_run=True, base_url="", token="")
    result = await orch.dim_for_focus()
    assert result["ok"] is True
    assert result["dry"] is True
    assert orch.dry_calls == 1
    assert orch.live_calls == 0
    assert orch.mode_label == "dry_run"


@pytest.mark.asyncio
async def test_disabled_iot() -> None:
    orch = PhysicalOrchestrator(enabled=False)
    result = await orch.restore_lights()
    assert result["dry"] is True
