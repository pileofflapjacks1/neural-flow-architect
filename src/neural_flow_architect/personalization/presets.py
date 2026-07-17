"""Named daily presets for one-tap setup (implant-user friendly)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class DailyPreset:
    id: str
    label: str
    description: str
    recipe: str = "study"
    user_goal: str = "deep work"
    predictive_enabled: bool = False
    agent_paused: bool = False
    simple_mode: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


BUILTIN_PRESETS: list[DailyPreset] = [
    DailyPreset(
        id="morning_focus",
        label="Morning focus",
        description="Quiet study setup for deep work blocks",
        recipe="study",
        user_goal="deep work",
        predictive_enabled=False,
        simple_mode=True,
    ),
    DailyPreset(
        id="creative",
        label="Creative session",
        description="Calm UI for art, writing, or design",
        recipe="create",
        user_goal="creative focus",
        simple_mode=True,
    ),
    DailyPreset(
        id="light_social",
        label="Messages & social",
        description="Notifications back; co-pilot stays gentle",
        recipe="social",
        user_goal="communication",
        predictive_enabled=False,
        simple_mode=True,
    ),
    DailyPreset(
        id="wind_down",
        label="Wind down",
        description="Rest recipe — protect recovery, not productivity",
        recipe="rest",
        user_goal="recovery",
        agent_paused=False,
        simple_mode=True,
    ),
    DailyPreset(
        id="power_user",
        label="Power user",
        description="Full controls + optional predictive layer",
        recipe="study",
        user_goal="deep work",
        predictive_enabled=True,
        simple_mode=False,
    ),
]


def list_presets(custom_dir: Path | None = None) -> list[dict[str, Any]]:
    presets = [p.to_dict() for p in BUILTIN_PRESETS]
    if custom_dir and custom_dir.exists():
        for path in sorted(custom_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "id" in data:
                    presets.append(data)
            except (OSError, json.JSONDecodeError):
                continue
    return presets


def get_preset(preset_id: str, custom_dir: Path | None = None) -> DailyPreset | None:
    for p in BUILTIN_PRESETS:
        if p.id == preset_id:
            return p
    if custom_dir:
        path = custom_dir / f"{preset_id}.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return DailyPreset(
                id=str(data.get("id", preset_id)),
                label=str(data.get("label", preset_id)),
                description=str(data.get("description", "")),
                recipe=str(data.get("recipe", "study")),
                user_goal=str(data.get("user_goal", "deep work")),
                predictive_enabled=bool(data.get("predictive_enabled", False)),
                agent_paused=bool(data.get("agent_paused", False)),
                simple_mode=bool(data.get("simple_mode", True)),
            )
    return None


def save_custom_preset(directory: Path, preset: DailyPreset) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{preset.id}.json"
    path.write_text(json.dumps(preset.to_dict(), indent=2), encoding="utf-8")
    return path
