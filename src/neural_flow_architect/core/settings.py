"""Runtime settings — env + YAML defaults."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NFA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = "development"
    log_level: str = "INFO"

    local_only: bool = True
    allow_cloud_llm: bool = False
    data_dir: Path = Field(default_factory=lambda: Path("./data"))

    adapter: Literal["simulator", "brainflow", "neuralink_stub", "replay"] = "simulator"
    sample_rate_hz: float = 250.0
    channels: int = 8
    simulator_seed: int = 42

    brainflow_board_id: int = -1
    brainflow_serial_port: str = ""

    agent_mode: Literal["rules", "llm_local", "llm_cloud"] = "rules"
    explain_actions: bool = True
    require_confirm_for_high_impact: bool = True
    dry_run: bool = False
    agent_min_confidence: float = 0.45
    agent_min_quality: float = 0.35
    protect_engagement_threshold: float = 0.62
    deep_flow_engagement_threshold: float = 0.82

    iot_enabled: bool = False
    home_assistant_url: str = ""
    home_assistant_token: str = ""

    api_host: str = "127.0.0.1"
    api_port: int = 8741

    window_sec: float = 1.0
    hop_sec: float = 0.25
    loop_hz: float = 4.0

    def ensure_data_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "sessions").mkdir(exist_ok=True)
        (self.data_dir / "profiles").mkdir(exist_ok=True)
        (self.data_dir / "audit").mkdir(exist_ok=True)


def load_yaml_config(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or (_repo_root() / "configs" / "default.yaml")
    if not cfg_path.exists():
        return {}
    with cfg_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config root must be a mapping: {cfg_path}")
    return data


def _yaml_to_settings_kwargs(yaml_data: dict[str, Any]) -> dict[str, Any]:
    """Map nested YAML sections onto flat Settings fields."""
    out: dict[str, Any] = {}
    privacy = yaml_data.get("privacy") or {}
    signal = yaml_data.get("signal") or {}
    flow = yaml_data.get("flow") or {}
    agent = yaml_data.get("agent") or {}
    environment = yaml_data.get("environment") or {}
    adapter = yaml_data.get("adapter") or {}
    api = yaml_data.get("api") or {}

    if isinstance(privacy, dict):
        if "local_only" in privacy:
            out["local_only"] = privacy["local_only"]
        if "allow_cloud_llm" in privacy:
            out["allow_cloud_llm"] = privacy["allow_cloud_llm"]
    if isinstance(adapter, dict) and "name" in adapter:
        out["adapter"] = adapter["name"]
    if isinstance(signal, dict):
        for src, dst in (
            ("sample_rate_hz", "sample_rate_hz"),
            ("channels", "channels"),
            ("window_sec", "window_sec"),
            ("hop_sec", "hop_sec"),
        ):
            if src in signal:
                out[dst] = signal[src]
    if isinstance(flow, dict):
        for key in (
            "protect_engagement_threshold",
            "deep_flow_engagement_threshold",
        ):
            if key in flow:
                out[key] = flow[key]
    if isinstance(agent, dict):
        mapping = {
            "mode": "agent_mode",
            "dry_run": "dry_run",
            "explain_actions": "explain_actions",
            "min_confidence": "agent_min_confidence",
            "min_quality": "agent_min_quality",
            "require_confirm_for_high_impact": "require_confirm_for_high_impact",
        }
        for src, dst in mapping.items():
            if src in agent:
                out[dst] = agent[src]
    if isinstance(environment, dict) and "iot_enabled" in environment:
        out["iot_enabled"] = environment["iot_enabled"]
    if isinstance(api, dict):
        if "host" in api:
            out["api_host"] = api["host"]
        if "port" in api:
            out["api_port"] = api["port"]
    return out


def get_settings(config_path: Path | None = None) -> Settings:
    """Load YAML defaults, then apply environment / constructor overrides."""
    yaml_data = load_yaml_config(config_path)
    kwargs = _yaml_to_settings_kwargs(yaml_data)
    # BaseSettings still reads env vars with higher priority for unset constructor fields
    # when we pass YAML as defaults via model construction.
    return Settings(**kwargs)
