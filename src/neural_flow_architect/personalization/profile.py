"""Per-user preference and threshold profile (local)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from neural_flow_architect.core.types import UserPreferences


@dataclass
class UserProfile:
    user_id: str = "local"
    preferences: UserPreferences = field(default_factory=UserPreferences)
    protect_engagement_threshold: float = 0.62
    deep_flow_engagement_threshold: float = 0.82
    notes: str = ""

    def save(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{self.user_id}.json"
        payload = {
            "user_id": self.user_id,
            "preferences": self.preferences.model_dump(),
            "protect_engagement_threshold": self.protect_engagement_threshold,
            "deep_flow_engagement_threshold": self.deep_flow_engagement_threshold,
            "notes": self.notes,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    @classmethod
    def load(cls, directory: Path, user_id: str = "local") -> UserProfile:
        path = directory / f"{user_id}.json"
        if not path.exists():
            return cls(user_id=user_id)
        data = json.loads(path.read_text(encoding="utf-8"))
        prefs = UserPreferences.model_validate(data.get("preferences", {}))
        return cls(
            user_id=data.get("user_id", user_id),
            preferences=prefs,
            protect_engagement_threshold=float(
                data.get("protect_engagement_threshold", 0.62)
            ),
            deep_flow_engagement_threshold=float(
                data.get("deep_flow_engagement_threshold", 0.82)
            ),
            notes=str(data.get("notes", "")),
        )
