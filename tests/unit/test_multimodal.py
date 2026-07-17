"""Multimodal keyboard/voice parsing tests."""

from neural_flow_architect.core.multimodal import (
    parse_keyboard,
    parse_voice_text,
    keymap_for_ui,
)


def test_keyboard_pause() -> None:
    cmd = parse_keyboard("KeyP")
    assert cmd is not None
    assert cmd.intent_type == "pause_agent"


def test_keyboard_ignores_modifiers() -> None:
    assert parse_keyboard("KeyP", meta=True) is None


def test_voice_rest() -> None:
    cmd = parse_voice_text("please rest mode now")
    assert cmd is not None
    assert cmd.intent_type == "rest_mode"


def test_voice_unknown() -> None:
    assert parse_voice_text("what's for dinner") is None


def test_keymap_for_ui() -> None:
    keys = keymap_for_ui()
    assert any(k["intent"] == "undo" for k in keys)
