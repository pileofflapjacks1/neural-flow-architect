"""Shared domain types for Neural Flow Architect."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, Field, field_validator


class SourceKind(str, Enum):
    SIMULATOR = "simulator"
    OPEN_EEG = "open_eeg"
    INTRACORTICAL = "intracortical"
    INTENT_API = "intent_api"
    REPLAY = "replay"


class FlowState(str, Enum):
    UNKNOWN = "unknown"
    LOW = "low"
    PRE_FLOW = "pre_flow"
    FLOW = "flow"
    DEEP_FLOW = "deep_flow"
    POST_FLOW = "post_flow"
    FATIGUED = "fatigued"


class AgentMode(str, Enum):
    IDLE = "idle"
    IDLE_DEGRADED = "idle_degraded"
    PROTECT = "protect"
    RE_ENTER = "re_enter"
    TRANSITION = "transition"


class ImpactLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class QualityFlags(BaseModel):
    clipping: bool = False
    flatline: bool = False
    high_noise: bool = False
    dropout: bool = False
    overall: float = Field(default=1.0, ge=0.0, le=1.0)

    @property
    def is_usable(self) -> bool:
        return self.overall >= 0.35 and not self.dropout


class ChannelLayout(BaseModel):
    names: list[str] = Field(default_factory=list)
    units: str = "a.u."


class StreamMetadata(BaseModel):
    source_kind: SourceKind
    sampling_rate_hz: float
    n_channels: int
    layout: ChannelLayout = Field(default_factory=ChannelLayout)
    vendor: str | None = None
    device_id_hash: str | None = None
    adapter_name: str = "unknown"


class NeuralFrame(BaseModel):
    """One chunk of multichannel samples. Data is not validated element-wise for speed."""

    model_config = {"arbitrary_types_allowed": True}

    seq: int
    timestamp_ns: int
    data: NDArray[np.float64]
    quality: QualityFlags = Field(default_factory=QualityFlags)

    @field_validator("data")
    @classmethod
    def _check_2d(cls, v: NDArray[np.float64]) -> NDArray[np.float64]:
        if v.ndim != 2:
            raise ValueError("NeuralFrame.data must be 2-D (channels, samples)")
        return v


class IntentEvent(BaseModel):
    seq: int
    timestamp_ns: int
    intent_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class FeatureWindow(BaseModel):
    timestamp_ns: int
    features: dict[str, float]
    quality: QualityFlags = Field(default_factory=QualityFlags)


class FlowEstimate(BaseModel):
    timestamp_ns: int
    engagement: float = Field(ge=0.0, le=1.0)
    arousal_balance: float = Field(ge=0.0, le=1.0)
    self_ref_proxy: float = Field(ge=0.0, le=1.0)
    effort_ease: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    state: FlowState = FlowState.UNKNOWN
    minutes_in_state: float = 0.0
    reasons: list[str] = Field(default_factory=list)


class ContextSnapshot(BaseModel):
    active_app: str | None = None
    app_category: str = "unknown"  # study | create | social | system | unknown
    time_of_day: str = "unknown"
    hour: int | None = None
    user_goal: str | None = None
    recipe: str = "study"  # study | create | rest | social
    focus_session_id: str | None = None


class UserPreferences(BaseModel):
    protect_style: str = "calm"  # calm | assertive
    allow_iot: bool = False
    agent_paused: bool = False
    denied_tools: list[str] = Field(default_factory=list)
    granted_tools: list[str] = Field(default_factory=list)
    require_confirm_high_impact: bool = True
    preferred_recipe: str = "study"
    label_count: int = 0
    positive_flow_labels: int = 0
    simple_mode: bool = True
    active_preset: str | None = None
    # Accessibility (BCI-native long sessions)
    ui_scale: float = Field(default=1.15, ge=1.0, le=2.0)
    high_contrast: bool = False
    reduced_motion: bool = True
    dwell_ms: int = Field(default=1200, ge=400, le=3000)
    sticky_controls: bool = True
    keyboard_enabled: bool = True
    voice_command_bar: bool = True
    auto_start_on_preset: bool = False
    # Quiet hours (local clock) — soft-limit medium/high actions
    quiet_hours_enabled: bool = False
    quiet_hours_start: int = Field(default=22, ge=0, le=23)
    quiet_hours_end: int = Field(default=7, ge=0, le=23)
    # Soft recipe suggestion from active app (never auto-switch without consent)
    suggest_recipe_from_app: bool = True
    # Zero-precision sequential scanning mode
    scan_mode: bool = False
    scan_interval_ms: int = Field(default=1400, ge=600, le=4000)
    # Screen-reader / live-region verbosity for co-pilot state changes
    announce_actions: bool = True


class WorldSnapshot(BaseModel):
    time: datetime
    flow: FlowEstimate
    quality: QualityFlags
    context: ContextSnapshot = Field(default_factory=ContextSnapshot)
    preferences: UserPreferences = Field(default_factory=UserPreferences)


class ActionProposal(BaseModel):
    tool_id: str
    impact: ImpactLevel
    params: dict[str, Any] = Field(default_factory=dict)
    score: float = 0.0
    causes: list[dict[str, Any]] = Field(default_factory=list)


class Explanation(BaseModel):
    action: str
    text: str
    because: list[dict[str, Any]] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ActionResult(BaseModel):
    tool_id: str
    success: bool
    message: str = ""
    reversible: bool = True
    undo_token: str | None = None
    dry_run: bool = False
