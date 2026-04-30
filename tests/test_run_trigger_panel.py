from __future__ import annotations

from pathlib import Path
from typing import Any

import run_trigger_panel


def test_main_uses_local_defaults_when_env_missing(monkeypatch) -> None:
    monkeypatch.delenv("HOST", raising=False)
    monkeypatch.delenv("PORT", raising=False)

    captured: dict[str, Any] = {}

    class DummyServer:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
            return None

        def serve_forever(self) -> None:
            captured["serve_forever_called"] = True

    def fake_make_server(host: str, port: int, app: Any) -> DummyServer:
        captured["host"] = host
        captured["port"] = port
        captured["app"] = app
        return DummyServer()

    monkeypatch.setattr(run_trigger_panel, "make_server", fake_make_server)
    run_trigger_panel.main()

    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 8019
    assert captured["serve_forever_called"] is True
    assert getattr(captured["app"], "service", None) is not None
    assert captured["app"].service.store.path == Path("data") / "trigger_events.jsonl"


def test_main_uses_host_and_port_from_env(monkeypatch) -> None:
    monkeypatch.setenv("HOST", "0.0.0.0")
    monkeypatch.setenv("PORT", "9000")

    captured: dict[str, Any] = {}

    class DummyServer:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
            return None

        def serve_forever(self) -> None:
            captured["serve_forever_called"] = True

    def fake_make_server(host: str, port: int, app: Any) -> DummyServer:
        captured["host"] = host
        captured["port"] = port
        captured["app"] = app
        return DummyServer()

    monkeypatch.setattr(run_trigger_panel, "make_server", fake_make_server)
    run_trigger_panel.main()

    assert captured["host"] == "0.0.0.0"
    assert captured["port"] == 9000
    assert captured["serve_forever_called"] is True
