"""Browser-usable WSGI app for Trigger Panel operator flows."""

from __future__ import annotations

import hashlib
import hmac
import html
import json
import os
from pathlib import Path
from http.cookies import SimpleCookie
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
    "Outputs": (
        "output_created",
        "output_delivered",
        "output_failed",
    ),
    "Health": (
        "health_ok",
        "health_degraded",
        "health_error",
        "runtime_ping",
    ),
    "Automation Outcomes": (
        "automation_started",
        "automation_succeeded",
        "automation_failed",
        "automation_requires_manual_intervention",
    ),
    "Queue": (
        "queue_item_created",
        "queue_item_started",
        "queue_item_completed",
        "queue_item_failed",
    ),
    "Approvals": (
        "approval_requested",
        "approval_approved",
        "approval_rejected",
        "approval_expired",
    ),
    "Flags": (
        "flag_info",
        "flag_warning",
        "flag_error",
        "flag_resolved",
    ),
    "Manager Signals": (
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
COOKIE_NAME = "trigger_panel_session"
BRIDGE_DEFAULT_BASE_URL = "https://manager.subby.cloud"


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
            return self._gate(environ, start_response, method)

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
        if token == self.session_token:
            return True
        cookie_value = self._session_cookie_from_environ(environ)
        if not cookie_value:
            return False
        return hmac.compare_digest(cookie_value, self._session_cookie_value())

    def _operator_access_token(self) -> str:
        return str(os.getenv("OPERATOR_ACCESS_TOKEN", self.session_token) or "").strip() or self.session_token

    def _session_cookie_value(self) -> str:
        token = self._operator_access_token()
        digest_source = f"{token}:trigger-panel-session-v1".encode("utf-8")
        return hashlib.sha256(digest_source).hexdigest()

    @staticmethod
    def _session_cookie_from_environ(environ) -> str | None:  # type: ignore[no-untyped-def]
        raw_cookie = str(environ.get("HTTP_COOKIE", "") or "")
        if not raw_cookie:
            return None
        cookie = SimpleCookie()
        cookie.load(raw_cookie)
        morsel = cookie.get(COOKIE_NAME)
        if morsel is None:
            return None
        return morsel.value

    def _gate(self, environ, start_response, method: str):  # type: ignore[no-untyped-def]
        if method == "POST":
            body = self._read_form_body(environ)
            submitted = body.get("operator_access_token", [""])[0]
            if submitted and hmac.compare_digest(submitted, self._operator_access_token()):
                secure_cookie = str(environ.get("wsgi.url_scheme", "http")).lower() == "https"
                cookie_parts = [
                    f"{COOKIE_NAME}={self._session_cookie_value()}",
                    "Path=/",
                    "HttpOnly",
                    "SameSite=Lax",
                ]
                if secure_cookie:
                    cookie_parts.append("Secure")
                return self._redirect(
                    start_response,
                    "/admin/trigger-panel",
                    extra_headers=[("Set-Cookie", "; ".join(cookie_parts))],
                )
            return self._respond_html(start_response, self._gate_html(error_message="Invalid access token."), status_code=401)

        if self._authorized(environ):
            return self._redirect(start_response, "/admin/trigger-panel")
        return self._respond_html(start_response, self._gate_html())

    def _gate_html(self, error_message: str | None = None) -> str:
        error = f"<p class='error'>{html.escape(error_message)}</p>" if error_message else ""
        return f"""
        <!doctype html>
        <html>
        <head>
          <meta charset="utf-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1" />
          <title>Trigger Panel Gate</title>
          <style>
            body {{ font-family: Arial, sans-serif; margin: 2rem; color: #1f2933; }}
            .gate {{ max-width: 520px; border: 1px solid #d9e2ec; border-radius: 8px; padding: 1.2rem; }}
            label {{ display: block; font-weight: 600; margin-bottom: 0.5rem; }}
            input {{ width: 100%; padding: 0.5rem; margin-bottom: 0.8rem; }}
            button {{ padding: 0.5rem 0.9rem; }}
            .error {{ color: #b91c1c; font-weight: 600; }}
          </style>
        </head>
        <body>
          <div class="gate">
            <h1>Operator Gate</h1>
            <p>Enter OPERATOR_ACCESS_TOKEN to access the Trigger Panel.</p>
            {error}
            <form method="post" action="/gate">
              <label for="operator_access_token">OPERATOR_ACCESS_TOKEN</label>
              <input id="operator_access_token" name="operator_access_token" type="password" autocomplete="off" required />
              <button type="submit">Enter Trigger Panel</button>
            </form>
          </div>
        </body>
        </html>
        """

    @staticmethod
    def _bridge_status_snapshot() -> dict[str, str]:
        base_url = str(os.getenv("BRIDGE_BASE_URL", "") or "").strip()
        project_id = str(os.getenv("BRIDGE_PROJECT_ID", "") or "").strip()
        api_key = str(os.getenv("BRIDGE_API_KEY", "") or "").strip()

        configured = bool(base_url and project_id and api_key)
        return {
            "bridge_status": "configured" if configured else "not_configured",
            "base_url": base_url or BRIDGE_DEFAULT_BASE_URL,
            "project_id_status": "set" if project_id else "missing",
            "api_key_status": "set" if api_key else "missing",
        }

    def _shell(self, start_response):  # type: ignore[no-untyped-def]
        last_result = self.service.last_result or {
            "event_id": None,
            "accepted": False,
            "stored": False,
            "errors": [],
        }
        bridge = self._bridge_status_snapshot()
        runtime_buttons = "\n".join(
            [
                "<form method='post' action='/admin/trigger-panel/events/{event}'>"
                "<button type='submit'>Send {event}</button></form>".format(event=html.escape(event))
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
                            "<button type='submit'>Send {action}</button></form>".format(action=html.escape(action))
                            for action in actions
                        ]
                    ),
                )
                for title, actions in ACTION_TYPES_BY_CATEGORY.items()
            ]
        )
        safe_last_result = html.escape(json.dumps(last_result, ensure_ascii=True, indent=2))

        page_html = f"""
        <!doctype html>
        <html>
        <head>
          <meta charset="utf-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1" />
          <title>Trigger Panel</title>
          <style>
            body {{ font-family: Arial, sans-serif; margin: 1.2rem; color: #1f2933; }}
            h1 {{ margin-bottom: 0.4rem; }}
            section {{ border: 1px solid #d9e2ec; border-radius: 8px; padding: 0.8rem; margin-bottom: 0.7rem; }}
            form {{ display: inline-block; margin: 0.2rem 0.25rem 0.2rem 0; }}
            button {{ padding: 0.35rem 0.55rem; cursor: pointer; }}
            pre {{ background: #f8fafc; border-radius: 6px; padding: 0.6rem; overflow-x: auto; }}
            .muted {{ color: #52606d; }}
            .disabled-note {{ color: #7b341e; }}
          </style>
        </head>
        <body>
        <h1>Trigger Panel</h1>
        <section>
            <h2>Bridge Connection Status</h2>
            <p><strong>bridge_status = {html.escape(bridge["bridge_status"])}</strong></p>
            <p class="muted">Server-side push target base URL: {html.escape(bridge["base_url"])}</p>
            <p class="muted">Required env keys: BRIDGE_BASE_URL, BRIDGE_PROJECT_ID, BRIDGE_API_KEY</p>
            <p class="muted">BRIDGE_PROJECT_ID: {html.escape(bridge["project_id_status"])}, BRIDGE_API_KEY: {html.escape(bridge["api_key_status"])}</p>
            <p class="muted">When configured, button presses are pushed server-side via trigger-bridge to <code>/api/bridge/ingest</code>.</p>
        </section>
        <section>
            <h2>Runtime Events</h2>
            {runtime_buttons}
        </section>
        {action_sections}
        <section>
            <h2>Last Trigger Result</h2>
            <pre>{safe_last_result}</pre>
        </section>
        <section>
            <h2>Dashboard Visibility Check</h2>
            <p class="muted">Check local proof endpoints at <code>/admin/trigger-panel/summary</code> and <code>/admin/trigger-panel/trigger-log</code>.</p>
            <p class="muted">For live bridge checks, verify Accepted Payloads and Last Signal in manager dashboard.</p>
        </section>
        <section>
            <h2>Disabled Advertising / Performance</h2>
            <p class="disabled-note">disabled / not_connected</p>
            <p class="muted">Advertising and financial controls (ROI, ads, revenue, payments, affiliate payouts, CAC, LTV) remain intentionally disabled.</p>
        </section>
        <section>
            <h2>Operator Utilities</h2>
            <form method="post" action="/admin/trigger-panel/cleanup">
              <button type="submit">Run cleanup_operator_test_data</button>
            </form>
        </section>
        </body>
        </html>
        """
        return self._respond_html(start_response, page_html)

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
                "bridge_result": result.get("bridge_result"),
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
                "bridge_result": result.get("bridge_result"),
            },
        )

    @staticmethod
    def _read_form_body(environ) -> dict:  # type: ignore[no-untyped-def]
        try:
            length = int(environ.get("CONTENT_LENGTH", "0") or "0")
        except ValueError:
            length = 0
        input_stream = environ.get("wsgi.input")
        body_bytes = input_stream.read(length) if length > 0 and input_stream is not None else b""
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
    def _respond_html(start_response, html: str, *, status_code: int = 200, extra_headers: list[tuple[str, str]] | None = None):  # type: ignore[no-untyped-def]
        body = html.encode("utf-8")
        status_text = "OK" if status_code < 400 else "ERROR"
        headers = [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(body)))]
        if extra_headers:
            headers.extend(extra_headers)
        start_response(
            f"{status_code} {status_text}",
            headers,
        )
        return [body]

    @staticmethod
    def _redirect(start_response, location: str, extra_headers: list[tuple[str, str]] | None = None):  # type: ignore[no-untyped-def]
        headers = [("Location", location), ("Content-Length", "0")]
        if extra_headers:
            headers.extend(extra_headers)
        start_response("303 SEE OTHER", headers)
        return [b""]
