"""Append-only local audit log — actions, overrides, feedback (never raw neural)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass
class AuditEvent:
    event_type: str
    message: str
    detail: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AuditLog:
    """JSONL audit trail under data/audit/."""

    def __init__(self, directory: Path, *, max_memory: int = 200) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "audit.jsonl"
        self.max_memory = max_memory
        self._recent: list[AuditEvent] = []

    def record(
        self,
        event_type: str,
        message: str,
        **detail: Any,
    ) -> AuditEvent:
        # Strip anything that looks like raw samples
        safe = {k: v for k, v in detail.items() if k not in {"data", "samples", "raw"}}
        event = AuditEvent(event_type=event_type, message=message, detail=safe)
        self._recent.append(event)
        if len(self._recent) > self.max_memory:
            self._recent = self._recent[-self.max_memory :]
        try:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event.to_dict()) + "\n")
        except OSError:
            pass
        return event

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        if self._recent:
            return [e.to_dict() for e in self._recent[-limit:]]
        # Fall back to tail of file
        if not self.path.exists():
            return []
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
            out: list[dict[str, Any]] = []
            for line in lines[-limit:]:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            return out
        except OSError:
            return []
