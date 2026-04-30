"""Bridge push integration layer for Trigger Panel."""

from __future__ import annotations

from typing import Any


def _load_push_func():
    try:
        from trigger_bridge.client import push_trigger_payload_from_env

        return push_trigger_payload_from_env
    except ModuleNotFoundError:
        return None


def push_to_bridge(trigger_payload: dict[str, Any]) -> dict[str, Any]:
    push_func = _load_push_func()
    if push_func is None:
        return {
            "timestamp": None,
            "action": "bridge_push",
            "status": "unavailable",
            "accepted": False,
            "stored": None,
            "project_id": None,
            "event_id": None,
            "bridge_status": "adapter_unavailable",
            "http_status": None,
            "error": "trigger_bridge_adapter_unavailable",
            "raw_response": None,
        }
    return push_func(trigger_payload)
