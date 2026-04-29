"""Run Trigger Panel WSGI server locally."""

from __future__ import annotations

from pathlib import Path
from wsgiref.simple_server import make_server

from trigger_panel.app import TriggerPanelApp


def main() -> None:
    app = TriggerPanelApp(store_path=Path("data") / "trigger_events.jsonl")
    with make_server("127.0.0.1", 8019, app) as server:
        print("Trigger Panel running at http://127.0.0.1:8019/admin/trigger-panel")
        print("Use header X-Operator-Session: approved-operator")
        server.serve_forever()


if __name__ == "__main__":
    main()
