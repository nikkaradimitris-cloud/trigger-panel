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
            }
        return {
            "count": len(events),
            "last_event": events[-1],
            "status": "ok",
            "output": "stored",
        }
