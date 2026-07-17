"""Accessibility preferences for BCI-native long sessions."""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, Field

# Common presets (UI + docs); values match Access panel chips
DEFAULT_SCAN_PRESETS_MS: tuple[int, ...] = (800, 1400, 2000)
DEFAULT_DWELL_PRESETS_MS: tuple[int, ...] = (800, 1200, 1800)


class AccessibilitySettings(BaseModel):
    """Stored inside user profile preferences payload."""

    # UI scale multiplier for targets and type (1.0–1.75)
    ui_scale: float = Field(default=1.15, ge=1.0, le=2.0)
    high_contrast: bool = False
    reduced_motion: bool = True
    # Suggested dwell ms for dwell-select widgets
    dwell_ms: int = Field(default=1200, ge=400, le=3000)
    sticky_controls: bool = True
    keyboard_enabled: bool = True
    voice_command_bar: bool = True
    announce_actions: bool = True  # polite live-region verbosity for co-pilot changes
    scan_mode: bool = False
    scan_interval_ms: int = Field(default=1400, ge=600, le=4000)

    SCAN_PRESETS_MS: ClassVar[tuple[int, ...]] = DEFAULT_SCAN_PRESETS_MS
    DWELL_PRESETS_MS: ClassVar[tuple[int, ...]] = DEFAULT_DWELL_PRESETS_MS

    def css_vars(self) -> dict[str, str]:
        return {
            "--nfa-scale": str(self.ui_scale),
            "--target-min": f"{int(64 * self.ui_scale)}px",
        }
