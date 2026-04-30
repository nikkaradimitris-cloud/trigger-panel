"""Run Trigger Panel WSGI server locally."""

from __future__ import annotations

import os
from pathlib import Path
from wsgiref.simple_server import make_server

from trigger_panel.app import TriggerPanelApp


def _host_from_env() -> str:
    return str(os.getenv("HOST", "127.0.0.1") or "").strip() or "127.0.0.1"


def _port_from_env() -> int:
    raw = str(os.getenv("PORT", "8019") or "").strip()
    try:
        return int(raw)
    except ValueError:
        return 8019


def main() -> None:
    app = TriggerPanelApp(store_path=Path("data") / "trigger_events.jsonl")
    host = _host_from_env()
    port = _port_from_env()
    with make_server(host, port, app) as server:
        print(f"Trigger Panel running at http://{host}:{port}/admin/trigger-panel")
        print("Use header X-Operator-Session: approved-operator")
        server.serve_forever()


if __name__ == "__main__":
    main()
