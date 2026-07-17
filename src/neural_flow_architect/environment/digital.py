"""Digital interface orchestration (in-process state for MVP)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DigitalOrchestrator:
    """Tracks desired digital environment; OS hooks can attach later."""

    density: str = "normal"
    notifications_suppressed: bool = False
    focus_enabled: bool = False
    rest_mode: bool = False
    history: list[str] = field(default_factory=list)

    def set_density(self, density: str) -> None:
        self.density = density
        self.history.append(f"density={density}")

    def suppress_noncritical(self, enabled: bool) -> None:
        self.notifications_suppressed = enabled
        self.history.append(f"suppress_notifications={enabled}")

    def set_focus(self, enabled: bool) -> None:
        self.focus_enabled = enabled
        self.history.append(f"focus={enabled}")

    def set_rest_mode(self, enabled: bool) -> None:
        self.rest_mode = enabled
        if enabled:
            self.focus_enabled = False
            self.notifications_suppressed = False
            self.density = "normal"
        self.history.append(f"rest_mode={enabled}")

    def snapshot(self) -> dict[str, Any]:
        return {
            "density": self.density,
            "notifications_suppressed": self.notifications_suppressed,
            "focus_enabled": self.focus_enabled,
            "rest_mode": self.rest_mode,
        }

    def restore(self, snap: dict[str, Any]) -> None:
        self.density = str(snap.get("density", "normal"))
        self.notifications_suppressed = bool(snap.get("notifications_suppressed", False))
        self.focus_enabled = bool(snap.get("focus_enabled", False))
        self.rest_mode = bool(snap.get("rest_mode", False))
        self.history.append("restore_snapshot")
