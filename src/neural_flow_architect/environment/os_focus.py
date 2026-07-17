"""Best-effort OS Focus / Do Not Disturb hooks.

Never required for core function. Defaults to dry-run (record intent only).
Full Focus Mode on macOS often needs Shortcuts / TCC; we try safe local calls.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FocusBackendResult:
    ok: bool
    dry: bool
    backend: str
    action: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "dry": self.dry,
            "backend": self.backend,
            "action": self.action,
            "message": self.message,
        }


@dataclass
class OSFocusController:
    """
    enable_focus() when protecting flow; restore() when leaving.

    force_dry_run=True (default): never mutate OS settings — log only.
    """

    force_dry_run: bool = True
    enabled: bool = False  # master switch from settings
    history: list[str] = field(default_factory=list)
    active: bool = False

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "force_dry_run": self.force_dry_run,
            "active": self.active,
            "platform": platform.system().lower(),
            "mode": self._mode(),
            "history": self.history[-10:],
        }

    def _mode(self) -> str:
        if not self.enabled:
            return "disabled"
        if self.force_dry_run:
            return "dry_run"
        return "live_attempt"

    def enable_focus(self) -> FocusBackendResult:
        if not self.enabled:
            r = FocusBackendResult(True, True, "null", "enable", "OS Focus integration disabled")
            self.history.append("enable:disabled")
            return r
        if self.force_dry_run:
            self.active = True
            self.history.append("enable:dry_run")
            return FocusBackendResult(
                True,
                True,
                platform.system().lower(),
                "enable",
                "Dry-run: would request OS Focus / DND (no system change)",
            )
        system = platform.system().lower()
        if system == "darwin":
            return self._macos_enable()
        if system == "windows":
            return self._windows_enable()
        if system == "linux":
            return self._linux_enable()
        self.history.append("enable:unsupported")
        return FocusBackendResult(
            True, True, system, "enable", "Platform unsupported — companion policy only"
        )

    def restore(self) -> FocusBackendResult:
        if not self.enabled:
            return FocusBackendResult(
                True, True, "null", "restore", "OS Focus integration disabled"
            )
        if self.force_dry_run:
            self.active = False
            self.history.append("restore:dry_run")
            return FocusBackendResult(
                True,
                True,
                platform.system().lower(),
                "restore",
                "Dry-run: would restore OS Focus / DND",
            )
        system = platform.system().lower()
        if system == "darwin":
            return self._macos_restore()
        if system == "windows":
            return self._windows_restore()
        if system == "linux":
            return self._linux_restore()
        self.active = False
        return FocusBackendResult(True, True, system, "restore", "Platform unsupported")

    def _macos_enable(self) -> FocusBackendResult:
        # Best-effort: Shortcuts CLI if present (user must create "NFA Focus On")
        if shutil.which("shortcuts"):
            proc = subprocess.run(
                ["shortcuts", "run", "NFA Focus On"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            ok = proc.returncode == 0
            self.active = ok
            self.history.append(f"enable:shortcuts:{ok}")
            return FocusBackendResult(
                ok,
                False,
                "macos-shortcuts",
                "enable",
                "Ran Shortcuts 'NFA Focus On'"
                if ok
                else "Create a Shortcut named 'NFA Focus On' to enable live Focus",
            )
        self.active = True
        self.history.append("enable:notify_only")
        return FocusBackendResult(
            True,
            True,
            "macos",
            "enable",
            "No shortcuts CLI — dry companion note only. "
            "Install a Shortcut 'NFA Focus On' for live control.",
        )

    def _macos_restore(self) -> FocusBackendResult:
        if shutil.which("shortcuts"):
            proc = subprocess.run(
                ["shortcuts", "run", "NFA Focus Off"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            ok = proc.returncode == 0
            self.active = False
            self.history.append(f"restore:shortcuts:{ok}")
            return FocusBackendResult(
                ok,
                False,
                "macos-shortcuts",
                "restore",
                "Ran Shortcuts 'NFA Focus Off'"
                if ok
                else "Create Shortcut 'NFA Focus Off' for live restore",
            )
        self.active = False
        self.history.append("restore:notify_only")
        return FocusBackendResult(
            True, True, "macos", "restore", "No shortcuts CLI — companion restore only"
        )

    def _windows_enable(self) -> FocusBackendResult:
        # Focus Assist cannot be reliably toggled without elevated APIs; dry by default path
        self.active = True
        self.history.append("enable:windows_stub")
        return FocusBackendResult(
            True,
            True,
            "windows",
            "enable",
            "Windows Focus Assist: enable manually or set force_dry_run=false with future bridge",
        )

    def _windows_restore(self) -> FocusBackendResult:
        self.active = False
        self.history.append("restore:windows_stub")
        return FocusBackendResult(
            True, True, "windows", "restore", "Windows Focus Assist restore (stub)"
        )

    def _linux_enable(self) -> FocusBackendResult:
        if shutil.which("gsettings"):
            # GNOME notification quiet — best effort
            proc = subprocess.run(
                [
                    "gsettings",
                    "set",
                    "org.gnome.desktop.notifications",
                    "show-banners",
                    "false",
                ],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            ok = proc.returncode == 0
            self.active = ok
            self.history.append(f"enable:gsettings:{ok}")
            return FocusBackendResult(
                ok,
                False,
                "linux-gsettings",
                "enable",
                "GNOME banners suppressed" if ok else "gsettings failed",
            )
        self.active = True
        return FocusBackendResult(
            True, True, "linux", "enable", "No gsettings — dry companion only"
        )

    def _linux_restore(self) -> FocusBackendResult:
        if shutil.which("gsettings"):
            subprocess.run(
                [
                    "gsettings",
                    "set",
                    "org.gnome.desktop.notifications",
                    "show-banners",
                    "true",
                ],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
        self.active = False
        self.history.append("restore:linux")
        return FocusBackendResult(True, False, "linux", "restore", "Restored banners if GNOME")
