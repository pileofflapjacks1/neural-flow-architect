"""Permission, cooldown, and rate-limit gate for agent actions."""

from __future__ import annotations

import time
from collections import deque

from neural_flow_architect.core.types import ActionProposal, ImpactLevel, WorldSnapshot


class Governor:
    def __init__(
        self,
        max_medium_per_10_min: int = 6,
        tool_cooldown_sec: float = 45.0,
    ) -> None:
        self.max_medium_per_10_min = max_medium_per_10_min
        self.tool_cooldown_sec = tool_cooldown_sec
        self._recent_medium: deque[float] = deque()
        self._last_tool_ts: dict[str, float] = {}
        self._active_tools: set[str] = set()

    def filter(
        self, proposals: list[ActionProposal], snapshot: WorldSnapshot
    ) -> list[ActionProposal]:
        now = time.time()
        self._purge(now)
        allowed: list[ActionProposal] = []
        prefs = snapshot.preferences

        for prop in proposals:
            if prop.tool_id in prefs.denied_tools:
                continue
            if prop.tool_id in self._active_tools and prop.tool_id not in {
                "notify.allow_all",
                "focus.disable",
                "ui.set_density",
            }:
                # Avoid re-firing sticky protect tools every tick
                if prop.tool_id in {"notify.suppress_noncritical", "focus.enable"}:
                    continue
            last = self._last_tool_ts.get(prop.tool_id)
            if last is not None and (now - last) < self.tool_cooldown_sec:
                continue
            if prop.impact in {ImpactLevel.MEDIUM, ImpactLevel.HIGH}:
                if len(self._recent_medium) >= self.max_medium_per_10_min:
                    continue
            if prop.impact == ImpactLevel.HIGH and prefs.require_confirm_high_impact:
                if prop.tool_id not in prefs.granted_tools:
                    continue
            if prop.tool_id.startswith("iot.") and not prefs.allow_iot:
                continue
            allowed.append(prop)
        return allowed

    def record(self, tool_id: str, impact: ImpactLevel) -> None:
        now = time.time()
        self._last_tool_ts[tool_id] = now
        self._active_tools.add(tool_id)
        if impact in {ImpactLevel.MEDIUM, ImpactLevel.HIGH}:
            self._recent_medium.append(now)
        # Opposite tools clear sticky state
        if tool_id in {"notify.allow_all", "focus.disable"}:
            self._active_tools.discard("notify.suppress_noncritical")
            self._active_tools.discard("focus.enable")

    def _purge(self, now: float) -> None:
        while self._recent_medium and now - self._recent_medium[0] > 600:
            self._recent_medium.popleft()
