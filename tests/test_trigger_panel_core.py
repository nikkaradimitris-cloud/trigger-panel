from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from trigger_panel.app import EVENT_TYPES, TriggerPanelApp
from trigger_panel.contract import SOURCE, SOURCE_APP, validate_bridge_payload
from trigger_panel.payload_builder import FULL_PAYLOAD_FIELDS, build_runtime_event_payload


def _wsgi_call(app: TriggerPanelApp, method: str, path: str, *, token: str | None = None, form: dict[str, str] | None = None) -> tuple[int, dict[str, str], bytes]:
    body = urlencode(form or {}).encode("utf-8")
    environ: dict[str, Any] = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": io.BytesIO(body),
    }
    if token:
        environ["HTTP_X_OPERATOR_SESSION"] = token

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


def test_protected_route_redirects_without_session(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    status, headers, _ = _wsgi_call(app, "GET", "/admin/trigger-panel")
    assert status == 303
    assert headers["Location"] == "/gate"


def test_protected_route_renders_shell_with_session(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    status, _, body = _wsgi_call(app, "GET", "/admin/trigger-panel", token="approved-operator")
    text = body.decode("utf-8")
    assert status == 200
    assert "Runtime Events" in text
    assert "Health" in text
    assert "Outputs" in text
    assert "Last Trigger Result" in text


def test_payload_builder_required_fields_and_contract_compatibility() -> None:
    payload = build_runtime_event_payload(event_type="page_view", project_id="proj_001")
    for field in FULL_PAYLOAD_FIELDS:
        assert field in payload
    assert payload["schema_version"] == "1.0.0"
    assert payload["source_app"] == SOURCE_APP
    assert payload["source"] == SOURCE
    assert payload["test_mode"] is True
    assert payload["operator_generated"] is True
    assert payload["metadata"]["operator_generated"] is True
    assert isinstance(payload["event_id"], str) and payload["event_id"].startswith("tp_")
    assert payload["timestamp"].endswith("Z")
    assert validate_bridge_payload(payload) == []


def test_payload_builder_null_handling_and_anti_fake_metrics() -> None:
    payload = build_runtime_event_payload(
        event_type="intent_signal",
        project_id="proj_002",
    )
    assert payload["value"] is None
    assert payload["conversion"] is None
    assert payload["revenue"] is None
    assert payload["cost"] is None
    assert payload["visitor_id"] is None
    assert payload["page_url"] is None
    assert validate_bridge_payload(payload) == []


def test_each_runtime_event_type_action_accepts_and_stores(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    for event_type in EVENT_TYPES:
        status, _, body = _wsgi_call(
            app,
            "POST",
            f"/admin/trigger-panel/events/{event_type}",
            token="approved-operator",
            form={"project_id": "proj_actions"},
        )
        payload = json.loads(body.decode("utf-8"))
        assert status == 200
        assert payload["accepted"] is True
        assert payload["stored"] is True
        assert payload["event_id"].startswith("tp_")

    summary = app.service.get_summary()
    assert summary["count"] == len(EVENT_TYPES)


def test_summary_proof_count_and_last_event_updates(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    empty_status, _, empty_body = _wsgi_call(app, "GET", "/admin/trigger-panel/summary", token="approved-operator")
    empty_summary = json.loads(empty_body.decode("utf-8"))
    assert empty_status == 200
    assert empty_summary["count"] == 0
    assert empty_summary["last_event"] is None
    assert empty_summary["output"] == "data_not_yet"

    _wsgi_call(
        app,
        "POST",
        "/admin/trigger-panel/events/page_view",
        token="approved-operator",
        form={"project_id": "proj_summary"},
    )
    _wsgi_call(
        app,
        "POST",
        "/admin/trigger-panel/events/error_event",
        token="approved-operator",
        form={"project_id": "proj_summary"},
    )

    status, _, body = _wsgi_call(app, "GET", "/admin/trigger-panel/summary", token="approved-operator")
    summary = json.loads(body.decode("utf-8"))
    assert status == 200
    assert summary["count"] == 2
    assert summary["status"] == "ok"
    assert summary["last_event"]["event_type"] == "error_event"
    assert summary["last_event"]["revenue"] is None
    assert summary["last_event"]["cost"] is None
    assert summary["last_event"]["conversion"] is None
    assert summary["last_event"]["value"] is None


def test_no_forbidden_reference_repos_modified() -> None:
    forbidden_paths = [
        Path(r"C:\Users\User\Desktop\subby-clean-v3"),
        Path(r"C:\Users\User\Desktop\mision-comand-conektor"),
        Path(r"C:\Users\User\Desktop\subby-universal-bridge"),
        Path(r"C:\Users\User\Desktop\subby-contract-reference"),
    ]
    for path in forbidden_paths:
        assert path.exists()
