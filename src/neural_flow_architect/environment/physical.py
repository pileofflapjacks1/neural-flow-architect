"""Physical / IoT orchestration — Home Assistant optional, dry-run safe."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PhysicalOrchestrator:
    """
    Smart-home integration point.

    Disabled by default. When enabled with a Home Assistant URL/token,
    attempts REST calls; failures are soft and logged in history.

    ``force_dry_run=True`` (recommended default for safety packs) never hits
    the network even if enabled+configured — use for rehearsal.
    """

    enabled: bool = False
    force_dry_run: bool = True  # safety default: simulate until explicitly live
    base_url: str = ""
    token: str = ""
    last_scene: str | None = None
    history: list[str] = field(default_factory=list)
    last_error: str | None = None
    live_calls: int = 0
    dry_calls: int = 0

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "force_dry_run": self.force_dry_run,
            "configured": bool(self.base_url and self.token),
            "mode": self.mode_label,
            "live_calls": self.live_calls,
            "dry_calls": self.dry_calls,
            "last_scene": self.last_scene,
            "last_error": self.last_error,
        }

    @property
    def mode_label(self) -> str:
        if not self.enabled:
            return "disabled"
        if self.force_dry_run or not (self.base_url and self.token):
            return "dry_run"
        return "live"

    async def dim_for_focus(self) -> dict[str, Any]:
        self.last_scene = "focus_dim"
        self.history.append("dim_for_focus")
        return await self._call_scene("nfa_focus_dim", fallback="dim_for_focus")

    async def restore_lights(self) -> dict[str, Any]:
        self.last_scene = "restored"
        self.history.append("restore_lights")
        return await self._call_scene("nfa_restore", fallback="restore_lights")

    async def _call_scene(self, scene: str, *, fallback: str) -> dict[str, Any]:
        if not self.enabled:
            self.dry_calls += 1
            return {"ok": True, "dry": True, "action": fallback, "message": "IoT disabled"}
        if self.force_dry_run:
            self.dry_calls += 1
            return {
                "ok": True,
                "dry": True,
                "action": fallback,
                "message": "IoT dry-run (force_dry_run=true) — no network call",
            }
        if not self.base_url or not self.token:
            self.dry_calls += 1
            return {
                "ok": True,
                "dry": True,
                "action": fallback,
                "message": "IoT enabled but HA URL/token not configured — simulated",
            }
        try:
            import httpx

            url = self.base_url.rstrip("/") + "/api/services/scene/turn_on"
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            }
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(url, headers=headers, json={"entity_id": f"scene.{scene}"})
            ok = resp.status_code < 300
            self.live_calls += 1
            if not ok:
                self.last_error = f"HA {resp.status_code}: {resp.text[:200]}"
                self.history.append(f"ha_error:{scene}")
            else:
                self.history.append(f"ha_ok:{scene}")
                self.last_error = None
            return {
                "ok": ok,
                "dry": False,
                "action": scene,
                "status_code": resp.status_code,
                "error": self.last_error,
            }
        except Exception as exc:  # noqa: BLE001
            self.live_calls += 1
            self.last_error = str(exc)
            self.history.append(f"ha_exception:{type(exc).__name__}")
            return {"ok": False, "dry": False, "action": scene, "error": self.last_error}
