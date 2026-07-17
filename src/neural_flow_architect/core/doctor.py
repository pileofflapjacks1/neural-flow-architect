"""Environment health checks for easy setup diagnosis."""

from __future__ import annotations

import importlib
import platform
import sys
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


def run_doctor() -> DoctorReport:
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
    return report
