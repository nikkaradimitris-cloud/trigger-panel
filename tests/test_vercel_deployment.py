from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from api.index import app


def test_vercel_entrypoint_file_exists() -> None:
    assert Path("api/index.py").exists()


def test_vercel_entrypoint_exposes_callable_wsgi_app() -> None:
    assert callable(app)
    environ: dict[str, Any] = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": "/",
        "CONTENT_LENGTH": "0",
        "wsgi.input": io.BytesIO(b""),
    }
    captured: dict[str, Any] = {"status": None}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        captured["status"] = status
        captured["headers"] = headers

    chunks = app(environ, start_response)
    body = b"".join(chunks)

    assert isinstance(body, bytes)
    assert str(captured["status"]).startswith("404")


def test_vercel_entrypoint_has_no_hardcoded_api_key() -> None:
    entrypoint = Path("api/index.py").read_text(encoding="utf-8")
    assert "sbk_" not in entrypoint
    assert "BRIDGE_API_KEY=" not in entrypoint


def test_deployment_docs_include_vercel_and_required_env_vars() -> None:
    content = Path("docs/deployment.md").read_text(encoding="utf-8")
    assert "Vercel" in content
    assert "nikkaradimitris-cloud/trigger-panel" in content
    assert "BRIDGE_BASE_URL=https://manager.subby.cloud" in content
    assert "OPERATOR_ACCESS_TOKEN=<secret>" in content
    assert "BRIDGE_PROJECT_ID=bridge_..." in content
    assert "BRIDGE_API_KEY=sbk_..." in content
