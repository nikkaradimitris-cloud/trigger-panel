"""HTTP client for Bridge ingest endpoint."""

from __future__ import annotations

import json
import socket
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import BridgeConfig, load_bridge_config_from_env
from .payload_mapper import BridgePayloadMapError, map_trigger_payload


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _redact_api_key(value: str | None) -> str:
    if not value:
        return "<redacted>"
    clean = str(value)
    if len(clean) <= 8:
        return "<redacted>"
    return f"{clean[:4]}...{clean[-4:]}"


def _redact_text(text: str, api_key: str) -> str:
    if not api_key:
        return text
    return text.replace(api_key, _redact_api_key(api_key))


def _safe_json(value: Any, *, api_key: str) -> Any:
    if isinstance(value, dict):
        safe: dict[str, Any] = {}
        for key, item in value.items():
            if "api_key" in str(key).lower():
                safe[key] = "<redacted>"
                continue
            safe[key] = _safe_json(item, api_key=api_key)
        return safe
    if isinstance(value, list):
        return [_safe_json(item, api_key=api_key) for item in value]
    if isinstance(value, str):
        return _redact_text(value, api_key)
    return value


def _base_result(*, project_id: str, action: str, bridge_status: str) -> dict[str, Any]:
    return {
        "timestamp": _utc_now_iso(),
        "action": action,
        "status": "ok" if bridge_status == "accepted" else bridge_status,
        "accepted": bridge_status == "accepted",
        "stored": True if bridge_status == "accepted" else None,
        "project_id": project_id,
        "event_id": None,
        "bridge_status": bridge_status,
        "http_status": None,
        "error": None,
        "raw_response": None,
        "debug_outbound_body": None,
    }


class BridgeClient:
    def __init__(self, config: BridgeConfig) -> None:
        self.config = config

    def push(self, trigger_payload: dict[str, Any]) -> dict[str, Any]:
        result = _base_result(project_id=self.config.project_id, action="bridge_push", bridge_status="pending")
        try:
            bridge_payload = map_trigger_payload(trigger_payload, bridge_project_id=self.config.project_id)
        except BridgePayloadMapError as exc:
            result["status"] = "failed"
            result["bridge_status"] = "mapping_error"
            result["error"] = str(exc)
            return result

        result["debug_outbound_body"] = bridge_payload
        body = json.dumps(bridge_payload, ensure_ascii=True).encode("utf-8")
        request = Request(
            self.config.ingest_url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Bridge-Project-ID": self.config.project_id,
                "X-Bridge-API-Key": self.config.api_key,
            },
        )
        try:
            with urlopen(request, timeout=self.config.request_timeout_seconds) as response:
                http_status = int(response.status)
                raw_text = response.read().decode("utf-8")
            parsed = json.loads(raw_text) if raw_text else {}
            safe_raw = _safe_json(parsed, api_key=self.config.api_key)
            normalized = self._normalize_success(
                parsed=parsed,
                safe_raw=safe_raw,
                http_status=http_status,
                debug_outbound_body=bridge_payload,
            )
            return normalized
        except HTTPError as exc:
            raw_text = exc.read().decode("utf-8", errors="replace")
            parsed: Any
            try:
                parsed = json.loads(raw_text)
            except json.JSONDecodeError:
                parsed = {"body": _redact_text(raw_text, self.config.api_key)}
            safe_raw = _safe_json(parsed, api_key=self.config.api_key)
            return self._normalize_error(
                bridge_status="rejected",
                http_status=int(exc.code),
                error=parsed.get("error", "bridge_http_error") if isinstance(parsed, dict) else "bridge_http_error",
                safe_raw=safe_raw,
                debug_outbound_body=bridge_payload,
            )
        except (TimeoutError, socket.timeout):
            return self._normalize_error(
                bridge_status="request_failed",
                http_status=None,
                error="request_timeout",
                safe_raw={"error": "request_timeout"},
                debug_outbound_body=bridge_payload,
            )
        except URLError as exc:
            return self._normalize_error(
                bridge_status="request_failed",
                http_status=None,
                error=_redact_text(str(exc.reason), self.config.api_key),
                safe_raw={"error": "url_error"},
                debug_outbound_body=bridge_payload,
            )
        except Exception as exc:  # pragma: no cover - defensive fallback
            return self._normalize_error(
                bridge_status="request_failed",
                http_status=None,
                error=_redact_text(str(exc), self.config.api_key),
                safe_raw={"error": "unexpected_error"},
                debug_outbound_body=bridge_payload,
            )

    def _normalize_success(
        self,
        *,
        parsed: dict[str, Any],
        safe_raw: Any,
        http_status: int,
        debug_outbound_body: dict[str, Any],
    ) -> dict[str, Any]:
        status_text = str(parsed.get("status") or "").strip().lower()
        bridge_event = parsed.get("bridge_event") if isinstance(parsed.get("bridge_event"), dict) else {}
        runtime_event = parsed.get("runtime_event") if isinstance(parsed.get("runtime_event"), dict) else {}

        accepted = status_text == "accepted" and http_status < 400
        normalized = _base_result(
            project_id=str(parsed.get("project_id") or self.config.project_id),
            action="bridge_push",
            bridge_status="accepted" if accepted else "rejected",
        )
        normalized["status"] = "accepted" if accepted else "rejected"
        normalized["accepted"] = accepted
        normalized["stored"] = True if accepted else None
        normalized["event_id"] = runtime_event.get("id") or bridge_event.get("runtime_event_id")
        normalized["http_status"] = http_status
        normalized["raw_response"] = safe_raw
        normalized["debug_outbound_body"] = debug_outbound_body
        if not accepted:
            normalized["error"] = str(parsed.get("error") or "bridge_rejected")
        return normalized

    def _normalize_error(
        self,
        *,
        bridge_status: str,
        http_status: int | None,
        error: str,
        safe_raw: Any,
        debug_outbound_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized = _base_result(
            project_id=self.config.project_id,
            action="bridge_push",
            bridge_status=bridge_status,
        )
        normalized["status"] = "rejected" if bridge_status == "rejected" else "failed"
        normalized["accepted"] = False
        normalized["stored"] = False if bridge_status == "rejected" else None
        normalized["http_status"] = http_status
        normalized["error"] = _redact_text(error, self.config.api_key)
        normalized["raw_response"] = safe_raw
        normalized["debug_outbound_body"] = debug_outbound_body
        return normalized


def not_configured_result() -> dict[str, Any]:
    return {
        "timestamp": _utc_now_iso(),
        "action": "bridge_push",
        "status": "not_configured",
        "accepted": False,
        "stored": None,
        "project_id": None,
        "event_id": None,
        "bridge_status": "not_configured",
        "http_status": None,
        "error": "missing_bridge_env",
        "raw_response": None,
        "debug_outbound_body": None,
    }


def push_trigger_payload_from_env(trigger_payload: dict[str, Any]) -> dict[str, Any]:
    config = load_bridge_config_from_env()
    if config is None:
        return not_configured_result()
    client = BridgeClient(config)
    return client.push(trigger_payload)
