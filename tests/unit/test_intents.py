"""Intent router tests — Neuralink-ready control vocabulary."""

from __future__ import annotations

import pytest

from neural_flow_architect.core.intents import KNOWN_INTENTS, IntentRouter
from neural_flow_architect.core.session import SessionController
from neural_flow_architect.core.settings import Settings


@pytest.mark.asyncio
async def test_pause_intent(tmp_path) -> None:  # type: ignore[no-untyped-def]
    settings = Settings(adapter="simulator", data_dir=tmp_path)
    session = SessionController(settings)
    router = IntentRouter(session, min_confidence=0.5)
    result = await router.handle_raw("pause_agent", confidence=0.9)
    assert result.ok
    assert session.profile.preferences.agent_paused is True


@pytest.mark.asyncio
async def test_low_confidence_ignored(tmp_path) -> None:  # type: ignore[no-untyped-def]
    settings = Settings(adapter="simulator", data_dir=tmp_path)
    session = SessionController(settings)
    router = IntentRouter(session, min_confidence=0.5)
    result = await router.handle_raw("pause_agent", confidence=0.1)
    assert result.ok is False
    assert session.profile.preferences.agent_paused is False


@pytest.mark.asyncio
async def test_recipe_intent(tmp_path) -> None:  # type: ignore[no-untyped-def]
    settings = Settings(adapter="simulator", data_dir=tmp_path)
    session = SessionController(settings)
    result = await session.inject_intent("recipe_create", confidence=1.0)
    assert result["ok"] is True
    assert session._recipe == "create"


def test_known_intents_cover_core_controls() -> None:
    for name in ("pause_agent", "undo", "rest_mode", "recipe_study"):
        assert name in KNOWN_INTENTS
