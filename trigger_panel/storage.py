"""Durable local proof storage for Trigger Panel events."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class TriggerEventStore:
    """JSONL-backed event storage for deterministic local proof."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, payload: dict[str, Any]) -> None:
        line = json.dumps(payload, ensure_ascii=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def list_events(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        events: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for raw in handle:
                clean = raw.strip()
                if not clean:
                    continue
                parsed = json.loads(clean)
                if isinstance(parsed, dict):
                    events.append(parsed)
        return events

    def summary(self) -> dict[str, Any]:
        events = self.list_events()
        if not events:
            return {
                "count": 0,
                "last_event": None,
                "status": "empty",
                "output": "data_not_yet",
                "unified_trigger_result_log": self.unified_log(None, events),
            }
        return {
            "count": len(events),
            "last_event": events[-1],
            "status": "ok",
            "output": "stored",
            "unified_trigger_result_log": self.unified_log(None, events),
        }

    def unified_log(self, last_result: dict[str, Any] | None = None, events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        records = events if events is not None else self.list_events()
        categories = (
            "runtime_event",
            "output",
            "health",
            "automation_outcome",
            "queue",
            "approval",
            "flag",
            "manager_signal",
            "runtime_registry_probe",
            "library_archive_probe",
        )
        counts_by_category = {category: 0 for category in categories}
        latest_by_category: dict[str, dict[str, Any] | None] = {category: None for category in categories}

        for record in records:
            category = record.get("payload_category")
            if category in counts_by_category:
                counts_by_category[category] += 1
                latest_by_category[category] = record

        latest_record = records[-1] if records else None
        latest_result = last_result
        if latest_result is None and latest_record is not None:
            latest_result = {
                "event_id": latest_record.get("event_id"),
                "accepted": bool(latest_record.get("accepted")),
                "stored": bool(latest_record.get("stored")),
                "errors": [],
                "payload": latest_record,
            }

        return {
            "latest_trigger_result": latest_result
            or {
                "event_id": None,
                "accepted": False,
                "stored": False,
                "errors": [],
            },
            "total_stored_trigger_count": len(records),
            "counts_by_category": counts_by_category,
            "latest_event_by_category": latest_by_category,
            "accepted_stored_status": {
                "accepted": bool(latest_record.get("accepted")) if latest_record else False,
                "stored": bool(latest_record.get("stored")) if latest_record else False,
            },
            "latest_payload_type": latest_record.get("event_type") if latest_record else None,
            "latest_payload_category": latest_record.get("payload_category") if latest_record else None,
            "latest_timestamp": latest_record.get("timestamp") if latest_record else None,
            "latest_event_id": latest_record.get("event_id") if latest_record else None,
            "records": records,
            "empty_state": "data_not_yet" if not records else None,
        }

    def cleanup_operator_test_data(self) -> int:
        events = self.list_events()
        kept_events: list[dict[str, Any]] = []
        removed_count = 0
        for event in events:
            is_operator_test_record = (
                event.get("source") == "trigger_panel"
                and event.get("test_mode") is True
                and event.get("operator_generated") is True
            )
            if is_operator_test_record:
                removed_count += 1
            else:
                kept_events.append(event)

        with self.path.open("w", encoding="utf-8") as handle:
            for event in kept_events:
                handle.write(json.dumps(event, ensure_ascii=True) + "\n")

        return removed_count
