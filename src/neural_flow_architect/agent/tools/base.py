"""Tool protocol and registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from neural_flow_architect.core.types import ActionResult, ImpactLevel, WorldSnapshot


class Tool(Protocol):
    id: str
    impact: ImpactLevel
    description: str

    async def run(
        self, snapshot: WorldSnapshot, params: dict[str, Any], *, dry_run: bool
    ) -> ActionResult: ...


@dataclass
class ToolSpec:
    id: str
    impact: ImpactLevel
    description: str
    handler: Tool
    reversible: bool = True


@dataclass
class ToolRegistry:
    tools: dict[str, ToolSpec] = field(default_factory=dict)

    def register(self, tool: Tool, *, reversible: bool = True) -> None:
        self.tools[tool.id] = ToolSpec(
            id=tool.id,
            impact=tool.impact,
            description=tool.description,
            handler=tool,
            reversible=reversible,
        )

    def get(self, tool_id: str) -> ToolSpec | None:
        return self.tools.get(tool_id)

    def list_ids(self) -> list[str]:
        return sorted(self.tools.keys())
