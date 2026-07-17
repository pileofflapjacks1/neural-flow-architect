"""First-run onboarding state for users and caregivers."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

ONBOARDING_STEPS = (
    "welcome",
    "privacy",
    "controls",
    "preset",
    "ready",
)


@dataclass
class OnboardingState:
    completed: bool = False
    current_step: str = "welcome"
    completed_steps: list[str] = field(default_factory=list)
    simple_mode: bool = True
    chosen_preset: str | None = None
    caregiver_assisted: bool = False
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def load(cls, path: Path) -> OnboardingState:
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(
                completed=bool(data.get("completed", False)),
                current_step=str(data.get("current_step", "welcome")),
                completed_steps=list(data.get("completed_steps") or []),
                simple_mode=bool(data.get("simple_mode", True)),
                chosen_preset=data.get("chosen_preset"),
                caregiver_assisted=bool(data.get("caregiver_assisted", False)),
                updated_at=str(data.get("updated_at") or datetime.utcnow().isoformat()),
            )
        except (OSError, json.JSONDecodeError, TypeError):
            return cls()

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.updated_at = datetime.utcnow().isoformat()
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    def advance(self, step: str | None = None) -> None:
        if step is None:
            try:
                idx = ONBOARDING_STEPS.index(self.current_step)
                step = ONBOARDING_STEPS[min(idx + 1, len(ONBOARDING_STEPS) - 1)]
            except ValueError:
                step = "ready"
        if self.current_step not in self.completed_steps:
            self.completed_steps.append(self.current_step)
        self.current_step = step
        if step == "ready" or (set(ONBOARDING_STEPS[:-1]).issubset(set(self.completed_steps))):
            if step == "ready":
                self.completed = True
                if "ready" not in self.completed_steps:
                    self.completed_steps.append("ready")

    def copy_for_ui(self) -> dict[str, Any]:
        data = self.to_dict()
        data["steps"] = list(ONBOARDING_STEPS)
        data["copy"] = STEP_COPY
        return data


STEP_COPY: dict[str, dict[str, str]] = {
    "welcome": {
        "title": "Welcome",
        "body": (
            "Neural Flow Architect helps protect deep focus using your BCI signal. "
            "You always stay in control — Pause and Undo are always available."
        ),
    },
    "privacy": {
        "title": "Your data stays local",
        "body": (
            "Neural processing defaults to this device. Raw samples are not saved. "
            "This is research/assistive software — not a medical device."
        ),
    },
    "controls": {
        "title": "Three big controls",
        "body": (
            "Pause Architect — stop proactive actions instantly. "
            "Undo — reverse the last change. "
            "Rest mode — wind down gently when you need a break."
        ),
    },
    "preset": {
        "title": "Pick a daily preset",
        "body": (
            "Choose Morning focus, Creative, Social, or Wind down. "
            "You can change this anytime with large buttons."
        ),
    },
    "ready": {
        "title": "You're ready",
        "body": (
            "Start a session when you want. If someone is helping with setup, "
            "they can leave now — everyday use is designed for low-precision control."
        ),
    },
}
