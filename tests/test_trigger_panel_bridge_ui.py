from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from trigger_panel.app import EVENT_TYPES, TriggerPanelApp


def _wsgi_call(
    app: TriggerPanelApp,
    method: str,
    path: str,
    *,
    token: str | None = None,
    cookie: str | None = None,
    form: dict[str, str] | None = None,
    scheme: str = "http",
) -> tuple[int, dict[str, str], bytes]:
    body = urlencode(form or {}).encode("utf-8")
    environ: dict[str, Any] = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": io.BytesIO(body),
        "wsgi.url_scheme": scheme,
    }
    if token:
        environ["HTTP_X_OPERATOR_SESSION"] = token
    if cookie:
        environ["HTTP_COOKIE"] = cookie

    captured: dict[str, Any] = {"status": "500 ERROR", "headers": []}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        captured["status"] = status
        captured["headers"] = headers

    chunks = app(environ, start_response)
    response_body = b"".join(chunks)
    status_code = int(str(captured["status"]).split()[0])
    headers = {k: v for (k, v) in captured["headers"]}
    return status_code, headers, response_body


def _make_app(tmp_path: Path) -> TriggerPanelApp:
    return TriggerPanelApp(store_path=tmp_path / "events.jsonl")


def test_ui_renders_bridge_connection_section(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    status, _, body = _wsgi_call(app, "GET", "/admin/trigger-panel", token="approved-operator")
    html = body.decode("utf-8")
    assert status == 200
    assert "Bridge Connection Status" in html
    assert "BRIDGE_BASE_URL" in html


def test_runtime_buttons_still_exist(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    status, _, body = _wsgi_call(app, "GET", "/admin/trigger-panel", token="approved-operator")
    html = body.decode("utf-8")
    assert status == 200
    for event_type in EVENT_TYPES:
        assert f"Send {event_type}" in html


def test_ui_renders_required_sections(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    status, _, body = _wsgi_call(app, "GET", "/admin/trigger-panel", token="approved-operator")
    html = body.decode("utf-8")
    assert status == 200
    required_sections = (
        "Bridge Connection Status",
        "Runtime Events",
        "Outputs",
        "Health",
        "Automation Outcomes",
        "Queue",
        "Approvals",
        "Flags",
        "Manager Signals",
        "Runtime Registry Probe",
        "Library / Archive Probe",
        "Last Trigger Result",
        "Dashboard Visibility Check",
        "Disabled Advertising / Performance",
    )
    for section in required_sections:
        assert section in html


def test_browser_gate_session_flow_allows_cookie_access(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPERATOR_ACCESS_TOKEN", "live-operator-token")
    app = _make_app(tmp_path)

    gate_status, _, gate_body = _wsgi_call(app, "GET", "/gate")
    assert gate_status == 200
    assert "Operator Gate" in gate_body.decode("utf-8")

    status, headers, _ = _wsgi_call(
        app,
        "POST",
        "/gate",
        form={"operator_access_token": "live-operator-token"},
    )
    assert status == 303
    assert headers["Location"] == "/admin/trigger-panel"
    assert "Set-Cookie" in headers
    cookie = headers["Set-Cookie"].split(";", 1)[0]

    panel_status, _, panel_body = _wsgi_call(
        app,
        "GET",
        "/admin/trigger-panel",
        cookie=cookie,
    )
    assert panel_status == 200
    assert "Trigger Panel" in panel_body.decode("utf-8")


def test_unauthorized_browser_access_redirects_to_gate(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    status, headers, _ = _wsgi_call(app, "GET", "/admin/trigger-panel")
    assert status == 303
    assert headers["Location"] == "/gate"


def test_button_action_calls_bridge_push_layer_when_mocked(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    seen = {}

    def _bridge_pusher(payload: dict[str, Any]) -> dict[str, Any]:
        seen["signal_type"] = payload.get("signal_type") or payload.get("event_type") or payload.get("action")
        return {
            "timestamp": "2026-01-01T00:00:00Z",
            "action": "bridge_push",
            "status": "accepted",
            "accepted": True,
            "stored": True,
            "project_id": "bridge_1",
            "event_id": "runtime_1",
            "bridge_status": "accepted",
            "http_status": 200,
            "error": None,
            "raw_response": {"status": "accepted"},
        }

    app.service.bridge_pusher = _bridge_pusher
    status, _, body = _wsgi_call(
        app,
        "POST",
        "/admin/trigger-panel/events/page_view",
        token="approved-operator",
    )
    response = json.loads(body.decode("utf-8"))
    assert status == 200
    assert response["bridge_result"]["accepted"] is True
    assert seen["signal_type"] == "page_view"


def test_configured_bridge_env_calls_bridge_push_layer(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("BRIDGE_BASE_URL", "https://manager.subby.cloud")
    monkeypatch.setenv("BRIDGE_PROJECT_ID", "bridge_project_live")
    monkeypatch.setenv("BRIDGE_API_KEY", "sbk_live_key")
    app = _make_app(tmp_path)
    seen_calls: list[str] = []

    def _bridge_pusher(payload: dict[str, Any]) -> dict[str, Any]:
        seen_calls.append(str(payload.get("event_type") or payload.get("signal_type") or ""))
        return {
            "timestamp": "2026-01-01T00:00:00Z",
            "action": "bridge_push",
            "status": "accepted",
            "accepted": True,
            "stored": True,
            "project_id": "bridge_project_live",
            "event_id": "runtime_1",
            "bridge_status": "accepted",
            "http_status": 200,
            "error": None,
            "raw_response": {"status": "accepted"},
        }

    app.service.bridge_pusher = _bridge_pusher
    status, _, body = _wsgi_call(
        app,
        "POST",
        "/admin/trigger-panel/events/page_view",
        token="approved-operator",
    )
    response = json.loads(body.decode("utf-8"))
    assert status == 200
    assert response["bridge_result"]["bridge_status"] == "accepted"
    assert seen_calls == ["page_view"]


def test_missing_bridge_env_does_not_crash_and_shows_not_configured(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("BRIDGE_PROJECT_ID", raising=False)
    monkeypatch.delenv("BRIDGE_API_KEY", raising=False)
    app = _make_app(tmp_path)

    status, _, body = _wsgi_call(
        app,
        "POST",
        "/admin/trigger-panel/events/runtime_ping",
        token="approved-operator",
    )
    response = json.loads(body.decode("utf-8"))
    assert status == 200
    assert response["bridge_result"]["bridge_status"] == "not_configured"

    ui_status, _, ui_body = _wsgi_call(app, "GET", "/admin/trigger-panel", token="approved-operator")
    assert ui_status == 200
    assert "bridge_status = not_configured" in ui_body.decode("utf-8")


def test_last_trigger_result_renders_accepted_result(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    app.service.last_result = {
        "event_id": "tp_accepted",
        "accepted": True,
        "stored": True,
        "errors": [],
        "bridge_result": {"bridge_status": "accepted", "accepted": True},
    }
    status, _, body = _wsgi_call(app, "GET", "/admin/trigger-panel", token="approved-operator")
    html = body.decode("utf-8")
    assert status == 200
    assert "bridge_status" in html
    assert "accepted" in html


def test_last_trigger_result_renders_rejected_error_result(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    app.service.last_result = {
        "event_id": "tp_rejected",
        "accepted": True,
        "stored": True,
        "errors": [],
        "bridge_result": {"bridge_status": "rejected", "error": "invalid_api_key"},
    }
    status, _, body = _wsgi_call(app, "GET", "/admin/trigger-panel", token="approved-operator")
    html = body.decode("utf-8")
    assert status == 200
    assert "bridge_status" in html
    assert "rejected" in html
    assert "invalid_api_key" in html


def test_last_trigger_result_renders_error_result(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    app.service.last_result = {
        "event_id": "tp_error",
        "accepted": False,
        "stored": False,
        "errors": ["invalid timestamp format"],
        "bridge_result": {"bridge_status": "request_failed", "error": "network_unreachable"},
    }
    status, _, body = _wsgi_call(app, "GET", "/admin/trigger-panel", token="approved-operator")
    html = body.decode("utf-8")
    assert status == 200
    assert "bridge_status" in html
    assert "request_failed" in html
    assert "network_unreachable" in html


def test_api_key_not_rendered_into_html(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("BRIDGE_API_KEY", "sbk_secret_should_not_render")
    app = _make_app(tmp_path)
    status, _, body = _wsgi_call(app, "GET", "/admin/trigger-panel", token="approved-operator")
    html = body.decode("utf-8")
    assert status == 200
    assert "sbk_secret_should_not_render" not in html


def test_signal_type_never_empty_for_bridge_push(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    seen_signals: list[str] = []

    def _bridge_pusher(payload: dict[str, Any]) -> dict[str, Any]:
        signal = payload.get("signal_type")
        seen_signals.append(str(signal or ""))
        return {
            "timestamp": "2026-01-01T00:00:00Z",
            "action": "bridge_push",
            "status": "accepted",
            "accepted": True,
            "stored": True,
            "project_id": "bridge_1",
            "event_id": "runtime_1",
            "bridge_status": "accepted",
            "http_status": 200,
            "error": None,
            "raw_response": None,
        }

    app.service.bridge_pusher = _bridge_pusher
    for event in EVENT_TYPES:
        status, _, _ = _wsgi_call(
            app,
            "POST",
            f"/admin/trigger-panel/events/{event}",
            token="approved-operator",
        )
        assert status == 200

    assert seen_signals
    assert all(signal.strip() for signal in seen_signals)


def test_disabled_advertising_performance_has_no_fake_buttons(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    status, _, body = _wsgi_call(app, "GET", "/admin/trigger-panel", token="approved-operator")
    html = body.decode("utf-8")
    assert status == 200
    assert "Disabled Advertising / Performance" in html
    assert "Send roi" not in html.lower()
    assert "Send revenue" not in html
    assert "Send payments" not in html
    assert "Send affiliate_payouts" not in html
