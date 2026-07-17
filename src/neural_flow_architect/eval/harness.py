"""Offline evaluation harness — trajectory → flow → policy scores (no hardware)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from neural_flow_architect.adapters.replay import ReplayAdapter
from neural_flow_architect.agent.architect import Architect
from neural_flow_architect.core.types import (
    ContextSnapshot,
    UserPreferences,
    WorldSnapshot,
)
from neural_flow_architect.flow.engine import FlowEngine
from neural_flow_architect.signal.features import FeatureExtractor


@dataclass
class EvalReport:
    ticks: int = 0
    state_counts: dict[str, int] = field(default_factory=dict)
    actions: dict[str, int] = field(default_factory=dict)
    modes: dict[str, int] = field(default_factory=dict)
    mean_engagement: float = 0.0
    mean_confidence: float = 0.0
    protect_ticks: int = 0
    degraded_ticks: int = 0
    duration_sec: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticks": self.ticks,
            "state_counts": self.state_counts,
            "actions": self.actions,
            "modes": self.modes,
            "mean_engagement": round(self.mean_engagement, 4),
            "mean_confidence": round(self.mean_confidence, 4),
            "protect_ticks": self.protect_ticks,
            "degraded_ticks": self.degraded_ticks,
            "duration_sec": self.duration_sec,
            "action_rate": round(sum(self.actions.values()) / max(self.ticks, 1), 4),
        }


async def run_offline_eval(
    *,
    trajectory_path: Path | str | None = None,
    duration_sec: float = 30.0,
    sample_rate_hz: float = 128.0,
    channels: int = 4,
    recipe: str = "study",
    dry_run: bool = True,
) -> EvalReport:
    """
    Fast offline loop using ReplayAdapter (realtime=False).

    Scores policy behavior without needing a live server.
    """
    adapter = ReplayAdapter(
        trajectory_path=trajectory_path,
        n_channels=channels,
        sample_rate_hz=sample_rate_hz,
        chunk_samples=32,
        loop=True,
        realtime=False,
    )
    features = FeatureExtractor(
        sample_rate_hz=sample_rate_hz,
        window_sec=0.5,
        hop_sec=0.25,
    )
    flow = FlowEngine()
    architect = Architect(dry_run=dry_run)
    report = EvalReport(duration_sec=duration_sec)

    await adapter.connect()
    eng_sum = 0.0
    conf_sum = 0.0
    sim_t = 0.0
    dt = 32 / sample_rate_hz
    try:
        async for frame in adapter.stream():
            if sim_t >= duration_sec:
                break
            sim_t += dt
            for window in features.push(frame):
                est = flow.update(window)
                report.ticks += 1
                report.state_counts[est.state.value] = (
                    report.state_counts.get(est.state.value, 0) + 1
                )
                eng_sum += est.engagement
                conf_sum += est.confidence
                if est.confidence < 0.45:
                    report.degraded_ticks += 1
                snap = WorldSnapshot(
                    time=datetime.utcnow(),
                    flow=est,
                    quality=window.quality,
                    context=ContextSnapshot(recipe=recipe, user_goal="eval"),
                    preferences=UserPreferences(),
                )
                decision = await architect.step(snap)
                report.modes[decision.mode.value] = report.modes.get(decision.mode.value, 0) + 1
                if decision.mode.value == "protect":
                    report.protect_ticks += 1
                for res in decision.results:
                    if res.success:
                        report.actions[res.tool_id] = report.actions.get(res.tool_id, 0) + 1
    finally:
        await adapter.disconnect()

    if report.ticks:
        report.mean_engagement = eng_sum / report.ticks
        report.mean_confidence = conf_sum / report.ticks
    return report


def run_offline_eval_sync(**kwargs: Any) -> EvalReport:
    return asyncio.run(run_offline_eval(**kwargs))
