"""Vercel Python runtime entrypoint for Trigger Panel."""

from __future__ import annotations

import os
from pathlib import Path

from trigger_panel.app import TriggerPanelApp


def _store_path() -> Path:
    configured = str(os.getenv("TRIGGER_PANEL_STORE_PATH", "") or "").strip()
    if configured:
        return Path(configured)
    # Vercel allows writes only in /tmp.
    return Path("/tmp") / "trigger_events.jsonl"


app = TriggerPanelApp(store_path=_store_path())
