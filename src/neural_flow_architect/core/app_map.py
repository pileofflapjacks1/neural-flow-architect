"""User-editable app name → category map (local JSON)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VALID_CATEGORIES = frozenset({"study", "create", "social", "system", "unknown"})

DEFAULT_MAP: dict[str, str] = {
    # exact / substring keys are lowercased on match
    "code": "study",
    "cursor": "study",
    "obsidian": "study",
    "notion": "study",
    "terminal": "study",
    "iterm": "study",
    "chrome": "study",
    "safari": "study",
    "firefox": "study",
    "figma": "create",
    "photoshop": "create",
    "blender": "create",
    "slack": "social",
    "discord": "social",
    "messages": "social",
    "mail": "social",
    "zoom": "social",
    "teams": "social",
    "finder": "system",
}


class AppCategoryMap:
    """
    Local overrides for active-app categorization.

    Matching: case-insensitive substring of the frontmost app name.
    Longer keys win over shorter ones when multiple match.
    """

    def __init__(self, mapping: dict[str, str] | None = None) -> None:
        self.mapping: dict[str, str] = {
            k.lower(): v for k, v in (mapping or DEFAULT_MAP).items() if v in VALID_CATEGORIES
        }

    @classmethod
    def load(cls, path: Path) -> AppCategoryMap:
        if not path.exists():
            m = cls()
            m.save(path)  # seed defaults for user edit
            return m
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            raw = data.get("map") if isinstance(data, dict) else data
            if not isinstance(raw, dict):
                return cls()
            return cls({str(k): str(v) for k, v in raw.items()})
        except (OSError, json.JSONDecodeError, TypeError):
            return cls()

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "description": (
                "Substring map: if the frontmost app name contains the key "
                "(case-insensitive), use that category. Valid: study, create, "
                "social, system, unknown."
            ),
            "map": dict(sorted(self.mapping.items())),
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def categorize(self, name: str | None, *, fallback: str = "unknown") -> str:
        if not name:
            return fallback
        lower = name.lower()
        # longest key first for specificity
        for key in sorted(self.mapping.keys(), key=len, reverse=True):
            if key in lower:
                return self.mapping[key]
        return fallback

    def set_entry(self, key: str, category: str) -> None:
        cat = category.lower().strip()
        if cat not in VALID_CATEGORIES:
            raise ValueError(f"Invalid category {category}")
        self.mapping[key.lower().strip()] = cat

    def remove_entry(self, key: str) -> None:
        self.mapping.pop(key.lower().strip(), None)

    def to_dict(self) -> dict[str, Any]:
        return {"map": dict(sorted(self.mapping.items())), "categories": sorted(VALID_CATEGORIES)}
