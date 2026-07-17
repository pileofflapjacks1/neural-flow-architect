"""Caregiver independence checklist — setup then step back."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

CHECKLIST_ITEMS = (
    ("start_session", "User can start a session alone"),
    ("pause", "User can Pause the Architect"),
    ("undo", "User can Undo an action"),
    ("rest", "User can enter Rest mode"),
    ("label_or_review", "User can label flow or complete a block review"),
    ("helper_leaves", "Helper can leave; user remains in control"),
)


@dataclass
class CaregiverChecklist:
    items: dict[str, bool] = field(default_factory=dict)
    completed: bool = False
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    notes: str = ""

    def __post_init__(self) -> None:
        for key, _ in CHECKLIST_ITEMS:
            self.items.setdefault(key, False)

    def mark(self, key: str, done: bool = True) -> None:
        if key in dict(CHECKLIST_ITEMS):
            self.items[key] = done
        self.completed = all(self.items.get(k, False) for k, _ in CHECKLIST_ITEMS)
        self.updated_at = datetime.utcnow().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": [
                {
                    "id": key,
                    "label": label,
                    "done": bool(self.items.get(key, False)),
                }
                for key, label in CHECKLIST_ITEMS
            ],
            "completed": self.completed,
            "updated_at": self.updated_at,
            "notes": self.notes,
            "progress": sum(1 for k, _ in CHECKLIST_ITEMS if self.items.get(k)),
            "total": len(CHECKLIST_ITEMS),
        }

    @classmethod
    def load(cls, path: Path) -> CaregiverChecklist:
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            c = cls(
                items=dict(data.get("items_map") or {}),
                completed=bool(data.get("completed", False)),
                updated_at=str(data.get("updated_at") or datetime.utcnow().isoformat()),
                notes=str(data.get("notes") or ""),
            )
            # hydrate from list form if present
            for row in data.get("items") or []:
                if isinstance(row, dict) and "id" in row:
                    c.items[str(row["id"])] = bool(row.get("done"))
            c.completed = all(c.items.get(k, False) for k, _ in CHECKLIST_ITEMS)
            return c
        except (OSError, json.JSONDecodeError, TypeError):
            return cls()

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "items_map": self.items,
            "items": self.to_dict()["items"],
            "completed": self.completed,
            "updated_at": self.updated_at,
            "notes": self.notes,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
