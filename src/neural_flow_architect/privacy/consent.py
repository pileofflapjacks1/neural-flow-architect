"""Granular, revocable consent manager."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ConsentScope(str, Enum):
    ACQUIRE = "acquire"
    PROCESS_REALTIME = "process_realtime"
    PERSIST_FEATURES = "persist_features"
    PERSIST_RAW = "persist_raw"
    AGENT_ACT = "agent_act"
    IOT_CONTROL = "iot_control"
    EXPORT = "export"
    OPTIONAL_LLM = "optional_llm"


# Safe defaults for local demo: process + act, no raw/cloud persistence
DEFAULT_GRANTS: dict[ConsentScope, bool] = {
    ConsentScope.ACQUIRE: True,
    ConsentScope.PROCESS_REALTIME: True,
    ConsentScope.PERSIST_FEATURES: False,
    ConsentScope.PERSIST_RAW: False,
    ConsentScope.AGENT_ACT: True,
    ConsentScope.IOT_CONTROL: False,
    ConsentScope.EXPORT: False,
    ConsentScope.OPTIONAL_LLM: False,
}


@dataclass
class ConsentRecord:
    scope: ConsentScope
    granted: bool
    changed_at: datetime
    note: str = ""


@dataclass
class ConsentManager:
    grants: dict[ConsentScope, bool] = field(
        default_factory=lambda: dict(DEFAULT_GRANTS)
    )
    history: list[ConsentRecord] = field(default_factory=list)

    def allows(self, scope: ConsentScope | str) -> bool:
        if isinstance(scope, str):
            scope = ConsentScope(scope)
        return bool(self.grants.get(scope, False))

    def set(self, scope: ConsentScope, granted: bool, note: str = "") -> None:
        self.grants[scope] = granted
        self.history.append(
            ConsentRecord(
                scope=scope,
                granted=granted,
                changed_at=datetime.utcnow(),
                note=note,
            )
        )

    def revoke_all(self) -> None:
        for scope in ConsentScope:
            self.set(scope, False, note="revoke_all")

    def as_dict(self) -> dict[str, bool]:
        return {s.value: self.grants.get(s, False) for s in ConsentScope}
