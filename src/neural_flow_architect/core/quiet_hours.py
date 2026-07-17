"""Quiet hours — reduce proactive medium/high actions overnight."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class QuietHours:
    enabled: bool = False
    start_hour: int = 22  # inclusive, local
    end_hour: int = 7  # exclusive, local

    def is_quiet(self, now: datetime | None = None) -> bool:
        if not self.enabled:
            return False
        now = now or datetime.now()
        h = now.hour
        start, end = self.start_hour % 24, self.end_hour % 24
        if start == end:
            return True  # full day quiet if equal (degenerate)
        if start < end:
            return start <= h < end
        # wraps midnight, e.g. 22 → 7
        return h >= start or h < end

    def to_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "start_hour": self.start_hour,
            "end_hour": self.end_hour,
            "active_now": self.is_quiet(),
        }
