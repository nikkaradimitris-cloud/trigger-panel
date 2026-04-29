"""Minimal WSGI app for Trigger Panel core flows."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs

from .service import TriggerPanelService
from .storage import TriggerEventStore

EVENT_TYPES = (
    "page_view",
    "interaction_click",
    "intent_signal",
    "funnel_step",
    "dropoff_event",
    "error_event",
    "runtime_ping",
)

ACTION_TYPES_BY_CATEGORY = {
    "Output Trigger Buttons": (
        "output_created",
        "output_delivered",
        "output_failed",
    ),
    "Health Trigger Buttons": (
        "health_ok",
        "health_degraded",
        "health_error",
        "runtime_ping",
    ),
    "Automation Outcome Buttons": (
        "automation_started",
        "automation_succeeded",
        "automation_failed",
        "automation_requires_manual_intervention",
    ),
    "Queue Trigger Buttons": (
        "queue_item_created",
        "queue_item_started",
        "queue_item_completed",
        "queue_item_failed",
    ),
    "Approvals Trigger Buttons": (
        "approval_requested",
        "approval_approved",
        "approval_rejected",
        "approval_expired",
    ),
    "Flags Trigger Buttons": (
        "flag_info",
        "flag_warning",
        "flag_error",
        "flag_resolved",
    ),
    "Manager Signal Buttons": (
        "manager_signal_observed",
        "manager_decision_requested",
        "manager_decision_suggested",
        "manager_action_required",
    ),
    "Runtime Registry Probe": (
        "runtime_registry_probe",
        "runtime_registry_available",
        "runtime_registry_missing",
        "runtime_registry_error",
    ),
    "Library / Archive Probe": (
        "library_archive_probe",
        "library_item_found",
        "library_item_missing",
        "library_archive_error",
    ),
}

ACTION_TYPES = tuple(action for actions in ACTION_TYPES_BY_CATEGORY.values() for action in actions)


class TriggerPanelApp:
    def __init__(
        self,
        *,
        session_token: str = "approved-operator",
        store_path: Path | None = None,
    ) -> None:
        resolved_store_path = store_path or Path("data") / "trigger_events.jsonl"
        self.session_token = session_token
        self.service = TriggerPanelService(TriggerEventStore(resolved_store_path))

    def __call__(self, environ, start_response):  # type: ignore[no-untyped-def]
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "/")

        if path == "/gate":
            return self._respond_html(start_response, "<h1>Operator Gate</h1><p>Session required.</p>")

        if path == "/admin/trigger-panel":
            if not self._authorized(environ):
                return self._redirect(start_response, "/gate")
            return self._shell(start_response)

        if path.startswith("/admin/trigger-panel/events/") and method == "POST":
            if not self._authorized(environ):
                return self._redirect(start_response, "/gate")
            event_type = path.rsplit("/", 1)[-1]
            return self._trigger_event(environ, start_response, event_type)

        if path.startswith("/admin/trigger-panel/actions/") and method == "POST":
            if not self._authorized(environ):
                return self._redirect(start_response, "/gate")
            action_type = path.rsplit("/", 1)[-1]
            return self._trigger_action(environ, start_response, action_type)

        if path == "/admin/trigger-panel/summary":
            if not self._authorized(environ):
                return self._redirect(start_response, "/gate")
            return self._summary(start_response)

        if path == "/admin/trigger-panel/trigger-log":
            if not self._authorized(environ):
                return self._redirect(start_response, "/gate")
            return self._unified_log(start_response)

        if path == "/admin/trigger-panel/cleanup" and method == "POST":
            if not self._authorized(environ):
                return self._redirect(start_response, "/gate")
            return self._cleanup(start_response)

        return self._respond_json(start_response, 404, {"error": "not_found"})

    def _authorized(self, environ) -> bool:  # type: ignore[no-untyped-def]
        token = environ.get("HTTP_X_OPERATOR_SESSION")
        return token == self.session_token

    def _shell(self, start_response):  # type: ignore[no-untyped-def]
        last_result = self.service.last_result or {
            "event_id": None,
            "accepted": False,
            "stored": False,
            "errors": [],
        }
        buttons = "\n".join(
            [
                "<form method='post' action='/admin/trigger-panel/events/{event}'>"
                "<button type='submit'>Send {event}</button></form>".format(event=event)
                for event in EVENT_TYPES
            ]
        )
        runtime_buttons = "\n".join(
            [
                "<form method='post' action='/admin/trigger-panel/events/{event}'>"
                "<button type='submit'>Send {event}</button></form>".format(event=event)
                for event in EVENT_TYPES
            ]
        )
        action_sections = "\n".join(
            [
                "<section><h2>{title}</h2>{buttons}</section>".format(
                    title=title,
                    buttons="\n".join(
                        [
                            "<form method='post' action='/admin/trigger-panel/actions/{action}'>"
                            "<button type='submit'>Send {action}</button></form>".format(action=action)
                            for action in actions
                        ]
                    ),
                )
                for title, actions in ACTION_TYPES_BY_CATEGORY.items()
            ]
        )

        html = f"""
        <h1>Trigger Panel</h1>
        <section><h2>Runtime Event Buttons</h2>{runtime_buttons}</section>
        {action_sections}
        <section>
            <h2>Unified Trigger Result Log</h2>
            <p>Local/operator proof at <code>/admin/trigger-panel/summary</code> and <code>/admin/trigger-panel/trigger-log</code>.</p>
        </section>
        <section>
            <h2>Test Data Cleanup Controls</h2>
            <form method='post' action='/admin/trigger-panel/cleanup'>
                <button type='submit'>Run cleanup_operator_test_data</button>
            </form>
        </section>
        <section>
            <h2>Last Trigger Result</h2>
            <pre>{json.dumps(last_result, ensure_ascii=True)}</pre>
        </section>
        """
        return self._respond_html(start_response, html)

    def _trigger_event(self, environ, start_response, event_type: str):  # type: ignore[no-untyped-def]
        if event_type not in EVENT_TYPES:
            return self._respond_json(start_response, 400, {"error": "unsupported_event_type"})
        body = self._read_form_body(environ)
        project_id = body.get("project_id", ["proj_trigger_panel"])[0]
        result = self.service.trigger_event(
            event_type,
            project_id=project_id,
            context={"triggered_from": "runtime_event_button"},
        )
        return self._respond_json(
            start_response,
            200 if result["accepted"] else 422,
            {
                "event_id": result["event_id"],
                "accepted": result["accepted"],
                "stored": result["stored"],
                "errors": result["errors"],
            },
        )

    def _summary(self, start_response):  # type: ignore[no-untyped-def]
        return self._respond_json(start_response, 200, self.service.get_summary())

    def _unified_log(self, start_response):  # type: ignore[no-untyped-def]
        return self._respond_json(start_response, 200, self.service.get_unified_log())

    def _cleanup(self, start_response):  # type: ignore[no-untyped-def]
        return self._respond_json(start_response, 200, self.service.cleanup_operator_test_data())

    def _trigger_action(self, environ, start_response, action_type: str):  # type: ignore[no-untyped-def]
        if action_type not in ACTION_TYPES:
            return self._respond_json(start_response, 400, {"error": "unsupported_action_type"})
        body = self._read_form_body(environ)
        project_id = body.get("project_id", ["proj_trigger_panel"])[0]
        result = self.service.trigger_action(
            action_type,
            project_id=project_id,
            context={"triggered_from": "operator_action_button"},
        )
        return self._respond_json(
            start_response,
            200 if result["accepted"] else 422,
            {
                "event_id": result["event_id"],
                "accepted": result["accepted"],
                "stored": result["stored"],
                "errors": result["errors"],
            },
        )

    @staticmethod
    def _read_form_body(environ) -> dict:  # type: ignore[no-untyped-def]
        try:
            length = int(environ.get("CONTENT_LENGTH", "0") or "0")
        except ValueError:
            length = 0
        body_bytes = environ["wsgi.input"].read(length) if length > 0 else b""
        return parse_qs(body_bytes.decode("utf-8")) if body_bytes else {}

    @staticmethod
    def _respond_json(start_response, status_code: int, payload: dict):  # type: ignore[no-untyped-def]
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        start_response(
            f"{status_code} {'OK' if status_code < 400 else 'ERROR'}",
            [("Content-Type", "application/json"), ("Content-Length", str(len(body)))],
        )
        return [body]

    @staticmethod
    def _respond_html(start_response, html: str):  # type: ignore[no-untyped-def]
        body = html.encode("utf-8")
        start_response(
            "200 OK",
            [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(body)))],
        )
        return [body]

    @staticmethod
    def _redirect(start_response, location: str):  # type: ignore[no-untyped-def]
        start_response("303 SEE OTHER", [("Location", location), ("Content-Length", "0")])
        return [b""]
