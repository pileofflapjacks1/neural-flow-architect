"""Session summary store — features/summaries only, never raw by default."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from neural_flow_architect.core.types import FlowEstimate, FlowState


@dataclass
class SelfReportLabel:
    felt_in_flow: bool
    note: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    state_at_label: str = ""
    engagement_at_label: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "felt_in_flow": self.felt_in_flow,
            "note": self.note,
            "timestamp": self.timestamp.isoformat(),
            "state_at_label": self.state_at_label,
            "engagement_at_label": self.engagement_at_label,
        }


@dataclass
class SessionSummary:
    session_id: str
    started_at: datetime
    ended_at: datetime | None = None
    state_minutes: dict[str, float] = field(default_factory=dict)
    actions_count: int = 0
    undos_count: int = 0
    explanations: list[str] = field(default_factory=list)
    peak_engagement: float = 0.0
    labels: list[SelfReportLabel] = field(default_factory=list)
    adapter: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "state_minutes": self.state_minutes,
            "actions_count": self.actions_count,
            "undos_count": self.undos_count,
            "explanations": self.explanations[-50:],
            "peak_engagement": self.peak_engagement,
            "labels": [lab.to_dict() for lab in self.labels],
            "adapter": self.adapter,
            "flow_minutes": sum(
                v
                for k, v in self.state_minutes.items()
                if k in {"flow", "deep_flow", "pre_flow"}
            ),
        }


class InsightsStore:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self._current: SessionSummary | None = None
        self._last_state: FlowState | None = None
        self._last_ts: datetime | None = None

    @property
    def current(self) -> SessionSummary | None:
        return self._current

    def start_session(self, adapter: str = "unknown") -> SessionSummary:
        self._current = SessionSummary(
            session_id=str(uuid4()),
            started_at=datetime.utcnow(),
            adapter=adapter,
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

    def observe_undo(self) -> None:
        if self._current is None:
            return
        self._current.undos_count += 1

    def add_label(
        self,
        felt_in_flow: bool,
        note: str = "",
        *,
        state: str = "",
        engagement: float = 0.0,
    ) -> SelfReportLabel:
        if self._current is None:
            self.start_session()
        assert self._current is not None
        label = SelfReportLabel(
            felt_in_flow=felt_in_flow,
            note=note,
            state_at_label=state,
            engagement_at_label=engagement,
        )
        self._current.labels.append(label)
        return label

    def snapshot_current(self) -> dict[str, Any] | None:
        if self._current is None:
            return None
        # Include provisional end without closing
        data = self._current.to_dict()
        data["live"] = True
        return data

    def end_session(self, *, persist: bool = True) -> SessionSummary | None:
        if self._current is None:
            return None
        # Flush last state segment
        if self._last_state is not None and self._last_ts is not None:
            now = datetime.utcnow()
            delta_min = max(0.0, (now - self._last_ts).total_seconds() / 60.0)
            key = self._last_state.value
            self._current.state_minutes[key] = (
                self._current.state_minutes.get(key, 0.0) + delta_min
            )
        self._current.ended_at = datetime.utcnow()
        summary = self._current
        if persist:
            path = self.directory / f"{summary.session_id}.json"
            path.write_text(json.dumps(summary.to_dict(), indent=2), encoding="utf-8")
        self._current = None
        self._last_state = None
        self._last_ts = None
        return summary

    def list_sessions(self, limit: int = 20) -> list[dict[str, Any]]:
        files = sorted(self.directory.glob("*.json"), reverse=True)
        out: list[dict[str, Any]] = []
        for path in files[:limit]:
            try:
                out.append(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                continue
        return out

    def export_session(self, session_id: str, dest: Path) -> Path:
        src = self.directory / f"{session_id}.json"
        if not src.exists():
            raise FileNotFoundError(session_id)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        return dest
