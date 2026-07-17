"""BCI intent control channel — map high-level intents to co-pilot actions.

Designed for future implant SDKs that expose discrete intents (select, pause,
etc.). No raw neural decoding lives here — only named intent events.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from neural_flow_architect.core.types import IntentEvent

# Stable intent vocabulary for adapters (Neuralink-ready surface)
KNOWN_INTENTS = frozenset(
    {
        "pause_agent",
        "resume_agent",
        "undo",
        "rest_mode",
        "label_flow_yes",
        "label_flow_no",
        "recipe_study",
        "recipe_create",
        "recipe_rest",
        "recipe_social",
        "start_session",
        "stop_session",
        "why",  # surface last explanation — UI-only
        "help",
    }
)


@dataclass
class IntentActionResult:
    intent_type: str
    ok: bool
    message: str
    side_effects: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_type": self.intent_type,
            "ok": self.ok,
            "message": self.message,
            "side_effects": self.side_effects or {},
        }


class IntentSink(Protocol):
    """Session-facing handlers the router can call."""

    def set_paused(self, paused: bool) -> dict[str, Any]: ...

    def undo(self) -> dict[str, Any]: ...

    def rest_mode(self) -> dict[str, Any]: ...

    def set_recipe(self, recipe: str) -> dict[str, Any]: ...

    def label_flow(self, felt_in_flow: bool, note: str = "") -> dict[str, Any]: ...

    async def start(self, duration_sec: float | None = None) -> dict[str, Any]: ...

    async def stop(self) -> dict[str, Any]: ...


class IntentRouter:
    """
    Routes IntentEvent → control-plane actions.

    Confidence gate avoids accidental triggers from low-confidence decoder output.
    """

    def __init__(
        self,
        sink: IntentSink,
        *,
        min_confidence: float = 0.5,
        on_result: Callable[[IntentActionResult], None] | None = None,
    ) -> None:
        self.sink = sink
        self.min_confidence = min_confidence
        self.on_result = on_result
        self.last_result: IntentActionResult | None = None
        self.history: list[IntentActionResult] = []

    async def handle(self, event: IntentEvent) -> IntentActionResult:
        intent = event.intent_type.strip().lower()
        if event.confidence < self.min_confidence:
            result = IntentActionResult(
                intent_type=intent,
                ok=False,
                message=f"Ignored low-confidence intent ({event.confidence:.2f})",
            )
            return self._record(result)

        if intent not in KNOWN_INTENTS:
            result = IntentActionResult(
                intent_type=intent,
                ok=False,
                message=f"Unknown intent '{intent}'",
            )
            return self._record(result)

        result = await self._dispatch(intent, event.payload)
        return self._record(result)

    async def handle_raw(
        self,
        intent_type: str,
        confidence: float = 1.0,
        payload: dict[str, Any] | None = None,
    ) -> IntentActionResult:
        return await self.handle(
            IntentEvent(
                seq=0,
                timestamp_ns=0,
                intent_type=intent_type,
                payload=payload or {},
                confidence=confidence,
            )
        )

    async def _dispatch(self, intent: str, payload: dict[str, Any]) -> IntentActionResult:
        if intent == "pause_agent":
            out = self.sink.set_paused(True)
            return IntentActionResult(intent, True, "Architect paused", out)
        if intent == "resume_agent":
            out = self.sink.set_paused(False)
            return IntentActionResult(intent, True, "Architect resumed", out)
        if intent == "undo":
            out = self.sink.undo()
            return IntentActionResult(
                intent, bool(out.get("ok")), out.get("result", {}).get("message", "undo"), out
            )
        if intent == "rest_mode":
            out = self.sink.rest_mode()
            return IntentActionResult(intent, True, "Rest mode", out)
        if intent == "label_flow_yes":
            out = self.sink.label_flow(True, note=str(payload.get("note", "intent")))
            return IntentActionResult(intent, True, "Labeled: felt in flow", out)
        if intent == "label_flow_no":
            out = self.sink.label_flow(False, note=str(payload.get("note", "intent")))
            return IntentActionResult(intent, True, "Labeled: not in flow", out)
        if intent.startswith("recipe_"):
            recipe = intent.replace("recipe_", "", 1)
            out = self.sink.set_recipe(recipe)
            return IntentActionResult(intent, bool(out.get("ok")), f"Recipe {recipe}", out)
        if intent == "start_session":
            out = await self.sink.start()
            return IntentActionResult(intent, bool(out.get("ok")), out.get("message", "start"), out)
        if intent == "stop_session":
            out = await self.sink.stop()
            return IntentActionResult(intent, bool(out.get("ok")), out.get("message", "stop"), out)
        if intent in {"why", "help"}:
            return IntentActionResult(
                intent,
                True,
                "Open Why/Help in the companion UI — intent acknowledged",
                {"ui_hint": intent},
            )
        return IntentActionResult(intent, False, "Unhandled")

    def _record(self, result: IntentActionResult) -> IntentActionResult:
        self.last_result = result
        self.history.append(result)
        if len(self.history) > 50:
            self.history = self.history[-50:]
        if self.on_result is not None:
            self.on_result(result)
        return result
