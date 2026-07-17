"""Predictive intent-precursor layer (research-grade, opt-in).

Uses only derived flow metrics (never raw samples). Heuristics estimate
short-horizon precursors such as rising engagement or impending break.
These are *not* mind-reading and must stay off by default.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from neural_flow_architect.core.types import (
    ActionProposal,
    FlowEstimate,
    FlowState,
    ImpactLevel,
    WorldSnapshot,
)


class PrecursorKind(str, Enum):
    RISING_FLOW = "rising_flow"
    BREAKING_FLOW = "breaking_flow"
    TASK_SWITCH_HINT = "task_switch_hint"
    FATIGUE_HINT = "fatigue_hint"


@dataclass
class PrecursorEvent:
    kind: PrecursorKind
    confidence: float
    horizon_sec: float
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "confidence": round(self.confidence, 3),
            "horizon_sec": self.horizon_sec,
            "detail": self.detail,
        }


class PrecursorTracker:
    """Rolling window of engagement/state for simple derivative features."""

    def __init__(self, window: int = 24) -> None:
        self._engagement: deque[float] = deque(maxlen=window)
        self._states: deque[str] = deque(maxlen=window)
        self._ease: deque[float] = deque(maxlen=window)
        self.enabled = False
        self.min_confidence = 0.55

    def reset(self) -> None:
        self._engagement.clear()
        self._states.clear()
        self._ease.clear()

    def observe(self, estimate: FlowEstimate) -> list[PrecursorEvent]:
        self._engagement.append(estimate.engagement)
        self._states.append(estimate.state.value)
        self._ease.append(estimate.effort_ease)
        if not self.enabled or len(self._engagement) < 6:
            return []
        return self._detect()

    def _slope(self, series: deque[float], n: int = 6) -> float:
        vals = list(series)[-n:]
        if len(vals) < 2:
            return 0.0
        # Simple first-last slope normalized by steps
        return (vals[-1] - vals[0]) / (len(vals) - 1)

    def _detect(self) -> list[PrecursorEvent]:
        events: list[PrecursorEvent] = []
        eng_slope = self._slope(self._engagement)
        ease_slope = self._slope(self._ease)
        recent = list(self._states)[-4:]
        eng = self._engagement[-1]

        # Rising flow: positive engagement slope while not yet deep
        if (
            eng_slope > 0.015
            and eng > 0.45
            and recent[-1]
            in {
                FlowState.LOW.value,
                FlowState.PRE_FLOW.value,
                FlowState.FLOW.value,
            }
        ):
            conf = min(0.95, 0.5 + eng_slope * 8 + (eng - 0.45) * 0.5)
            if conf >= self.min_confidence:
                events.append(
                    PrecursorEvent(
                        kind=PrecursorKind.RISING_FLOW,
                        confidence=conf,
                        horizon_sec=30.0,
                        detail={"engagement_slope": round(eng_slope, 4), "engagement": eng},
                    )
                )

        # Breaking flow: negative slope from flow/deep
        if eng_slope < -0.02 and recent[-1] in {
            FlowState.FLOW.value,
            FlowState.DEEP_FLOW.value,
        }:
            conf = min(0.95, 0.5 + abs(eng_slope) * 10)
            if conf >= self.min_confidence:
                events.append(
                    PrecursorEvent(
                        kind=PrecursorKind.BREAKING_FLOW,
                        confidence=conf,
                        horizon_sec=20.0,
                        detail={"engagement_slope": round(eng_slope, 4)},
                    )
                )

        # Task-switch hint: volatility in state labels + ease drop
        unique_recent = len(set(recent))
        if unique_recent >= 3 and ease_slope < -0.01 and eng > 0.4:
            conf = min(0.9, 0.45 + 0.1 * unique_recent)
            if conf >= self.min_confidence:
                events.append(
                    PrecursorEvent(
                        kind=PrecursorKind.TASK_SWITCH_HINT,
                        confidence=conf,
                        horizon_sec=45.0,
                        detail={"recent_states": recent, "ease_slope": round(ease_slope, 4)},
                    )
                )

        # Fatigue: low engagement + low ease sustained
        if eng < 0.3 and self._ease[-1] < 0.35 and all(e < 0.4 for e in list(self._ease)[-4:]):
            events.append(
                PrecursorEvent(
                    kind=PrecursorKind.FATIGUE_HINT,
                    confidence=0.6,
                    horizon_sec=60.0,
                    detail={"engagement": eng, "ease": self._ease[-1]},
                )
            )

        return events


def propose_from_precursors(
    events: list[PrecursorEvent],
    snapshot: WorldSnapshot,
) -> list[ActionProposal]:
    """Map precursors to *preparatory* low-impact actions only."""
    proposals: list[ActionProposal] = []
    for ev in events:
        causes: list[dict[str, Any]] = [
            {"signal": "module", "value": "predictor"},
            {"signal": "precursor", "value": ev.kind.value},
            {"signal": "confidence", "value": round(ev.confidence, 3)},
            {"signal": "horizon_sec", "value": ev.horizon_sec},
        ]
        if ev.kind == PrecursorKind.RISING_FLOW:
            proposals.append(
                ActionProposal(
                    tool_id="prepare.context",
                    impact=ImpactLevel.LOW,
                    params={"hint": "rising_flow", "recipe": snapshot.context.recipe},
                    score=0.4 + 0.3 * ev.confidence,
                    causes=causes
                    + [
                        {
                            "signal": "reason",
                            "value": "prepare focus supports before flow consolidates",
                        }
                    ],
                )
            )
        elif ev.kind == PrecursorKind.BREAKING_FLOW:
            proposals.append(
                ActionProposal(
                    tool_id="prepare.context",
                    impact=ImpactLevel.LOW,
                    params={"hint": "breaking_flow"},
                    score=0.35 + 0.25 * ev.confidence,
                    causes=causes
                    + [{"signal": "reason", "value": "soften environment as engagement dips"}],
                )
            )
        elif ev.kind == PrecursorKind.TASK_SWITCH_HINT:
            proposals.append(
                ActionProposal(
                    tool_id="tasks.queue_next",
                    impact=ImpactLevel.LOW,
                    params={"suggestion": "next logical micro-task"},
                    score=0.3 + 0.2 * ev.confidence,
                    causes=causes
                    + [
                        {
                            "signal": "reason",
                            "value": "possible task-switch precursor — queue non-modal suggestion",
                        }
                    ],
                )
            )
        elif ev.kind == PrecursorKind.FATIGUE_HINT:
            proposals.append(
                ActionProposal(
                    tool_id="prepare.context",
                    impact=ImpactLevel.LOW,
                    params={"hint": "fatigue", "recipe": "rest"},
                    score=0.45,
                    causes=causes
                    + [
                        {
                            "signal": "reason",
                            "value": "fatigue-like pattern — prepare rest supports",
                        }
                    ],
                )
            )
    return sorted(proposals, key=lambda p: p.score, reverse=True)
