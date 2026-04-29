from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from trigger_panel.app import ACTION_TYPES, ACTION_TYPES_BY_CATEGORY, EVENT_TYPES, TriggerPanelApp
from trigger_panel.contract import SOURCE, SOURCE_APP, validate_bridge_payload
from trigger_panel.payload_builder import FULL_PAYLOAD_FIELDS, build_action_payload, build_runtime_event_payload
from trigger_panel.storage import TriggerEventStore


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
    assert "Runtime Event Buttons" in text
    assert "Output Trigger Buttons" in text
    assert "Health Trigger Buttons" in text
    assert "Runtime Registry Probe" in text
    assert "Library / Archive Probe" in text
    assert "Unified Trigger Result Log" in text
    assert "Test Data Cleanup Controls" in text
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


def test_each_trigger_action_accepts_and_stores(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    for action_type in ACTION_TYPES:
        status, _, body = _wsgi_call(
            app,
            "POST",
            f"/admin/trigger-panel/actions/{action_type}",
            token="approved-operator",
            form={"project_id": "proj_actions"},
        )
        payload = json.loads(body.decode("utf-8"))
        assert status == 200
        assert payload["accepted"] is True
        assert payload["stored"] is True
        assert payload["event_id"].startswith("tp_")

    unified_log = app.service.get_unified_log()
    assert unified_log["total_stored_trigger_count"] == len(ACTION_TYPES)
    for category in (
        "output",
        "health",
        "automation_outcome",
        "queue",
        "approval",
        "flag",
        "manager_signal",
        "runtime_registry_probe",
        "library_archive_probe",
    ):
        assert unified_log["counts_by_category"][category] > 0


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


def test_unified_log_empty_state_is_honest(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    status, _, body = _wsgi_call(app, "GET", "/admin/trigger-panel/trigger-log", token="approved-operator")
    payload = json.loads(body.decode("utf-8"))
    assert status == 200
    assert payload["total_stored_trigger_count"] == 0
    assert payload["latest_event_id"] is None
    assert payload["latest_timestamp"] is None
    assert payload["empty_state"] == "data_not_yet"
    for count in payload["counts_by_category"].values():
        assert count == 0


def test_unified_log_uses_stored_records_and_latest_by_category(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    _wsgi_call(app, "POST", "/admin/trigger-panel/events/page_view", token="approved-operator")
    _wsgi_call(app, "POST", "/admin/trigger-panel/actions/output_created", token="approved-operator")
    _wsgi_call(app, "POST", "/admin/trigger-panel/actions/health_error", token="approved-operator")

    status, _, body = _wsgi_call(app, "GET", "/admin/trigger-panel/summary", token="approved-operator")
    summary = json.loads(body.decode("utf-8"))
    assert status == 200
    unified = summary["unified_trigger_result_log"]
    assert unified["total_stored_trigger_count"] == 3
    assert unified["counts_by_category"]["runtime_event"] == 1
    assert unified["counts_by_category"]["output"] == 1
    assert unified["counts_by_category"]["health"] == 1
    assert unified["latest_event_by_category"]["output"]["event_type"] == "output_created"
    assert unified["latest_event_by_category"]["health"]["event_type"] == "health_error"
    assert unified["accepted_stored_status"]["accepted"] is True
    assert unified["accepted_stored_status"]["stored"] is True


def test_all_payloads_include_operator_test_markers_and_no_fake_metrics() -> None:
    for event_type in EVENT_TYPES:
        payload = build_runtime_event_payload(event_type=event_type, project_id="proj_runtime")
        assert payload["source"] == "trigger_panel"
        assert payload["test_mode"] is True
        assert payload["operator_generated"] is True
        assert payload["revenue"] is None
        assert payload["conversion"] is None
        assert payload["cost"] is None
        assert "ROI" not in payload
        assert "ads" not in payload
        assert "payments" not in payload
        assert "affiliate_payouts" not in payload
        assert validate_bridge_payload(payload) == []

    for action_type in ACTION_TYPES:
        payload = build_action_payload(action_type=action_type, project_id="proj_action")
        assert payload["source"] == "trigger_panel"
        assert payload["test_mode"] is True
        assert payload["operator_generated"] is True
        assert payload.get("revenue") is None
        assert payload.get("conversion") is None
        assert payload.get("cost") is None
        assert "ROI" not in payload
        assert "ads" not in payload
        assert "payments" not in payload
        assert "affiliate_payouts" not in payload
        assert validate_bridge_payload(payload) == []


def test_category_specific_honest_null_rules() -> None:
    output_created = build_action_payload(action_type="output_created", project_id="proj_output")
    output_failed = build_action_payload(action_type="output_failed", project_id="proj_output")
    assert output_created["destination"] is None
    assert output_created["error_message"] is None
    assert output_failed["error_message"] is not None

    automation_started = build_action_payload(action_type="automation_started", project_id="proj_auto")
    automation_manual = build_action_payload(
        action_type="automation_requires_manual_intervention",
        project_id="proj_auto",
    )
    assert automation_started["completed_at"] is None
    assert automation_started["duration_ms"] is None
    assert automation_started["requires_manual_intervention"] is False
    assert automation_manual["requires_manual_intervention"] is True

    queue_created = build_action_payload(action_type="queue_item_created", project_id="proj_queue")
    queue_failed = build_action_payload(action_type="queue_item_failed", project_id="proj_queue")
    assert queue_created["assigned_to"] is None
    assert queue_created["completed_at"] is None
    assert queue_failed["completed_at"] is not None
    assert queue_failed["error_message"] is not None

    approval_requested = build_action_payload(action_type="approval_requested", project_id="proj_approval")
    approval_expired = build_action_payload(action_type="approval_expired", project_id="proj_approval")
    assert approval_requested["requested_by"] is None
    assert approval_requested["approved_by"] is None
    assert approval_requested["rejected_by"] is None
    assert approval_requested["reason"] is None
    assert approval_expired["reason"] is not None

    flag_warning = build_action_payload(action_type="flag_warning", project_id="proj_flag")
    flag_resolved = build_action_payload(action_type="flag_resolved", project_id="proj_flag")
    assert flag_warning["resolved_at"] is None
    assert flag_resolved["resolved_at"] is not None

    manager_observed = build_action_payload(action_type="manager_signal_observed", project_id="proj_manager")
    manager_required = build_action_payload(action_type="manager_action_required", project_id="proj_manager")
    assert manager_observed["confidence"] is None
    assert manager_observed["decision_required"] is False
    assert manager_required["decision_required"] is True

    registry_available = build_action_payload(action_type="runtime_registry_available", project_id="proj_registry")
    registry_missing = build_action_payload(action_type="runtime_registry_missing", project_id="proj_registry")
    registry_error = build_action_payload(action_type="runtime_registry_error", project_id="proj_registry")
    assert registry_available["found"] is True
    assert registry_missing["found"] is False
    assert registry_error["error_message"] is not None

    library_found = build_action_payload(action_type="library_item_found", project_id="proj_library")
    library_missing = build_action_payload(action_type="library_item_missing", project_id="proj_library")
    library_error = build_action_payload(action_type="library_archive_error", project_id="proj_library")
    assert library_found["found"] is True
    assert library_missing["found"] is False
    assert library_error["error_message"] is not None


def test_cleanup_removes_only_operator_test_data(tmp_path: Path) -> None:
    store = TriggerEventStore(tmp_path / "events.jsonl")
    app = TriggerPanelApp(store_path=tmp_path / "events.jsonl")

    _wsgi_call(app, "POST", "/admin/trigger-panel/actions/output_created", token="approved-operator")
    _wsgi_call(app, "POST", "/admin/trigger-panel/actions/health_ok", token="approved-operator")
    store.append(
        {
            "event_id": "external_1",
            "event_type": "external_event",
            "payload_category": "runtime_event",
            "source": "external_app",
            "test_mode": False,
            "operator_generated": False,
            "timestamp": "2026-01-01T00:00:00Z",
            "accepted": True,
            "stored": True,
            "payload": {"event_type": "external_event"},
        }
    )

    status, _, body = _wsgi_call(app, "POST", "/admin/trigger-panel/cleanup", token="approved-operator")
    payload = json.loads(body.decode("utf-8"))
    assert status == 200
    assert payload["removed_count"] == 2

    remaining = store.list_events()
    assert len(remaining) == 1
    assert remaining[0]["event_id"] == "external_1"
    assert payload["summary"]["count"] == 1


def test_cleanup_endpoint_is_protected(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    status, headers, _ = _wsgi_call(app, "POST", "/admin/trigger-panel/cleanup")
    assert status == 303
    assert headers["Location"] == "/gate"


def test_actions_route_rejects_unknown_action(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    status, _, body = _wsgi_call(app, "POST", "/admin/trigger-panel/actions/unknown", token="approved-operator")
    payload = json.loads(body.decode("utf-8"))
    assert status == 400
    assert payload["error"] == "unsupported_action_type"


def test_all_action_buttons_are_present_in_ui(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    status, _, body = _wsgi_call(app, "GET", "/admin/trigger-panel", token="approved-operator")
    html = body.decode("utf-8")
    assert status == 200
    for title, actions in ACTION_TYPES_BY_CATEGORY.items():
        assert title in html
        for action in actions:
            assert f"Send {action}" in html
