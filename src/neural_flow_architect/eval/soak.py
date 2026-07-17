"""Long-session soak test — multi-hour simulation for memory/latency stability."""

from __future__ import annotations

import asyncio
import time
import tracemalloc
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from neural_flow_architect.adapters.replay import ReplayAdapter
from neural_flow_architect.agent.architect import Architect
from neural_flow_architect.core.failsafe import FailSafeGuard
from neural_flow_architect.core.types import (
    ContextSnapshot,
    UserPreferences,
    WorldSnapshot,
)
from neural_flow_architect.flow.engine import FlowEngine
from neural_flow_architect.signal.features import FeatureExtractor


@dataclass
class SoakReport:
    duration_sec: float
    target_duration_sec: float
    frames: int = 0
    ticks: int = 0
    actions: int = 0
    peak_rss_mb: float = 0.0
    current_rss_mb: float = 0.0
    mean_tick_ms: float = 0.0
    max_tick_ms: float = 0.0
    failsafe_trips: int = 0
    ok: bool = True
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "duration_sec": round(self.duration_sec, 2),
            "target_duration_sec": self.target_duration_sec,
            "frames": self.frames,
            "ticks": self.ticks,
            "actions": self.actions,
            "peak_rss_mb": round(self.peak_rss_mb, 2),
            "current_rss_mb": round(self.current_rss_mb, 2),
            "mean_tick_ms": round(self.mean_tick_ms, 3),
            "max_tick_ms": round(self.max_tick_ms, 3),
            "failsafe_trips": self.failsafe_trips,
            "ok": self.ok,
            "notes": self.notes,
        }


def _rss_mb() -> float:
    try:
        # ru_maxrss is KB on Linux, bytes on macOS — normalize roughly
        import platform
        import resource

        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if platform.system() == "Darwin":
            return rss / (1024 * 1024)
        return rss / 1024.0
    except Exception:
        return 0.0


async def run_soak(
    *,
    duration_sec: float = 120.0,
    sample_rate_hz: float = 128.0,
    channels: int = 8,
    memory_limit_mb: float = 512.0,
) -> SoakReport:
    """
    Fast-forward soak using non-realtime replay.

    ``duration_sec`` is simulated stream time, not wall clock.
    """
    tracemalloc.start()
    adapter = ReplayAdapter(
        n_channels=channels,
        sample_rate_hz=sample_rate_hz,
        chunk_samples=32,
        loop=True,
        realtime=False,
    )
    features = FeatureExtractor(sample_rate_hz=sample_rate_hz, window_sec=0.5, hop_sec=0.25)
    flow = FlowEngine()
    architect = Architect(dry_run=True)
    guard = FailSafeGuard(low_quality_streak=100)  # don't trip on synthetic noise lightly
    report = SoakReport(duration_sec=0.0, target_duration_sec=duration_sec)
    tick_ms: list[float] = []
    sim_t = 0.0
    dt = 32 / sample_rate_hz
    wall0 = time.perf_counter()

    await adapter.connect()
    try:
        async for frame in adapter.stream():
            if sim_t >= duration_sec:
                break
            sim_t += dt
            report.frames += 1
            guard.note_frame(frame.quality.overall, dropout=frame.quality.dropout)
            if guard.state.active:
                report.failsafe_trips += 1
            t0 = time.perf_counter()
            for window in features.push(frame):
                est = flow.update(window)
                snap = WorldSnapshot(
                    time=datetime.utcnow(),
                    flow=est,
                    quality=window.quality,
                    context=ContextSnapshot(recipe="study"),
                    preferences=UserPreferences(),
                )
                decision = await architect.step(snap)
                report.ticks += 1
                report.actions += sum(1 for r in decision.results if r.success)
            t1 = time.perf_counter()
            tick_ms.append((t1 - t0) * 1000.0)
            report.current_rss_mb = _rss_mb()
            report.peak_rss_mb = max(report.peak_rss_mb, report.current_rss_mb)
            if report.peak_rss_mb > memory_limit_mb > 0:
                report.ok = False
                report.notes.append(
                    f"Memory peak {report.peak_rss_mb:.1f} MB exceeded limit {memory_limit_mb}"
                )
                break
    finally:
        await adapter.disconnect()
        tracemalloc.stop()

    report.duration_sec = sim_t
    if tick_ms:
        report.mean_tick_ms = sum(tick_ms) / len(tick_ms)
        report.max_tick_ms = max(tick_ms)
    wall = time.perf_counter() - wall0
    report.notes.append(f"Wall clock {wall:.2f}s for {sim_t:.1f}s simulated stream")
    if report.ticks < 1:
        report.ok = False
        report.notes.append("No flow ticks produced")
    return report


def run_soak_sync(**kwargs: Any) -> SoakReport:
    return asyncio.run(run_soak(**kwargs))
