"""Trigger Bridge adapter package."""

from .client import push_trigger_payload_from_env
from .config import BridgeConfig
from .payload_mapper import BridgePayloadMapError, map_trigger_payload

__all__ = [
    "BridgeConfig",
    "BridgePayloadMapError",
    "map_trigger_payload",
    "push_trigger_payload_from_env",
]
