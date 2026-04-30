"""Map Trigger Panel payloads to Bridge ingest contract."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class BridgePayloadMapError(ValueError):
    """Local mapping/validation failure before network calls."""


BLOCKED_FAKE_FIELDS = (
    "roi",
    "ad_spend",
    "ads",
    "payments",
    "payment_amount",
    "affiliate_payout",
    "affiliate_payouts",
    "ltv",
    "cac",
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _is_valid_iso_timestamp(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _ensure_required_markers(trigger_payload: dict[str, Any]) -> None:
    if trigger_payload.get("source") != "trigger_panel":
        raise BridgePayloadMapError("missing_source")
    if trigger_payload.get("test_mode") is not True:
        raise BridgePayloadMapError("missing_test_mode")
    if trigger_payload.get("operator_generated") is not True:
        raise BridgePayloadMapError("missing_operator_generated")


def _resolve_signal_type(trigger_payload: dict[str, Any]) -> str:
    for key in ("signal_type", "event_type", "action"):
        value = trigger_payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise BridgePayloadMapError("missing_signal_type")


def _enforce_null_honesty(trigger_payload: dict[str, Any]) -> None:
    for field in ("revenue", "cost", "conversion"):
        if trigger_payload.get(field) is not None:
            raise BridgePayloadMapError(f"field_must_be_null:{field}")

    if "value" in trigger_payload and trigger_payload.get("value") is not None:
        raise BridgePayloadMapError("field_must_be_null:value")

    payload_view = trigger_payload.get("payload")
    blocked_targets = [trigger_payload]
    if isinstance(payload_view, dict):
        blocked_targets.append(payload_view)

    for view in blocked_targets:
        for field in BLOCKED_FAKE_FIELDS:
            if field not in view:
                continue
            value = view.get(field)
            if value is None:
                continue
            text = str(value).strip().lower()
            if text in {"", "null", "none", "not_connected", "not_applicable", "empty"}:
                continue
            raise BridgePayloadMapError(f"fake_value_not_allowed:{field}")


def map_trigger_payload(trigger_payload: dict[str, Any], *, bridge_project_id: str) -> dict[str, Any]:
    if not isinstance(trigger_payload, dict):
        raise BridgePayloadMapError("payload_must_be_object")
    project_id = str(bridge_project_id or "").strip()
    if not project_id:
        raise BridgePayloadMapError("missing_project_id")

    _ensure_required_markers(trigger_payload)
    _enforce_null_honesty(trigger_payload)
    signal_type = _resolve_signal_type(trigger_payload)

    incoming_timestamp = trigger_payload.get("timestamp")
    if isinstance(incoming_timestamp, str) and incoming_timestamp.strip() and _is_valid_iso_timestamp(incoming_timestamp):
        timestamp = incoming_timestamp
    else:
        timestamp = _utc_now_iso()

    return {
        "schema_version": "1.0",
        "source_app": "subby-trigger-panel",
        "project_id": project_id,
        "timestamp": timestamp,
        "signal_type": signal_type,
        "payload": trigger_payload,
        "test_mode": True,
        "operator_generated": True,
    }
