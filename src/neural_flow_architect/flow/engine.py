"""Flow estimation and discrete state machine with hysteresis."""

from __future__ import annotations

import time

from neural_flow_architect.core.types import FeatureWindow, FlowEstimate, FlowState, QualityFlags


class FlowEngine:
    """
    Multi-dimensional flow-related estimation for prototype use.

    Scientific humility: outputs are **estimated proxies**, not ground-truth phenomenology.
    """

    def __init__(
        self,
        protect_engagement_threshold: float = 0.62,
        deep_flow_engagement_threshold: float = 0.82,
        min_confidence: float = 0.35,
    ) -> None:
        self.protect_t = protect_engagement_threshold
        self.deep_t = deep_flow_engagement_threshold
        self.min_confidence = min_confidence
        self._state = FlowState.UNKNOWN
        self._state_entered_ns = time.time_ns()
        self._ema_engagement = 0.4
        self._ema_alpha = 0.2

    @property
    def state(self) -> FlowState:
        return self._state

    def update(self, window: FeatureWindow) -> FlowEstimate:
        f = window.features
        quality = window.quality
        eng_raw = float(f.get("engagement_proxy", 0.0))
        self._ema_engagement = (
            self._ema_alpha * eng_raw + (1 - self._ema_alpha) * self._ema_engagement
        )
        engagement = float(self._ema_engagement)
        arousal = float(f.get("arousal_proxy", 0.5))
        # Optimal arousal is mid-high, not max
        arousal_balance = float(max(0.0, 1.0 - abs(arousal - 0.55) / 0.55))
        self_ref = float(f.get("self_ref_proxy", 0.5))
        ease = float(f.get("ease_proxy", 0.5))
        confidence = _confidence(quality, f)

        reasons: list[str] = []
        new_state = self._transition(engagement, arousal_balance, self_ref, ease, confidence, reasons)
        if new_state != self._state:
            self._state = new_state
            self._state_entered_ns = window.timestamp_ns
            reasons.append(f"transition→{new_state.value}")

        minutes = max(0.0, (window.timestamp_ns - self._state_entered_ns) / 1e9 / 60.0)
        return FlowEstimate(
            timestamp_ns=window.timestamp_ns,
            engagement=engagement,
            arousal_balance=arousal_balance,
            self_ref_proxy=self_ref,
            effort_ease=ease,
            confidence=confidence,
            state=self._state,
            minutes_in_state=minutes,
            reasons=reasons,
        )

    def _transition(
        self,
        engagement: float,
        arousal_balance: float,
        self_ref: float,
        ease: float,
        confidence: float,
        reasons: list[str],
    ) -> FlowState:
        if confidence < self.min_confidence:
            reasons.append("low_confidence")
            return FlowState.UNKNOWN

        # Hysteresis margins
        enter = 0.03
        exit_m = 0.05
        composite = 0.5 * engagement + 0.2 * arousal_balance + 0.15 * (1 - self_ref) + 0.15 * ease

        current = self._state
        if composite < 0.28 and engagement < 0.35:
            return FlowState.LOW if engagement > 0.15 else FlowState.FATIGUED

        if current == FlowState.DEEP_FLOW:
            if engagement < self.deep_t - exit_m:
                return FlowState.FLOW if engagement >= self.protect_t - exit_m else FlowState.POST_FLOW
            return FlowState.DEEP_FLOW

        if current == FlowState.FLOW:
            if engagement >= self.deep_t + enter and ease > 0.45:
                return FlowState.DEEP_FLOW
            if engagement < self.protect_t - exit_m:
                return FlowState.POST_FLOW if engagement > 0.4 else FlowState.LOW
            return FlowState.FLOW

        if current in {FlowState.PRE_FLOW, FlowState.LOW, FlowState.POST_FLOW, FlowState.UNKNOWN, FlowState.FATIGUED}:
            if engagement >= self.deep_t and ease > 0.5:
                return FlowState.DEEP_FLOW
            if engagement >= self.protect_t + enter:
                return FlowState.FLOW
            if engagement >= self.protect_t - 0.12 and engagement > 0.45:
                return FlowState.PRE_FLOW
            if current == FlowState.POST_FLOW and engagement < 0.45:
                return FlowState.POST_FLOW
            return FlowState.LOW if engagement < 0.45 else FlowState.PRE_FLOW

        return current


def _confidence(quality: QualityFlags, features: dict[str, float]) -> float:
    base = quality.overall
    if quality.dropout or quality.flatline:
        return min(base, 0.2)
    variance = features.get("variance", 1.0)
    if variance < 1e-8:
        base *= 0.5
    return float(max(0.0, min(1.0, base)))
