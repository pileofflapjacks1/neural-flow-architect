"""Export / import local profiles (no raw neural data)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from neural_flow_architect.personalization.profile import UserProfile

EXPORT_VERSION = 1


def export_profile_bundle(
    profile: UserProfile,
    *,
    onboarding: dict[str, Any] | None = None,
    include_sessions_meta: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Privacy-safe backup: prefs, thresholds, onboarding — never raw samples.
    """
    return {
        "format": "neural-flow-architect-profile",
        "version": EXPORT_VERSION,
        "exported_at": datetime.utcnow().isoformat(),
        "disclaimer": "Not a medical record. Contains preferences only; no raw neural data.",
        "profile": {
            "user_id": profile.user_id,
            "preferences": profile.preferences.model_dump(),
            "protect_engagement_threshold": profile.protect_engagement_threshold,
            "deep_flow_engagement_threshold": profile.deep_flow_engagement_threshold,
            "notes": profile.notes,
        },
        "onboarding": onboarding or {},
        "sessions_meta": include_sessions_meta or [],
    }


def write_export(path: Path, bundle: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    return path


def import_profile_bundle(directory: Path, bundle: dict[str, Any]) -> UserProfile:
    if bundle.get("format") != "neural-flow-architect-profile":
        raise ValueError("Unrecognized backup format")
    data = bundle.get("profile") or {}
    from neural_flow_architect.core.types import UserPreferences

    prefs = UserPreferences.model_validate(data.get("preferences") or {})
    profile = UserProfile(
        user_id=str(data.get("user_id") or "local"),
        preferences=prefs,
        protect_engagement_threshold=float(data.get("protect_engagement_threshold", 0.62)),
        deep_flow_engagement_threshold=float(data.get("deep_flow_engagement_threshold", 0.82)),
        notes=str(data.get("notes") or ""),
    )
    profile.save(directory)
    return profile
