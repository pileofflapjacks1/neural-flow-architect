"""App category map, OS Focus dry-run, scoreboard, timeline."""

from __future__ import annotations

from pathlib import Path

from neural_flow_architect.core.active_app import categorize_app
from neural_flow_architect.core.app_map import VALID_CATEGORIES, AppCategoryMap
from neural_flow_architect.core.types import FlowEstimate, FlowState
from neural_flow_architect.environment.os_focus import OSFocusController
from neural_flow_architect.insights.scoreboard import build_policy_scoreboard
from neural_flow_architect.insights.store import InsightsStore


def test_app_map_load_save_and_match(tmp_path: Path) -> None:
    path = tmp_path / "app_categories.json"
    m = AppCategoryMap.load(path)
    assert path.exists()
    assert m.categorize("Google Chrome") == "study"
    m.set_entry("specialapp", "create")
    m.save(path)
    m2 = AppCategoryMap.load(path)
    assert m2.categorize("My SpecialApp Window") == "create"
    m2.remove_entry("specialapp")
    assert m2.categorize("specialapp") == "unknown"
    assert "study" in VALID_CATEGORIES


def test_categorize_prefers_user_map() -> None:
    um = AppCategoryMap({"weirdtool": "social"})
    assert categorize_app("WeirdTool Pro", user_map=um) == "social"
    assert categorize_app("TotallyUnknown", user_map=um) == "unknown"


def test_os_focus_dry_run_default() -> None:
    ctrl = OSFocusController(enabled=True, force_dry_run=True)
    r = ctrl.enable_focus()
    assert r.ok and r.dry
    assert ctrl.active is True
    st = ctrl.status()
    assert st["mode"] == "dry_run"
    r2 = ctrl.restore()
    assert r2.ok and r2.dry
    assert ctrl.active is False


def test_os_focus_disabled() -> None:
    ctrl = OSFocusController(enabled=False, force_dry_run=False)
    r = ctrl.enable_focus()
    assert r.backend == "null"
    assert ctrl.active is False


def test_scoreboard_empty() -> None:
    sb = build_policy_scoreboard([])
    assert sb["sessions"] == 0
    assert sb["score"] is None


def test_scoreboard_with_sessions() -> None:
    sessions = [
        {
            "actions_count": 10,
            "undos_count": 1,
            "recipe": "study",
            "flow_minutes": 12.0,
            "block_review": {"helpful_block": True, "architect_helpful": True},
        },
        {
            "actions_count": 5,
            "undos_count": 0,
            "recipe": "create",
            "flow_minutes": 8.0,
            "block_review": {"helpful_block": True, "architect_helpful": True},
        },
    ]
    sb = build_policy_scoreboard(sessions, feedback_history=[])
    assert sb["sessions"] == 2
    assert sb["score"] is not None
    assert 0 <= sb["score"] <= 100
    assert "study" in sb["by_recipe"]
    assert sb["totals"]["helpful_blocks"] == 2


def test_timeline_records_state_action_undo(tmp_path: Path) -> None:
    store = InsightsStore(tmp_path)
    store.start_session(adapter="simulator")
    est = FlowEstimate(
        timestamp_ns=1,
        engagement=0.7,
        arousal_balance=0.5,
        self_ref_proxy=0.2,
        effort_ease=0.5,
        confidence=0.8,
        state=FlowState.FLOW,
        minutes_in_state=0.5,
    )
    store.observe_flow(est)
    store.observe_action("protected focus", tool_id="focus.enable")
    store.observe_undo()
    snap = store.snapshot_current()
    assert snap is not None
    kinds = [e["kind"] for e in snap["timeline"]]
    assert "state" in kinds
    assert "action" in kinds
    assert "undo" in kinds
    action = next(e for e in snap["timeline"] if e["kind"] == "action")
    assert action["detail"]["tool_id"] == "focus.enable"
    summary = store.end_session(persist=True)
    assert summary is not None
    listed = store.list_sessions()
    assert listed[0]["timeline"]
