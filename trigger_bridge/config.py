"""Environment-backed Bridge adapter configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_INGEST_PATH = "/api/bridge/ingest"


@dataclass(frozen=True)
class BridgeConfig:
    base_url: str
    project_id: str
    api_key: str
    ingest_path: str = DEFAULT_INGEST_PATH

    @property
    def ingest_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/{self.ingest_path.lstrip('/')}"


def _clean_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    clean = value.strip()
    return clean or None


def load_bridge_config_from_env() -> BridgeConfig | None:
    base_url = _clean_env("BRIDGE_BASE_URL")
    project_id = _clean_env("BRIDGE_PROJECT_ID")
    api_key = _clean_env("BRIDGE_API_KEY")
    ingest_path = _clean_env("BRIDGE_INGEST_PATH") or DEFAULT_INGEST_PATH

    if not base_url or not project_id or not api_key:
        return None
    return BridgeConfig(
        base_url=base_url,
        project_id=project_id,
        api_key=api_key,
        ingest_path=ingest_path,
    )
