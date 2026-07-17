"""Physical / IoT orchestration stubs."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PhysicalOrchestrator:
    """Home Assistant (etc.) integration point — disabled by default."""

    enabled: bool = False
    last_scene: str | None = None
    history: list[str] = field(default_factory=list)

    async def dim_for_focus(self) -> None:
        self.last_scene = "focus_dim"
        self.history.append("dim_for_focus")
        # Phase 2: call Home Assistant scene service when configured

    async def restore_lights(self) -> None:
        self.last_scene = "restored"
        self.history.append("restore_lights")
