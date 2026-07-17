"""Undo stack for reversible Architect actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass
class UndoRecord:
    tool_id: str
    previous_digital: dict[str, Any]
    explanation: str
    undo_token: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    params: dict[str, Any] = field(default_factory=dict)


class UndoStack:
    """Last-in-first-out stack of reversible environment changes."""

    def __init__(self, max_size: int = 32) -> None:
        self.max_size = max_size
        self._items: list[UndoRecord] = []

    def push(self, record: UndoRecord) -> None:
        self._items.append(record)
        if len(self._items) > self.max_size:
            self._items.pop(0)

    def pop(self) -> UndoRecord | None:
        if not self._items:
            return None
        return self._items.pop()

    def peek(self) -> UndoRecord | None:
        return self._items[-1] if self._items else None

    @property
    def can_undo(self) -> bool:
        return bool(self._items)

    def clear(self) -> None:
        self._items.clear()

    def as_list(self) -> list[dict[str, Any]]:
        return [
            {
                "tool_id": r.tool_id,
                "explanation": r.explanation,
                "undo_token": r.undo_token,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in self._items
        ]
