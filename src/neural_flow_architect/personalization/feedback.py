"""Action feedback — helpful / unhelpful / never for preference learning."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

FeedbackRating = Literal["helpful", "unhelpful", "never"]


@dataclass
class ActionFeedback:
    tool_id: str
    rating: FeedbackRating
    timestamp: datetime = field(default_factory=datetime.utcnow)
    note: str = ""
    mode: str = ""
    engagement: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "rating": self.rating,
            "timestamp": self.timestamp.isoformat(),
            "note": self.note,
            "mode": self.mode,
            "engagement": self.engagement,
        }


@dataclass
class ToolAffinity:
    """Per-tool scores used by the governor to prefer/avoid tools."""

    helpful: int = 0
    unhelpful: int = 0
    never: bool = False

    @property
    def score_delta(self) -> float:
        if self.never:
            return -1.0
        # Bounded boost/penalty
        return max(-0.5, min(0.5, 0.08 * self.helpful - 0.12 * self.unhelpful))

    def to_dict(self) -> dict[str, Any]:
        return {
            "helpful": self.helpful,
            "unhelpful": self.unhelpful,
            "never": self.never,
            "score_delta": round(self.score_delta, 3),
        }


class FeedbackStore:
    def __init__(self) -> None:
        self.history: list[ActionFeedback] = []
        self.affinity: dict[str, ToolAffinity] = {}

    def record(
        self,
        tool_id: str,
        rating: FeedbackRating,
        *,
        note: str = "",
        mode: str = "",
        engagement: float = 0.0,
        denied_tools: list[str] | None = None,
        granted_tools: list[str] | None = None,
    ) -> dict[str, Any]:
        fb = ActionFeedback(
            tool_id=tool_id,
            rating=rating,
            note=note,
            mode=mode,
            engagement=engagement,
        )
        self.history.append(fb)
        if len(self.history) > 200:
            self.history = self.history[-200:]

        aff = self.affinity.setdefault(tool_id, ToolAffinity())
        denied = set(denied_tools or [])
        granted = set(granted_tools or [])

        if rating == "helpful":
            aff.helpful += 1
            aff.never = False
            denied.discard(tool_id)
            # Soft grant after repeated helpful
            if aff.helpful >= 3:
                granted.add(tool_id)
        elif rating == "unhelpful":
            aff.unhelpful += 1
            granted.discard(tool_id)
        elif rating == "never":
            aff.never = True
            denied.add(tool_id)
            granted.discard(tool_id)

        return {
            "feedback": fb.to_dict(),
            "affinity": aff.to_dict(),
            "denied_tools": sorted(denied),
            "granted_tools": sorted(granted),
            "message": _message(tool_id, rating),
        }

    def score_bonus(self, tool_id: str) -> float:
        aff = self.affinity.get(tool_id)
        return aff.score_delta if aff else 0.0

    def is_never(self, tool_id: str) -> bool:
        aff = self.affinity.get(tool_id)
        return bool(aff and aff.never)

    def as_dict(self) -> dict[str, Any]:
        return {
            "history": [h.to_dict() for h in self.history[-50:]],
            "affinity": {k: v.to_dict() for k, v in self.affinity.items()},
        }


def _message(tool_id: str, rating: FeedbackRating) -> str:
    if rating == "helpful":
        return f"Thanks — will prefer similar actions ({tool_id})."
    if rating == "unhelpful":
        return f"Got it — will use {tool_id} less often."
    return f"Understood — will never use {tool_id} unless you clear the block."
