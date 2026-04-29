"""Core Trigger Panel orchestration service."""

from __future__ import annotations

from typing import Any

from .contract import validate_bridge_payload
from .payload_builder import build_action_payload, build_runtime_event_payload
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
        return self._validate_and_store(payload)

    def trigger_action(self, action_type: str, *, project_id: str | None = None, context: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = build_action_payload(
            action_type=action_type,
            project_id=project_id or self.default_project_id,
            metadata=context or {},
        )
        return self._validate_and_store(payload)

    def get_summary(self) -> dict[str, Any]:
        return self.store.summary()

    def get_unified_log(self) -> dict[str, Any]:
        return self.store.unified_log(self.last_result)

    def cleanup_operator_test_data(self) -> dict[str, Any]:
        removed_count = self.store.cleanup_operator_test_data()
        result = {
            "event_id": None,
            "accepted": True,
            "stored": False,
            "errors": [],
            "payload": None,
            "cleanup_removed_count": removed_count,
        }
        self.last_result = result
        return {
            "removed_count": removed_count,
            "cleanup_scope": {
                "source": "trigger_panel",
                "test_mode": True,
                "operator_generated": True,
            },
            "summary": self.get_summary(),
            "unified_log": self.get_unified_log(),
        }

    def _validate_and_store(self, payload: dict[str, Any]) -> dict[str, Any]:
        errors = validate_bridge_payload(payload)
        accepted = len(errors) == 0
        stored = False
        if accepted:
            payload["accepted"] = True
            payload["stored"] = True
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
