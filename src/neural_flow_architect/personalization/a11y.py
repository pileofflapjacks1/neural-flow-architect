"""Accessibility preferences for BCI-native long sessions."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AccessibilitySettings(BaseModel):
    """Stored inside user profile preferences payload."""

    # UI scale multiplier for targets and type (1.0–1.75)
    ui_scale: float = Field(default=1.15, ge=1.0, le=2.0)
    high_contrast: bool = False
    reduced_motion: bool = True
    # Suggested dwell ms for future dwell-select widgets
    dwell_ms: int = Field(default=1200, ge=400, le=3000)
    sticky_controls: bool = True
    keyboard_enabled: bool = True
    voice_command_bar: bool = True
    announce_actions: bool = False  # screen-reader-friendly live region verbosity

    def css_vars(self) -> dict[str, str]:
        return {
            "--nfa-scale": str(self.ui_scale),
            "--target-min": f"{int(64 * self.ui_scale)}px",
        }
