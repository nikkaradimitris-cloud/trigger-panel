"""Universal Bridge compatibility helpers for Trigger Panel runtime events."""

from __future__ import annotations

from datetime import datetime
from typing import Any

SCHEMA_VERSION = "1.0.0"
SOURCE_APP = "trigger_panel"
SOURCE = "trigger_panel"

REQUIRED_FIELDS = (
    "schema_version",
    "source_app",
    "source",
    "project_id",
    "timestamp",
    "test_mode",
    "payload",
)


def is_valid_iso_timestamp(value: str) -> bool:
    """Return True for machine-readable ISO timestamps."""
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def validate_bridge_payload(payload: dict[str, Any]) -> list[str]:
    """Validate strict Trigger Panel + Universal Bridge baseline fields."""
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in payload:
            errors.append(f"missing required field: {field}")

    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("unsupported schema_version")
    if payload.get("source_app") != SOURCE_APP:
        errors.append("source_app must be trigger_panel")
    if payload.get("source") != SOURCE:
        errors.append("source must be trigger_panel")
    if payload.get("test_mode") is not True:
        errors.append("test_mode must be true")
    if payload.get("operator_generated") is not True:
        errors.append("operator_generated must be true")

    if not payload.get("event_type") and not payload.get("signal_type"):
        errors.append("event_type or signal_type is required")

    timestamp = payload.get("timestamp")
    if not isinstance(timestamp, str) or not is_valid_iso_timestamp(timestamp):
        errors.append("invalid timestamp format")

    if not isinstance(payload.get("payload"), dict):
        errors.append("payload must be an object")

    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        errors.append("metadata must be an object")
    elif metadata.get("operator_generated") is not True:
        errors.append("metadata.operator_generated must be true")

    # Strict anti-fake rule for operator test triggers.
    for metric_field in ("revenue", "cost", "conversion", "value"):
        if payload.get(metric_field) is not None:
            errors.append(f"{metric_field} must be null for operator test events")

    return errors
