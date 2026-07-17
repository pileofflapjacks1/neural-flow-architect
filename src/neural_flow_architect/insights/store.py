"""Session summary store — features/summaries only, never raw by default."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from neural_flow_architect.core.types import FlowEstimate, FlowState


@dataclass
class SessionSummary:
    session_id: str
    started_at: datetime
    ended_at: datetime | None = None
    state_minutes: dict[str, float] = field(default_factory=dict)
    actions_count: int = 0
    explanations: list[str] = field(default_factory=list)
    peak_engagement: float = 0.0

    def to_dict(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "state_minutes": self.state_minutes,
            "actions_count": self.actions_count,
            "explanations": self.explanations[-50:],
            "peak_engagement": self.peak_engagement,
        }


class InsightsStore:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self._current: SessionSummary | None = None
        self._last_state: FlowState | None = None
        self._last_ts: datetime | None = None

    def start_session(self) -> SessionSummary:
        self._current = SessionSummary(
            session_id=str(uuid4()),
            started_at=datetime.utcnow(),
        )
        self._last_state = None
        self._last_ts = self._current.started_at
        return self._current

    def observe_flow(self, estimate: FlowEstimate) -> None:
        if self._current is None:
            self.start_session()
        assert self._current is not None
        now = datetime.utcnow()
        if self._last_state is not None and self._last_ts is not None:
            delta_min = max(0.0, (now - self._last_ts).total_seconds() / 60.0)
            key = self._last_state.value
            self._current.state_minutes[key] = (
                self._current.state_minutes.get(key, 0.0) + delta_min
            )
        self._last_state = estimate.state
        self._last_ts = now
        self._current.peak_engagement = max(
            self._current.peak_engagement, estimate.engagement
        )

    def observe_action(self, explanation_text: str) -> None:
        if self._current is None:
            return
        self._current.actions_count += 1
        self._current.explanations.append(explanation_text)

    def end_session(self) -> SessionSummary | None:
        if self._current is None:
            return None
        self._current.ended_at = datetime.utcnow()
        path = self.directory / f"{self._current.session_id}.json"
        path.write_text(json.dumps(self._current.to_dict(), indent=2), encoding="utf-8")
        summary = self._current
        self._current = None
        return summary
