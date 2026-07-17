"""Local active-application context (optional, off by default).

Never sends window titles off-device. Used only to soft-tune recipes/policies
for multi-hour BCI computer use.
"""

from __future__ import annotations

import platform
import re
import subprocess
from dataclasses import dataclass
from typing import Any


@dataclass
class AppContext:
    app_name: str | None = None
    bundle_or_exe: str | None = None
    category: str = "unknown"  # study | create | social | system | unknown
    source: str = "none"

    def to_dict(self) -> dict[str, Any]:
        return {
            "app_name": self.app_name,
            "bundle_or_exe": self.bundle_or_exe,
            "category": self.category,
            "source": self.source,
        }


# Heuristic app → category map (extend freely; local only)
_STUDY = re.compile(
    r"code|cursor|vim|nvim|emacs|terminal|iterm|warp|sublime|pycharm|idea|"
    r"xcode|word|pages|obsidian|notion|zotero|preview|pdf|chrome|firefox|"
    r"safari|edge|brave|arc|reader",
    re.I,
)
_CREATE = re.compile(
    r"figma|sketch|photoshop|illustrator|affinity|blender|logic|garageband|"
    r"final cut|davinci|ableton|procreate|pixelmator|unity|godot",
    re.I,
)
_SOCIAL = re.compile(
    r"slack|discord|messages|mail|outlook|teams|zoom|facetime|telegram|"
    r"signal|whatsapp|twitter|x\.com|instagram|facebook|imessage",
    re.I,
)
_SYSTEM = re.compile(r"finder|explorer|system settings|activity monitor|dock", re.I)


def categorize_app(
    name: str | None,
    *,
    user_map: Any | None = None,
) -> str:
    """
    Categorize app name. Optional ``user_map`` is an AppCategoryMap instance
    checked first; built-in regexes remain as fallback.
    """
    if not name:
        return "unknown"
    if user_map is not None:
        custom = user_map.categorize(name, fallback="")
        if custom:
            return custom
    if _SOCIAL.search(name):
        return "social"
    if _CREATE.search(name):
        return "create"
    if _SYSTEM.search(name):
        return "system"
    if _STUDY.search(name):
        return "study"
    return "unknown"


def detect_active_app(*, enabled: bool = False) -> AppContext:
    """Best-effort foreground app detection. Safe no-op when disabled or unsupported."""
    if not enabled:
        return AppContext(source="disabled")
    system = platform.system().lower()
    try:
        if system == "darwin":
            return _macos_frontmost()
        if system == "linux":
            return _linux_frontmost()
        if system == "windows":
            return _windows_frontmost()
    except Exception:
        return AppContext(source=f"error:{system}")
    return AppContext(source=f"unsupported:{system}")


_USER_MAP: Any | None = None


def set_user_category_map(user_map: Any | None) -> None:
    """Inject AppCategoryMap used by detect_active_app (optional)."""
    global _USER_MAP
    _USER_MAP = user_map


def _macos_frontmost() -> AppContext:
    script = (
        'tell application "System Events" to get name of first application process '
        "whose frontmost is true"
    )
    proc = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=1.5,
        check=False,
    )
    name = (proc.stdout or "").strip() or None
    return AppContext(
        app_name=name,
        category=categorize_app(name, user_map=_USER_MAP),
        source="macos",
    )


def _linux_frontmost() -> AppContext:
    # xdotool if present
    proc = subprocess.run(
        ["xdotool", "getactivewindow", "getwindowname"],
        capture_output=True,
        text=True,
        timeout=1.5,
        check=False,
    )
    if proc.returncode != 0:
        return AppContext(source="linux-unavailable")
    name = (proc.stdout or "").strip() or None
    return AppContext(
        app_name=name, category=categorize_app(name, user_map=_USER_MAP), source="linux"
    )


def _windows_frontmost() -> AppContext:
    # PowerShell Get-Process foreground — best effort
    ps = (
        "Add-Type @'"
        "using System; using System.Runtime.InteropServices; "
        "public class F { [DllImport(\"user32.dll\")] public static extern IntPtr GetForegroundWindow(); "
        "[DllImport(\"user32.dll\")] public static extern int GetWindowText(IntPtr h, System.Text.StringBuilder t, int c); }"
        "'@; $h=[F]::GetForegroundWindow(); $t=New-Object System.Text.StringBuilder 256; "
        "[void][F]::GetWindowText($h,$t,256); $t.ToString()"
    )
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        capture_output=True,
        text=True,
        timeout=2.0,
        check=False,
    )
    name = (proc.stdout or "").strip() or None
    return AppContext(
        app_name=name, category=categorize_app(name, user_map=_USER_MAP), source="windows"
    )


def recipe_hint_for_category(category: str) -> str | None:
    return {
        "study": "study",
        "create": "create",
        "social": "social",
        "system": None,
        "unknown": None,
    }.get(category)


def recipe_suggestion(
    *,
    current_recipe: str,
    app_category: str,
    suggest_enabled: bool = True,
) -> dict[str, object] | None:
    """
    Soft suggestion when active app category disagrees with current recipe.

    Never auto-applies — UI/API surfaces suggestion for one-tap accept.
    """
    if not suggest_enabled:
        return None
    hint = recipe_hint_for_category(app_category)
    if not hint or hint == current_recipe:
        return None
    return {
        "suggested_recipe": hint,
        "from_category": app_category,
        "current_recipe": current_recipe,
        "message": (
            f"You seem to be in a {app_category} app — switch recipe to {hint}?"
        ),
    }
