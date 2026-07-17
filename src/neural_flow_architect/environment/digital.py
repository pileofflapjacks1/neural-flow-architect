"""Digital interface orchestration (in-process state for MVP)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DigitalOrchestrator:
    """Tracks desired digital environment; OS hooks land in Phase 1."""

    density: str = "normal"
    notifications_suppressed: bool = False
    focus_enabled: bool = False
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

    def snapshot(self) -> dict[str, object]:
        return {
            "density": self.density,
            "notifications_suppressed": self.notifications_suppressed,
            "focus_enabled": self.focus_enabled,
        }
