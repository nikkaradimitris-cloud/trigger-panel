"""Core Trigger Panel orchestration service."""

from __future__ import annotations

from typing import Any

from .contract import validate_bridge_payload
from .payload_builder import build_runtime_event_payload
from .storage import TriggerEventStore


class TriggerPanelService:
    def __init__(self, store: TriggerEventStore, default_project_id: str = "proj_trigger_panel") -> None:
        self.store = store
        self.default_project_id = default_project_id
        self.last_result: dict[str, Any] | None = None

    def trigger_event(self, event_type: str, *, project_id: str | None = None, context: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = build_runtime_event_payload(
            event_type=event_type,
            project_id=project_id or self.default_project_id,
            metadata=context or {},
        )
        errors = validate_bridge_payload(payload)
        accepted = len(errors) == 0
        stored = False
        if accepted:
            self.store.append(payload)
            stored = True

        result = {
            "event_id": payload["event_id"],
            "accepted": accepted,
            "stored": stored,
            "errors": errors,
            "payload": payload,
        }
        self.last_result = result
        return result

    def get_summary(self) -> dict[str, Any]:
        return self.store.summary()
