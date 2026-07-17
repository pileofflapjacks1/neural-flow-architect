"""Multimodal control bridge — keyboard shortcuts and voice phrases → intents.

All paths share IntentRouter so implant intents, UI, keyboard, and voice
remain consistent for Neuralink-class users.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Keyboard shortcuts (UI + documented for OS accessibility tools)
DEFAULT_KEYMAP: dict[str, str] = {
    "KeyP": "pause_agent",  # also toggled in UI
    "KeyU": "undo",
    "KeyR": "rest_mode",
    "KeyS": "start_session",
    "KeyX": "stop_session",
    "KeyY": "label_flow_yes",
    "KeyN": "label_flow_no",
    "Digit1": "recipe_study",
    "Digit2": "recipe_create",
    "Digit3": "recipe_rest",
    "Digit4": "recipe_social",
    "Slash": "why",
    "KeyH": "help",
    "KeyF": "resume_agent",
}


# Spoken / typed phrases (local STT can feed this later)
_VOICE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(pause|stop architect|stop co-?pilot)\b", re.I), "pause_agent"),
    (re.compile(r"\b(resume|continue architect|start architect)\b", re.I), "resume_agent"),
    (re.compile(r"\b(undo|go back|reverse)\b", re.I), "undo"),
    (re.compile(r"\b(rest|rest mode|i'?m tired|wind down)\b", re.I), "rest_mode"),
    (re.compile(r"\b(start session|begin session)\b", re.I), "start_session"),
    (re.compile(r"\b(stop session|end session)\b", re.I), "stop_session"),
    (re.compile(r"\b(i felt in flow|felt in flow|in the zone)\b", re.I), "label_flow_yes"),
    (re.compile(r"\b(not in flow|not really|out of flow)\b", re.I), "label_flow_no"),
    (re.compile(r"\b(study mode|focus mode)\b", re.I), "recipe_study"),
    (re.compile(r"\b(creative|create mode)\b", re.I), "recipe_create"),
    (re.compile(r"\b(social mode|messages)\b", re.I), "recipe_social"),
    (re.compile(r"\b(why|explain)\b", re.I), "why"),
    (re.compile(r"\b(help)\b", re.I), "help"),
]


@dataclass(frozen=True)
class ParsedCommand:
    intent_type: str
    source: str  # keyboard | voice | text
    raw: str
    confidence: float = 1.0


def keymap_for_ui() -> list[dict[str, str]]:
    """Human-readable shortcut list for the companion UI."""
    labels = {
        "pause_agent": "Pause Architect",
        "resume_agent": "Resume Architect",
        "undo": "Undo",
        "rest_mode": "Rest mode",
        "start_session": "Start session",
        "stop_session": "Stop session",
        "label_flow_yes": "Felt in flow",
        "label_flow_no": "Not in flow",
        "recipe_study": "Study recipe",
        "recipe_create": "Create recipe",
        "recipe_rest": "Rest recipe",
        "recipe_social": "Social recipe",
        "why": "Why?",
        "help": "Help",
    }
    out: list[dict[str, str]] = []
    for code, intent in DEFAULT_KEYMAP.items():
        key = code.replace("Key", "").replace("Digit", "")
        if code == "Slash":
            key = "/"
        out.append(
            {
                "code": code,
                "key": key,
                "intent": intent,
                "label": labels.get(intent, intent),
            }
        )
    return out


def parse_keyboard(
    code: str, *, shift: bool = False, alt: bool = False, meta: bool = False
) -> ParsedCommand | None:
    """Map KeyboardEvent.code-style strings to intents. Prefer unmodified keys."""
    if shift or alt or meta:
        # Avoid fighting browser/OS chords; only plain keys
        return None
    intent = DEFAULT_KEYMAP.get(code)
    if not intent:
        return None
    return ParsedCommand(intent_type=intent, source="keyboard", raw=code, confidence=1.0)


def parse_voice_text(text: str) -> ParsedCommand | None:
    """Map free-text (from voice STT or typed command bar) to an intent."""
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        return None
    for pattern, intent in _VOICE_PATTERNS:
        if pattern.search(cleaned):
            return ParsedCommand(
                intent_type=intent,
                source="voice",
                raw=cleaned,
                confidence=0.9,
            )
    # Exact intent id fallback
    token = cleaned.lower().replace(" ", "_")
    from neural_flow_architect.core.intents import KNOWN_INTENTS

    if token in KNOWN_INTENTS:
        return ParsedCommand(intent_type=token, source="text", raw=cleaned, confidence=1.0)
    return None
