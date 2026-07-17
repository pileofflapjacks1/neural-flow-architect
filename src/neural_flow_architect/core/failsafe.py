"""Fail-safe override — safety always wins over proactivity.

When signal stalls, quality collapses, or the agent errors, the system must:
  1. Stop medium/high impact and IoT actions
  2. Keep Pause / Undo / intent control responsive
  3. Surface a clear degraded state to the UI
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FailSafeReason(str, Enum):
    NONE = "none"
    USER_PAUSE = "user_pause"
    STREAM_STALL = "stream_stall"
    LOW_QUALITY = "low_quality"
    AGENT_ERROR = "agent_error"
    MANUAL = "manual"


@dataclass
class FailSafeState:
    active: bool = False
    reason: FailSafeReason = FailSafeReason.NONE
    message: str = ""
    since_mono: float | None = None
    consecutive_low_quality: int = 0
    last_frame_mono: float = field(default_factory=time.monotonic)
    agent_errors: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "active": self.active,
            "reason": self.reason.value,
            "message": self.message,
            "consecutive_low_quality": self.consecutive_low_quality,
            "agent_errors": self.agent_errors,
            "seconds_active": (
                round(time.monotonic() - self.since_mono, 1)
                if self.active and self.since_mono
                else 0.0
            ),
        }


class FailSafeGuard:
    """
    Tracks stream health and forces a safe mode that blocks proactive actions.

    Override (pause) and low-impact restore tools remain available via control plane.
    """

    def __init__(
        self,
        *,
        stall_sec: float = 3.0,
        low_quality_threshold: float = 0.35,
        low_quality_streak: int = 8,
        max_agent_errors: int = 3,
    ) -> None:
        self.stall_sec = stall_sec
        self.low_quality_threshold = low_quality_threshold
        self.low_quality_streak = low_quality_streak
        self.max_agent_errors = max_agent_errors
        self.state = FailSafeState()

    def note_frame(self, quality_overall: float, *, dropout: bool = False) -> FailSafeState:
        now = time.monotonic()
        self.state.last_frame_mono = now
        if dropout or quality_overall < self.low_quality_threshold:
            self.state.consecutive_low_quality += 1
        else:
            self.state.consecutive_low_quality = 0
            # Auto-clear quality-based fail-safe when signal recovers
            if self.state.active and self.state.reason in {
                FailSafeReason.LOW_QUALITY,
                FailSafeReason.STREAM_STALL,
            }:
                self.clear(reason_ok="signal_recovered")

        if self.state.consecutive_low_quality >= self.low_quality_streak:
            self.trip(
                FailSafeReason.LOW_QUALITY,
                "Signal quality low — proactive actions limited for safety.",
            )
        return self.state

    def note_heartbeat(self) -> FailSafeState:
        """Call periodically; trips if no frames for stall_sec."""
        gap = time.monotonic() - self.state.last_frame_mono
        if gap >= self.stall_sec:
            self.trip(
                FailSafeReason.STREAM_STALL,
                f"No neural frames for {gap:.1f}s — fail-safe active.",
            )
        return self.state

    def note_agent_error(self, exc: BaseException | str) -> FailSafeState:
        self.state.agent_errors += 1
        if self.state.agent_errors >= self.max_agent_errors:
            self.trip(
                FailSafeReason.AGENT_ERROR,
                f"Agent errors ({self.state.agent_errors}) — proactive actions halted.",
            )
        return self.state

    def note_user_pause(self, paused: bool) -> FailSafeState:
        if paused:
            self.trip(FailSafeReason.USER_PAUSE, "Architect paused by user.")
        elif self.state.reason == FailSafeReason.USER_PAUSE:
            self.clear(reason_ok="user_resumed")
        return self.state

    def trip(self, reason: FailSafeReason, message: str) -> None:
        # User pause is soft; don't override a harder trip message unless upgrading
        if self.state.active and self.state.reason == FailSafeReason.USER_PAUSE and reason != FailSafeReason.USER_PAUSE:
            pass  # allow upgrade
        self.state.active = True
        self.state.reason = reason
        self.state.message = message
        if self.state.since_mono is None:
            self.state.since_mono = time.monotonic()

    def clear(self, *, reason_ok: str = "") -> None:
        self.state.active = False
        self.state.reason = FailSafeReason.NONE
        self.state.message = reason_ok or ""
        self.state.since_mono = None
        self.state.consecutive_low_quality = 0
        # keep agent_errors for diagnostics unless full reset
        if reason_ok == "user_resumed" or reason_ok == "manual_clear":
            self.state.agent_errors = 0

    @property
    def blocks_proactive(self) -> bool:
        return self.state.active

    def allow_tool(self, tool_id: str, *, impact: str) -> bool:
        """Even in fail-safe, allow control/restore tools; block IoT and medium+."""
        if not self.state.active:
            return True
        # Always allow explicit restores / low-impact UI that reduces control surface
        if tool_id in {
            "notify.allow_all",
            "focus.disable",
            "ui.set_density",
            "agent.undo",
        }:
            return True
        if tool_id.startswith("iot."):
            return False
        if impact in {"medium", "high"}:
            return False
        # Block prepare/protect tools while failed
        if tool_id in {
            "notify.suppress_noncritical",
            "focus.enable",
            "recipe.apply",
            "prepare.context",
            "tasks.queue_next",
            "iot.lights.dim_for_focus",
        }:
            return False
        return impact == "low"
