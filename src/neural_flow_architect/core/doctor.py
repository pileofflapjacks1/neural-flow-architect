"""Environment health checks for easy setup diagnosis."""

from __future__ import annotations

import asyncio
import importlib
import platform
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from neural_flow_architect import __version__
from neural_flow_architect.core.settings import get_settings


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "ok": self.ok, "detail": self.detail}


@dataclass
class DoctorReport:
    version: str = __version__
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(c.ok for c in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "ok": self.ok,
            "checks": [c.to_dict() for c in self.checks],
        }


def run_doctor(*, brainflow: bool = False) -> DoctorReport:
    """
    Run install / privacy checks.

    When ``brainflow=True``, also validate the open-EEG path:
    fixture file, optional BrainFlow package, file-mode stream → features → flow,
    and a simple feature-stage latency smoke test.
    """
    report = DoctorReport()
    py = sys.version_info
    report.checks.append(
        CheckResult(
            "python",
            py >= (3, 11),
            f"{platform.python_version()} (need 3.11+)",
        )
    )

    for mod in ("numpy", "pydantic", "fastapi", "uvicorn", "typer", "httpx"):
        try:
            importlib.import_module(mod)
            report.checks.append(CheckResult(f"dep:{mod}", True, "installed"))
        except ImportError:
            report.checks.append(CheckResult(f"dep:{mod}", False, "missing — pip install -e ."))

    settings = get_settings()
    try:
        settings.ensure_data_dirs()
        probe = settings.data_dir / ".nfa_write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        report.checks.append(
            CheckResult("data_dir", True, f"writable: {settings.data_dir.resolve()}")
        )
    except OSError as exc:
        report.checks.append(CheckResult("data_dir", False, str(exc)))

    # Adapter factory
    try:
        from neural_flow_architect.adapters.registry import build_adapter

        settings.adapter = "simulator"
        adapter = build_adapter(settings)
        report.checks.append(CheckResult("adapter_simulator", True, f"built {adapter.name}"))
    except Exception as exc:  # noqa: BLE001
        report.checks.append(CheckResult("adapter_simulator", False, str(exc)))

    frontend = Path(__file__).resolve().parents[3] / "frontend" / "package.json"
    report.checks.append(
        CheckResult(
            "frontend_scaffold",
            frontend.exists(),
            str(frontend) if frontend.exists() else "frontend/package.json missing",
        )
    )

    report.checks.append(
        CheckResult(
            "local_only_default",
            bool(settings.local_only),
            f"local_only={settings.local_only}",
        )
    )
    report.checks.append(
        CheckResult(
            "privacy_cloud_llm_off",
            not settings.allow_cloud_llm,
            f"allow_cloud_llm={settings.allow_cloud_llm}",
        )
    )

    if brainflow:
        report.checks.extend(_brainflow_checks())

    return report


def _brainflow_checks() -> list[CheckResult]:
    """Open-EEG / BrainFlow path validation (file mode works without the package)."""
    checks: list[CheckResult] = []

    # Optional native package
    try:
        importlib.import_module("brainflow")
        checks.append(
            CheckResult(
                "brainflow_package",
                True,
                "installed (live boards + synthetic board available)",
            )
        )
        package_ok = True
    except ImportError:
        checks.append(
            CheckResult(
                "brainflow_package",
                True,  # not required for file mode
                "not installed — file mode still works; "
                "pip install -e '.[brainflow]' for live boards",
            )
        )
        package_ok = False

    from neural_flow_architect.adapters.registry import (
        default_brainflow_fixture,
        resolve_brainflow_file,
    )

    fixture = default_brainflow_fixture()
    checks.append(
        CheckResult(
            "brainflow_fixture",
            fixture.is_file(),
            str(fixture) if fixture.is_file() else f"missing fixture at {fixture}",
        )
    )
    if not fixture.is_file():
        return checks

    resolved = resolve_brainflow_file(str(fixture))
    checks.append(
        CheckResult(
            "brainflow_file_resolve",
            Path(resolved).is_file(),
            f"resolved → {resolved}",
        )
    )

    # File-mode stream contract (no package required)
    try:
        from neural_flow_architect.adapters.brainflow_adapter import BrainFlowAdapter
        from neural_flow_architect.adapters.contract import run_adapter_contract

        ad = BrainFlowAdapter(
            file_path=resolved,
            chunk_samples=32,
            sample_rate_hz=250.0,
            realtime=False,
        )
        report = asyncio.run(run_adapter_contract(ad, max_frames=3, timeout_sec=15.0))
        checks.append(
            CheckResult(
                "brainflow_file_contract",
                bool(report.get("ok")),
                f"frames={report.get('frames')} channels={report.get('n_channels')} "
                f"caps={sorted(report.get('capabilities') or [])}",
            )
        )
    except Exception as exc:  # noqa: BLE001
        checks.append(CheckResult("brainflow_file_contract", False, str(exc)))
        return checks

    # Features → flow latency smoke (guidance budget: feature+flow ≤ 70ms avg)
    try:
        latency = asyncio.run(_file_pipeline_latency_ms(resolved))
        # Soft budget for open-EEG file path (see LATENCY_BUDGET.md)
        ok = latency["p95_feature_flow_ms"] <= 80.0
        checks.append(
            CheckResult(
                "brainflow_latency_smoke",
                ok,
                (
                    f"mean={latency['mean_feature_flow_ms']:.2f}ms "
                    f"p95={latency['p95_feature_flow_ms']:.2f}ms "
                    f"windows={latency['windows']} "
                    f"(budget p95≤80ms feature→flow)"
                ),
            )
        )
    except Exception as exc:  # noqa: BLE001
        checks.append(CheckResult("brainflow_latency_smoke", False, str(exc)))

    # Short closed-loop runtime on file adapter
    try:
        from neural_flow_architect.core.runtime import NeuralFlowRuntime
        from neural_flow_architect.core.settings import Settings

        settings = Settings(
            adapter="brainflow",
            brainflow_file=resolved,
            channels=4,
            sample_rate_hz=250.0,
            window_sec=0.25,
            hop_sec=0.125,
            dry_run=True,
        )
        # Avoid real-time sleep in adapter for doctor speed
        runtime = NeuralFlowRuntime(settings)
        # Monkey-patch adapter realtime if file mode
        adapter_any: Any = runtime.adapter
        if hasattr(adapter_any, "realtime"):
            adapter_any.realtime = False
        ticks = asyncio.run(runtime.run(duration_sec=0.8))
        checks.append(
            CheckResult(
                "brainflow_runtime_loop",
                len(ticks) >= 1,
                f"ticks={len(ticks)} last_state={ticks[-1].flow.state.value if ticks else '—'}",
            )
        )
    except Exception as exc:  # noqa: BLE001
        checks.append(CheckResult("brainflow_runtime_loop", False, str(exc)))

    # Live synthetic board (only if package present)
    if package_ok:
        try:
            from neural_flow_architect.adapters.brainflow_adapter import BrainFlowAdapter
            from neural_flow_architect.adapters.contract import run_adapter_contract

            live = BrainFlowAdapter(board_id=-1, chunk_samples=32, realtime=True)
            live_report = asyncio.run(run_adapter_contract(live, max_frames=2, timeout_sec=20.0))
            checks.append(
                CheckResult(
                    "brainflow_synthetic_board",
                    bool(live_report.get("ok")),
                    f"board_id=-1 frames={live_report.get('frames')}",
                )
            )
        except Exception as exc:  # noqa: BLE001
            checks.append(
                CheckResult(
                    "brainflow_synthetic_board",
                    False,
                    f"synthetic board failed: {exc}",
                )
            )
    else:
        checks.append(
            CheckResult(
                "brainflow_synthetic_board",
                True,
                "skipped (brainflow package not installed)",
            )
        )

    # Common board ID reference (informational always-ok)
    checks.append(
        CheckResult(
            "brainflow_board_ids",
            True,
            "common: -1 synthetic · 0 Cyton · 1 Ganglion (Bluetooth) · "
            "2 Ganglion (native) · see BrainFlow docs for full list",
        )
    )
    return checks


async def _file_pipeline_latency_ms(file_path: str) -> dict[str, float]:
    """Measure feature extract + flow update latency on file frames."""
    from neural_flow_architect.adapters.brainflow_adapter import BrainFlowAdapter
    from neural_flow_architect.flow.engine import FlowEngine
    from neural_flow_architect.signal.features import FeatureExtractor

    adapter = BrainFlowAdapter(
        file_path=file_path,
        chunk_samples=64,
        sample_rate_hz=250.0,
        realtime=False,
    )
    meta = await adapter.connect()
    extractor = FeatureExtractor(
        sample_rate_hz=meta.sampling_rate_hz,
        window_sec=0.5,
        hop_sec=0.25,
    )
    engine = FlowEngine()
    times: list[float] = []
    windows = 0
    async for frame in adapter.stream():
        t0 = time.perf_counter()
        feats = extractor.push(frame)
        for fw in feats:
            engine.update(fw)
            windows += 1
        times.append((time.perf_counter() - t0) * 1000.0)
        if windows >= 12:
            break
    await adapter.disconnect()
    if not times:
        raise RuntimeError("No feature windows produced from fixture")
    times_sorted = sorted(times)
    p95 = times_sorted[int(0.95 * (len(times_sorted) - 1))]
    return {
        "mean_feature_flow_ms": sum(times) / len(times),
        "p95_feature_flow_ms": p95,
        "windows": float(windows),
    }
