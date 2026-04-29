"""Payload builders for Trigger Panel trigger categories."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from .contract import SCHEMA_VERSION, SOURCE, SOURCE_APP

SUPPORTED_EVENT_TYPES = (
    "page_view",
    "interaction_click",
    "intent_signal",
    "funnel_step",
    "dropoff_event",
    "error_event",
    "runtime_ping",
)

SUPPORTED_ACTION_TYPES = (
    "output_created",
    "output_delivered",
    "output_failed",
    "health_ok",
    "health_degraded",
    "health_error",
    "runtime_ping",
    "automation_started",
    "automation_succeeded",
    "automation_failed",
    "automation_requires_manual_intervention",
    "queue_item_created",
    "queue_item_started",
    "queue_item_completed",
    "queue_item_failed",
    "approval_requested",
    "approval_approved",
    "approval_rejected",
    "approval_expired",
    "flag_info",
    "flag_warning",
    "flag_error",
    "flag_resolved",
    "manager_signal_observed",
    "manager_decision_requested",
    "manager_decision_suggested",
    "manager_action_required",
    "runtime_registry_probe",
    "runtime_registry_available",
    "runtime_registry_missing",
    "runtime_registry_error",
    "library_archive_probe",
    "library_item_found",
    "library_item_missing",
    "library_archive_error",
)

FULL_PAYLOAD_FIELDS = (
    "event_id",
    "project_id",
    "event_type",
    "timestamp",
    "source",
    "origin",
    "session_id",
    "visitor_id",
    "page_url",
    "referrer",
    "user_agent",
    "device_type",
    "locale",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "action",
    "target",
    "value",
    "currency",
    "conversion",
    "revenue",
    "cost",
    "metadata",
    "test_mode",
    "operator_generated",
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _base_payload(
    *,
    project_id: str,
    metadata: dict | None,
    event_type: str | None = None,
    signal_type: str | None = None,
    category: str,
) -> dict:
    if not str(project_id).strip():
        raise ValueError("project_id_missing")

    clean_metadata = dict(metadata or {})
    clean_metadata["operator_generated"] = True
    clean_metadata.setdefault("context", "internal_operator_test")

    return {
        "schema_version": SCHEMA_VERSION,
        "source_app": SOURCE_APP,
        "source": SOURCE,
        "event_id": f"tp_{uuid4().hex}",
        "project_id": project_id,
        "event_type": event_type,
        "signal_type": signal_type,
        "timestamp": _utc_now_iso(),
        "metadata": clean_metadata,
        "test_mode": True,
        "operator_generated": True,
        "payload_category": category,
    }


def _finalize_payload(payload: dict) -> dict:
    payload["payload"] = {
        key: value
        for key, value in payload.items()
        if key not in {"schema_version", "source_app", "source", "payload"}
    }
    return payload


def build_runtime_event_payload(
    *,
    event_type: str,
    project_id: str,
    origin: str = "operator_panel",
    session_id: str | None = None,
    visitor_id: str | None = None,
    page_url: str | None = None,
    referrer: str | None = None,
    user_agent: str | None = None,
    device_type: str | None = None,
    locale: str | None = None,
    utm_source: str | None = None,
    utm_medium: str | None = None,
    utm_campaign: str | None = None,
    action: str | None = None,
    target: str | None = None,
    currency: str | None = None,
    metadata: dict | None = None,
) -> dict:
    if event_type not in SUPPORTED_EVENT_TYPES:
        raise ValueError("unsupported_event_type")
    payload = _base_payload(
        project_id=project_id,
        metadata=metadata,
        event_type=event_type,
        category="runtime_event",
    )
    payload.update(
        {
        "origin": origin,
        "session_id": session_id,
        "visitor_id": visitor_id,
        "page_url": page_url,
        "referrer": referrer,
        "user_agent": user_agent,
        "device_type": device_type,
        "locale": locale,
        "utm_source": utm_source,
        "utm_medium": utm_medium,
        "utm_campaign": utm_campaign,
        "action": action,
        "target": target,
        # Anti-fake baseline: leave economic/performance fields null.
        "value": None,
        "currency": currency,
        "conversion": None,
        "revenue": None,
        "cost": None,
        }
    )
    payload["payload"] = {key: payload.get(key) for key in FULL_PAYLOAD_FIELDS}
    return payload


def build_action_payload(*, action_type: str, project_id: str, metadata: dict | None = None) -> dict:
    if action_type not in SUPPORTED_ACTION_TYPES:
        raise ValueError("unsupported_action_type")

    now = _utc_now_iso()

    if action_type in {"output_created", "output_delivered", "output_failed"}:
        status = action_type.replace("output_", "")
        payload = _base_payload(
            project_id=project_id,
            metadata=metadata,
            event_type=action_type,
            category="output",
        )
        payload.update(
            {
                "output_id": f"out_{uuid4().hex}",
                "output_type": "operator_test_output",
                "output_status": status,
                "destination": None,
                "delivery_status": "failed" if action_type == "output_failed" else "pending",
                "error_message": "operator_test_delivery_failure" if action_type == "output_failed" else None,
            }
        )
        return _finalize_payload(payload)

    if action_type in {"health_ok", "health_degraded", "health_error", "runtime_ping"}:
        status_map = {
            "health_ok": "ok",
            "health_degraded": "degraded",
            "health_error": "error",
            "runtime_ping": "ok",
        }
        severity_map = {
            "health_ok": "info",
            "health_degraded": "warning",
            "health_error": "error",
            "runtime_ping": "info",
        }
        payload = _base_payload(
            project_id=project_id,
            metadata=metadata,
            event_type=action_type,
            category="health",
        )
        payload.update(
            {
                "health_status": status_map[action_type],
                "component": "trigger_panel",
                "severity": severity_map[action_type],
                "message": "operator_generated_test_signal",
            }
        )
        return _finalize_payload(payload)

    if action_type in {
        "automation_started",
        "automation_succeeded",
        "automation_failed",
        "automation_requires_manual_intervention",
    }:
        payload = _base_payload(
            project_id=project_id,
            metadata=metadata,
            event_type=action_type,
            category="automation_outcome",
        )
        requires_manual = action_type == "automation_requires_manual_intervention"
        payload.update(
            {
                "automation_id": f"auto_{uuid4().hex}",
                "automation_name": "trigger_panel_operator_flow",
                "outcome_status": action_type.replace("automation_", ""),
                "started_at": now,
                "completed_at": None if action_type == "automation_started" else now,
                "duration_ms": None,
                "error_message": (
                    "operator_test_automation_failure"
                    if action_type in {"automation_failed", "automation_requires_manual_intervention"}
                    else None
                ),
                "requires_manual_intervention": requires_manual,
            }
        )
        return _finalize_payload(payload)

    if action_type in {"queue_item_created", "queue_item_started", "queue_item_completed", "queue_item_failed"}:
        payload = _base_payload(
            project_id=project_id,
            metadata=metadata,
            event_type=action_type,
            category="queue",
        )
        completed = action_type in {"queue_item_completed", "queue_item_failed"}
        payload.update(
            {
                "queue_item_id": f"queue_{uuid4().hex}",
                "queue_name": "trigger_panel_operator_queue",
                "queue_status": action_type.replace("queue_item_", ""),
                "priority": "operator_test",
                "assigned_to": None,
                "started_at": now if action_type in {"queue_item_started", "queue_item_completed", "queue_item_failed"} else None,
                "completed_at": now if completed else None,
                "error_message": "operator_test_queue_failure" if action_type == "queue_item_failed" else None,
            }
        )
        return _finalize_payload(payload)

    if action_type in {"approval_requested", "approval_approved", "approval_rejected", "approval_expired"}:
        payload = _base_payload(
            project_id=project_id,
            metadata=metadata,
            event_type=action_type,
            category="approval",
        )
        payload.update(
            {
                "approval_id": f"approval_{uuid4().hex}",
                "approval_type": "operator_test_approval",
                "approval_status": action_type.replace("approval_", ""),
                "requested_by": None,
                "approved_by": None,
                "rejected_by": None,
                "reason": (
                    "operator_test_rejection_or_timeout"
                    if action_type in {"approval_rejected", "approval_expired"}
                    else None
                ),
            }
        )
        return _finalize_payload(payload)

    if action_type in {"flag_info", "flag_warning", "flag_error", "flag_resolved"}:
        severity = action_type.replace("flag_", "")
        payload = _base_payload(
            project_id=project_id,
            metadata=metadata,
            event_type=action_type,
            category="flag",
        )
        payload.update(
            {
                "flag_id": f"flag_{uuid4().hex}",
                "flag_type": "operator_test_flag",
                "severity": "info" if severity == "resolved" else severity,
                "flag_status": "resolved" if action_type == "flag_resolved" else "open",
                "message": "operator_generated_flag_signal",
                "resolved_at": now if action_type == "flag_resolved" else None,
            }
        )
        return _finalize_payload(payload)

    if action_type in {
        "manager_signal_observed",
        "manager_decision_requested",
        "manager_decision_suggested",
        "manager_action_required",
    }:
        payload = _base_payload(
            project_id=project_id,
            metadata=metadata,
            event_type=action_type,
            signal_type=action_type,
            category="manager_signal",
        )
        payload.update(
            {
                "manager_signal_id": f"mgr_{uuid4().hex}",
                "signal_type": action_type,
                "signal_status": action_type.replace("manager_", ""),
                "decision_required": action_type in {"manager_decision_requested", "manager_action_required"},
                "suggested_action": (
                    "operator_review_requested" if action_type in {"manager_decision_suggested", "manager_action_required"} else None
                ),
                "confidence": None,
            }
        )
        return _finalize_payload(payload)

    if action_type in {
        "runtime_registry_probe",
        "runtime_registry_available",
        "runtime_registry_missing",
        "runtime_registry_error",
    }:
        payload = _base_payload(
            project_id=project_id,
            metadata=metadata,
            event_type=action_type,
            category="runtime_registry_probe",
        )
        payload.update(
            {
                "registry_probe_id": f"registry_{uuid4().hex}",
                "runtime_id": None,
                "registry_status": action_type.replace("runtime_registry_", ""),
                "lookup_key": "operator_test_runtime_lookup",
                "found": True if action_type == "runtime_registry_available" else False if action_type == "runtime_registry_missing" else None,
                "error_message": "operator_test_registry_error" if action_type == "runtime_registry_error" else None,
            }
        )
        if action_type == "runtime_registry_probe":
            payload["found"] = None
        return _finalize_payload(payload)

    payload = _base_payload(
        project_id=project_id,
        metadata=metadata,
        event_type=action_type,
        category="library_archive_probe",
    )
    payload.update(
        {
            "library_probe_id": f"library_{uuid4().hex}",
            "item_id": None,
            "item_type": "operator_test_item",
            "archive_status": action_type.replace("library_", "").replace("archive_", ""),
            "found": True if action_type == "library_item_found" else False if action_type == "library_item_missing" else None,
            "error_message": "operator_test_archive_error" if action_type == "library_archive_error" else None,
        }
    )
    if action_type == "library_archive_probe":
        payload["archive_status"] = "probe"
    return _finalize_payload(payload)
