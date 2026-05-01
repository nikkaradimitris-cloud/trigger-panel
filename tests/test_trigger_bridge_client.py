from __future__ import annotations

import io
import json
import socket
from typing import Any
from urllib.error import HTTPError

import pytest

from trigger_bridge.client import BridgeClient, push_trigger_payload_from_env
from trigger_bridge.config import BridgeConfig, DEFAULT_REQUEST_TIMEOUT_SECONDS
from trigger_bridge.payload_mapper import BridgePayloadMapError, map_trigger_payload
from trigger_panel.payload_builder import build_runtime_event_payload


def _bridge_config() -> BridgeConfig:
    return BridgeConfig(
        base_url="https://manager.subby.cloud",
        project_id="bridge_oz930lsxmdku",
        api_key="sbk_live_super_secret_key",
    )


def _assert_debug_outbound_shape(debug_outbound_body: dict[str, Any]) -> None:
    required_top_level_fields = {
        "schema_version",
        "source_app",
        "source",
        "project_id",
        "timestamp",
        "signal_type",
        "test_mode",
        "operator_generated",
        "payload",
    }
    assert isinstance(debug_outbound_body, dict)
    assert required_top_level_fields.issubset(set(debug_outbound_body.keys()))


def test_page_view_mapper_produces_required_bridge_body_shape() -> None:
    trigger_payload = build_runtime_event_payload(event_type="page_view", project_id="local_project_1")
    outbound = map_trigger_payload(trigger_payload, bridge_project_id="bridge_oz930lsxmdku")

    assert outbound["schema_version"] == "1.0"
    assert outbound["source_app"] == "Trigger Panel Core Live Final"
    assert outbound["source"] == "trigger_panel"
    assert outbound["project_id"] == "bridge_oz930lsxmdku"
    assert isinstance(outbound["timestamp"], str) and outbound["timestamp"].strip()
    assert outbound["signal_type"] == "page_view"
    assert outbound["test_mode"] is True
    assert outbound["operator_generated"] is True
    assert isinstance(outbound["payload"], dict)
    assert outbound["payload"]["source"] == "trigger_panel"
    assert outbound["payload"]["project_id"] == "bridge_oz930lsxmdku"
    assert outbound["payload"]["signal_type"] == "page_view"
    assert "local_project_1" not in json.dumps(outbound)


def test_mapper_overrides_nested_payload_project_id_with_bridge_project_id() -> None:
    trigger_payload = build_runtime_event_payload(event_type="page_view", project_id="local_project_1")
    outbound = map_trigger_payload(trigger_payload, bridge_project_id="bridge_oz930lsxmdku")

    assert outbound["project_id"] == "bridge_oz930lsxmdku"
    assert outbound["source"] == "trigger_panel"
    assert outbound["payload"]["source"] == "trigger_panel"
    assert outbound["payload"]["project_id"] == "bridge_oz930lsxmdku"
    assert "local_project_1" not in json.dumps(outbound)


def test_mapper_rejects_empty_signal_type() -> None:
    trigger_payload = {
        "source": "trigger_panel",
        "test_mode": True,
        "operator_generated": True,
        "signal_type": "   ",
        "event_type": "",
        "action": None,
        "payload": {},
    }
    with pytest.raises(BridgePayloadMapError, match="missing_signal_type"):
        map_trigger_payload(trigger_payload, bridge_project_id="bridge_oz930lsxmdku")


def test_mapper_rejects_fake_financial_or_ads_fields() -> None:
    trigger_payload = build_runtime_event_payload(event_type="page_view", project_id="local_project_1")
    trigger_payload["payload"]["ads"] = "active_campaign"
    with pytest.raises(BridgePayloadMapError, match="fake_value_not_allowed:ads"):
        map_trigger_payload(trigger_payload, bridge_project_id="bridge_oz930lsxmdku")


def test_client_sends_api_key_header_only_and_normalizes_accepted(monkeypatch) -> None:
    config = _bridge_config()
    client = BridgeClient(config)
    trigger_payload = build_runtime_event_payload(event_type="page_view", project_id="local_project_1")
    captured: dict[str, Any] = {}

    class _FakeResponse:
        def __init__(self) -> None:
            self.status = 200

        def read(self) -> bytes:
            return json.dumps(
                {
                    "status": "accepted",
                    "project_id": "bridge_oz930lsxmdku",
                    "runtime_event": {"id": "runtime_evt_1"},
                }
            ).encode("utf-8")

        def __enter__(self) -> "_FakeResponse":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

    def _fake_urlopen(request, timeout: int):
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return _FakeResponse()

    monkeypatch.setattr("trigger_bridge.client.urlopen", _fake_urlopen)
    result = client.push(trigger_payload)

    lower_headers = {str(k).lower(): str(v) for k, v in captured["headers"].items()}
    assert lower_headers["x-bridge-api-key"] == "sbk_live_super_secret_key"
    assert "sbk_live_super_secret_key" not in json.dumps(captured["body"])
    assert captured["body"]["signal_type"] == "page_view"
    assert captured["body"]["source"] == "trigger_panel"
    assert isinstance(captured["body"]["payload"], dict)
    assert captured["body"]["payload"]["source"] == "trigger_panel"
    assert captured["body"]["project_id"] == "bridge_oz930lsxmdku"
    assert captured["body"]["payload"]["project_id"] == "bridge_oz930lsxmdku"
    assert "local_project_1" not in json.dumps(captured["body"])
    assert result["debug_outbound_body"] == captured["body"]
    _assert_debug_outbound_shape(result["debug_outbound_body"])
    assert "sbk_live_super_secret_key" not in json.dumps(result["debug_outbound_body"])
    assert "x-bridge-api-key" not in json.dumps(result["debug_outbound_body"]).lower()

    assert result["status"] == "accepted"
    assert result["accepted"] is True
    assert result["bridge_status"] == "accepted"
    assert result["http_status"] == 200
    assert result["error"] is None


def test_client_uses_longer_default_request_timeout(monkeypatch) -> None:
    config = _bridge_config()
    client = BridgeClient(config)
    trigger_payload = build_runtime_event_payload(event_type="page_view", project_id="local_project_1")
    captured: dict[str, Any] = {}

    class _FakeResponse:
        def __init__(self) -> None:
            self.status = 200

        def read(self) -> bytes:
            return b'{"status":"accepted"}'

        def __enter__(self) -> "_FakeResponse":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

    def _fake_urlopen(request, timeout: float):
        captured["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setattr("trigger_bridge.client.urlopen", _fake_urlopen)
    result = client.push(trigger_payload)

    assert captured["timeout"] == DEFAULT_REQUEST_TIMEOUT_SECONDS
    assert captured["timeout"] > 10
    assert result["bridge_status"] == "accepted"
    assert result["http_status"] == 200


def test_env_bridge_request_timeout_overrides_default(monkeypatch) -> None:
    trigger_payload = build_runtime_event_payload(event_type="page_view", project_id="local_project_1")
    captured: dict[str, Any] = {}

    class _FakeResponse:
        def __init__(self) -> None:
            self.status = 200

        def read(self) -> bytes:
            return b'{"status":"accepted"}'

        def __enter__(self) -> "_FakeResponse":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

    def _fake_urlopen(request, timeout: float):
        captured["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setenv("BRIDGE_BASE_URL", "https://manager.subby.cloud")
    monkeypatch.setenv("BRIDGE_PROJECT_ID", "bridge_oz930lsxmdku")
    monkeypatch.setenv("BRIDGE_API_KEY", "sbk_live_super_secret_key")
    monkeypatch.setenv("BRIDGE_REQUEST_TIMEOUT_SECONDS", "25")
    monkeypatch.setattr("trigger_bridge.client.urlopen", _fake_urlopen)

    result = push_trigger_payload_from_env(trigger_payload)

    assert captured["timeout"] == 25.0
    assert result["bridge_status"] == "accepted"
    assert result["http_status"] == 200


def test_invalid_env_bridge_request_timeout_falls_back_safely(monkeypatch) -> None:
    trigger_payload = build_runtime_event_payload(event_type="page_view", project_id="local_project_1")
    captured: dict[str, Any] = {}

    class _FakeResponse:
        def __init__(self) -> None:
            self.status = 200

        def read(self) -> bytes:
            return b'{"status":"accepted"}'

        def __enter__(self) -> "_FakeResponse":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

    def _fake_urlopen(request, timeout: float):
        captured["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setenv("BRIDGE_BASE_URL", "https://manager.subby.cloud")
    monkeypatch.setenv("BRIDGE_PROJECT_ID", "bridge_oz930lsxmdku")
    monkeypatch.setenv("BRIDGE_API_KEY", "sbk_live_super_secret_key")
    monkeypatch.setenv("BRIDGE_REQUEST_TIMEOUT_SECONDS", "not_a_number")
    monkeypatch.setattr("trigger_bridge.client.urlopen", _fake_urlopen)

    result = push_trigger_payload_from_env(trigger_payload)

    assert captured["timeout"] == DEFAULT_REQUEST_TIMEOUT_SECONDS
    assert result["bridge_status"] == "accepted"
    assert result["http_status"] == 200


def test_client_normalizes_500_bridge_api_internal_error(monkeypatch) -> None:
    config = _bridge_config()
    client = BridgeClient(config)
    trigger_payload = build_runtime_event_payload(event_type="page_view", project_id="local_project_1")

    def _fake_urlopen(request, timeout: int):
        raise HTTPError(
            url=config.ingest_url,
            code=500,
            msg="Internal Server Error",
            hdrs=None,
            fp=io.BytesIO(
                json.dumps(
                    {
                        "error": "bridge_api_internal_error",
                        "message": "bridge ingest failed",
                        "project_id": "bridge_oz930lsxmdku",
                    }
                ).encode("utf-8")
            ),
        )

    monkeypatch.setattr("trigger_bridge.client.urlopen", _fake_urlopen)
    result = client.push(trigger_payload)

    assert result["status"] == "rejected"
    assert result["accepted"] is False
    assert result["bridge_status"] == "rejected"
    assert result["http_status"] == 500
    assert result["error"] == "bridge_api_internal_error"
    assert result["raw_response"]["message"] == "bridge ingest failed"
    _assert_debug_outbound_shape(result["debug_outbound_body"])
    assert "sbk_live_super_secret_key" not in json.dumps(result["debug_outbound_body"])
    assert "x-bridge-api-key" not in json.dumps(result["debug_outbound_body"]).lower()


def test_client_normalizes_request_timeout_safely(monkeypatch) -> None:
    config = _bridge_config()
    client = BridgeClient(config)
    trigger_payload = build_runtime_event_payload(event_type="page_view", project_id="local_project_1")

    def _fake_urlopen(request, timeout: float):
        raise socket.timeout("The read operation timed out")

    monkeypatch.setattr("trigger_bridge.client.urlopen", _fake_urlopen)
    result = client.push(trigger_payload)

    assert result["status"] == "failed"
    assert result["accepted"] is False
    assert result["bridge_status"] == "request_failed"
    assert result["http_status"] is None
    assert result["error"] == "request_timeout"
    assert result["raw_response"] == {"error": "request_timeout"}
    _assert_debug_outbound_shape(result["debug_outbound_body"])
    assert "sbk_live_super_secret_key" not in json.dumps(result)
