"""Latency budgets and high-channel stress measurements."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np

from neural_flow_architect.agent.architect import Architect
from neural_flow_architect.core.types import (
    ContextSnapshot,
    FeatureWindow,
    NeuralFrame,
    QualityFlags,
    UserPreferences,
    WorldSnapshot,
)
from neural_flow_architect.flow.engine import FlowEngine
from neural_flow_architect.signal.features import FeatureExtractor


# Documented prototype budgets (ms) — see docs/architecture/LATENCY_BUDGET.md
BUDGETS_MS = {
    "feature_extract": 50.0,
    "flow_update": 20.0,
    "agent_rules": 10.0,
    "end_to_end_window": 80.0,
}


@dataclass
class LatencyReport:
    n_channels: int
    window_samples: int
    iterations: int
    feature_ms: list[float] = field(default_factory=list)
    flow_ms: list[float] = field(default_factory=list)
    agent_ms: list[float] = field(default_factory=list)
    e2e_ms: list[float] = field(default_factory=list)
    budgets_ms: dict[str, float] = field(default_factory=lambda: dict(BUDGETS_MS))

    def _stats(self, vals: list[float]) -> dict[str, float]:
        if not vals:
            return {"mean": 0.0, "p50": 0.0, "p95": 0.0, "max": 0.0}
        arr = np.array(vals)
        return {
            "mean": float(np.mean(arr)),
            "p50": float(np.percentile(arr, 50)),
            "p95": float(np.percentile(arr, 95)),
            "max": float(np.max(arr)),
        }

    def to_dict(self) -> dict[str, Any]:
        stages = {
            "feature_extract": self._stats(self.feature_ms),
            "flow_update": self._stats(self.flow_ms),
            "agent_rules": self._stats(self.agent_ms),
            "end_to_end_window": self._stats(self.e2e_ms),
        }
        pass_fail = {
            name: stages[name]["p95"] <= budget
            for name, budget in self.budgets_ms.items()
            if name in stages
        }
        return {
            "n_channels": self.n_channels,
            "window_samples": self.window_samples,
            "iterations": self.iterations,
            "stages_ms": stages,
            "budgets_ms": self.budgets_ms,
            "pass": pass_fail,
            "all_pass": all(pass_fail.values()) if pass_fail else False,
        }


async def run_latency_bench(
    *,
    n_channels: int = 8,
    sample_rate_hz: float = 250.0,
    window_sec: float = 1.0,
    iterations: int = 40,
    seed: int = 0,
) -> LatencyReport:
    rng = np.random.default_rng(seed)
    window_samples = max(int(window_sec * sample_rate_hz), 8)
    fx = FeatureExtractor(
        sample_rate_hz=sample_rate_hz,
        window_sec=window_sec,
        hop_sec=window_sec,
    )
    flow = FlowEngine()
    architect = Architect(dry_run=True)
    report = LatencyReport(
        n_channels=n_channels,
        window_samples=window_samples,
        iterations=iterations,
    )

    # Warm buffers to emit windows immediately
    chunk = window_samples
    for i in range(iterations):
        data = rng.normal(0, 1.0, size=(n_channels, chunk)).astype(np.float64)
        frame = NeuralFrame(
            seq=i,
            timestamp_ns=time.time_ns(),
            data=data,
            quality=QualityFlags(overall=1.0),
        )
        t0 = time.perf_counter()
        windows = fx.push(frame)
        t1 = time.perf_counter()
        report.feature_ms.append((t1 - t0) * 1000.0)
        if not windows:
            continue
        window: FeatureWindow = windows[0]
        t2 = time.perf_counter()
        est = flow.update(window)
        t3 = time.perf_counter()
        report.flow_ms.append((t3 - t2) * 1000.0)
        snap = WorldSnapshot(
            time=datetime.utcnow(),
            flow=est,
            quality=window.quality,
            context=ContextSnapshot(recipe="study"),
            preferences=UserPreferences(),
        )
        t4 = time.perf_counter()
        await architect.step(snap)
        t5 = time.perf_counter()
        report.agent_ms.append((t5 - t4) * 1000.0)
        report.e2e_ms.append((t5 - t0) * 1000.0)

    return report
