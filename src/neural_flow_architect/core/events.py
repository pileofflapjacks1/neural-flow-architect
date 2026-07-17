"""In-process event bus for runtime components."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

Handler = Callable[[Any], Awaitable[None] | None]


class EventBus:
    """Simple asyncio-friendly pub/sub. Not a distributed bus."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)
        self._queue: asyncio.Queue[tuple[str, Any]] | None = None

    def subscribe(self, topic: str, handler: Handler) -> None:
        self._handlers[topic].append(handler)

    def unsubscribe(self, topic: str, handler: Handler) -> None:
        if handler in self._handlers[topic]:
            self._handlers[topic].remove(handler)

    async def publish(self, topic: str, payload: Any) -> None:
        for handler in list(self._handlers.get(topic, [])):
            result = handler(payload)
            if asyncio.iscoroutine(result) or isinstance(result, Awaitable):
                await result  # type: ignore[arg-type]

    async def publish_many(self, events: list[tuple[str, Any]]) -> None:
        for topic, payload in events:
            await self.publish(topic, payload)


# Well-known topics
TOPIC_FLOW = "flow.estimate"
TOPIC_STATE = "flow.state"
TOPIC_ACTION = "agent.action"
TOPIC_EXPLAIN = "agent.explain"
TOPIC_QUALITY = "signal.quality"
TOPIC_OVERRIDE = "agent.override"
