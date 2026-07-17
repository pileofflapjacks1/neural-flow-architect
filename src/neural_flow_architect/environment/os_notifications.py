"""OS-level notification policy hooks — best-effort, platform-specific, never required."""

from __future__ import annotations

import platform
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Protocol


class NotificationBackend(Protocol):
    name: str

    def suppress_noncritical(self) -> dict[str, object]: ...

    def restore(self) -> dict[str, object]: ...


@dataclass
class NullNotificationBackend:
    """Default: no OS calls; companion-level policy only."""

    name: str = "null"
    suppressed: bool = False
    history: list[str] = field(default_factory=list)

    def suppress_noncritical(self) -> dict[str, object]:
        self.suppressed = True
        self.history.append("suppress")
        return {"ok": True, "backend": self.name, "simulated": True}

    def restore(self) -> dict[str, object]:
        self.suppressed = False
        self.history.append("restore")
        return {"ok": True, "backend": self.name, "simulated": True}


@dataclass
class MacOSNotificationBackend:
    """
    Best-effort macOS Focus-adjacent hints via shell.

    Full Focus Mode control requires user TCC permissions / Shortcuts;
    this backend records intent and optionally posts a user-visible notice.
    """

    name: str = "macos"
    suppressed: bool = False
    announce: bool = False
    history: list[str] = field(default_factory=list)

    def suppress_noncritical(self) -> dict[str, object]:
        self.suppressed = True
        self.history.append("suppress")
        if self.announce:
            _osascript_notify(
                "Neural Flow Architect",
                "Protecting focus — non-critical notifications should stay quiet.",
            )
        return {
            "ok": True,
            "backend": self.name,
            "simulated": False,
            "note": "macOS Focus Mode must be user-controlled; companion policy active",
        }

    def restore(self) -> dict[str, object]:
        self.suppressed = False
        self.history.append("restore")
        if self.announce:
            _osascript_notify(
                "Neural Flow Architect",
                "Focus protection eased — notifications restored in companion policy.",
            )
        return {"ok": True, "backend": self.name, "simulated": False}


@dataclass
class LinuxNotificationBackend:
    name: str = "linux"
    suppressed: bool = False
    history: list[str] = field(default_factory=list)

    def suppress_noncritical(self) -> dict[str, object]:
        self.suppressed = True
        self.history.append("suppress")
        if shutil.which("notify-send"):
            subprocess.run(
                [
                    "notify-send",
                    "--urgency=low",
                    "Neural Flow Architect",
                    "Focus protection active (companion policy).",
                ],
                check=False,
                capture_output=True,
            )
            return {"ok": True, "backend": self.name, "simulated": False}
        return {
            "ok": True,
            "backend": self.name,
            "simulated": True,
            "note": "notify-send not found",
        }

    def restore(self) -> dict[str, object]:
        self.suppressed = False
        self.history.append("restore")
        return {"ok": True, "backend": self.name, "simulated": True}


def _osascript_notify(title: str, message: str) -> None:
    script = f'display notification "{message}" with title "{title}"'
    try:
        subprocess.run(
            ["osascript", "-e", script],
            check=False,
            capture_output=True,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        pass


def build_notification_backend(
    *,
    enabled: bool = False,
    announce: bool = False,
) -> NotificationBackend:
    if not enabled:
        return NullNotificationBackend()
    system = platform.system().lower()
    if system == "darwin":
        return MacOSNotificationBackend(announce=announce)
    if system == "linux":
        return LinuxNotificationBackend()
    return NullNotificationBackend(name=f"null-{system}")
