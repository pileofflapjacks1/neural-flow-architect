"""Permission, cooldown, and rate-limit gate for agent actions."""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable

from neural_flow_architect.core.types import ActionProposal, ImpactLevel, WorldSnapshot


class Governor:
    def __init__(
        self,
        max_medium_per_10_min: int = 6,
        tool_cooldown_sec: float = 45.0,
        *,
        score_bonus_fn: Callable[[str], float] | None = None,
        failsafe_allow_fn: Callable[[str, str], bool] | None = None,
    ) -> None:
        self.max_medium_per_10_min = max_medium_per_10_min
        self.tool_cooldown_sec = tool_cooldown_sec
        self._recent_medium: deque[float] = deque()
        self._last_tool_ts: dict[str, float] = {}
        self._active_tools: set[str] = set()
        self._extra_cooldown: dict[str, float] = {}  # tool_id -> extra seconds
        self.score_bonus_fn = score_bonus_fn
        self.failsafe_allow_fn = failsafe_allow_fn

    def filter(
        self, proposals: list[ActionProposal], snapshot: WorldSnapshot
    ) -> list[ActionProposal]:
        now = time.time()
        self._purge(now)
        allowed: list[ActionProposal] = []
        prefs = snapshot.preferences

        # Apply preference affinity to proposal scores
        ranked = list(proposals)
        if self.score_bonus_fn is not None:
            for prop in ranked:
                prop.score = prop.score + self.score_bonus_fn(prop.tool_id)
            ranked = sorted(ranked, key=lambda p: p.score, reverse=True)

        for prop in ranked:
            if prop.tool_id in prefs.denied_tools:
                continue
            if self.failsafe_allow_fn is not None:
                if not self.failsafe_allow_fn(prop.tool_id, prop.impact.value):
                    continue
            if prop.tool_id in self._active_tools and prop.tool_id not in {
                "notify.allow_all",
                "focus.disable",
                "ui.set_density",
            }:
                # Avoid re-firing sticky protect tools every tick
                if prop.tool_id in {
                    "notify.suppress_noncritical",
                    "focus.enable",
                    "recipe.apply",
                    "iot.lights.dim_for_focus",
                    "prepare.context",
                    "tasks.queue_next",
                }:
                    continue

            last = self._last_tool_ts.get(prop.tool_id)
            cooldown = self.tool_cooldown_sec + self._extra_cooldown.get(prop.tool_id, 0.0)
            if last is not None and (now - last) < cooldown:
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

    def penalize_cooldown(self, tool_id: str, extra_sec: float = 90.0) -> None:
        self._extra_cooldown[tool_id] = max(self._extra_cooldown.get(tool_id, 0.0), extra_sec)

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
