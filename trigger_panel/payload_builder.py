"""Runtime event payload builder for Trigger Panel."""

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
    if not str(project_id).strip():
        raise ValueError("project_id_missing")

    clean_metadata = dict(metadata or {})
    clean_metadata["operator_generated"] = True
    clean_metadata.setdefault("context", "internal_operator_test")

    payload = {
        "schema_version": SCHEMA_VERSION,
        "source_app": SOURCE_APP,
        "event_id": f"tp_{uuid4().hex}",
        "project_id": project_id,
        "event_type": event_type,
        "timestamp": _utc_now_iso(),
        "source": SOURCE,
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
        "metadata": clean_metadata,
        "test_mode": True,
        "operator_generated": True,
    }

    # Bridge-required object field; keep operator payload nested and complete.
    payload["payload"] = {key: payload.get(key) for key in FULL_PAYLOAD_FIELDS}
    return payload
