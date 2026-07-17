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
    """

    enabled: bool = False
    base_url: str = ""
    token: str = ""
    last_scene: str | None = None
    history: list[str] = field(default_factory=list)
    last_error: str | None = None

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
            return {"ok": True, "dry": True, "action": fallback, "message": "IoT disabled"}
        if not self.base_url or not self.token:
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
                resp = await client.post(
                    url, headers=headers, json={"entity_id": f"scene.{scene}"}
                )
            ok = resp.status_code < 300
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
            self.last_error = str(exc)
            self.history.append(f"ha_exception:{type(exc).__name__}")
            return {"ok": False, "dry": False, "action": scene, "error": self.last_error}
