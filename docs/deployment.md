# Trigger Panel Deployment

This repository can be deployed as a standalone Trigger Panel web app.

## 1) Deploy this repo

- Deploy `subby-trigger-panel` as its own Python web service.
- Start command:

```bash
python run_trigger_panel.py
```

- For Procfile-based hosts, this repo includes:

```text
web: python run_trigger_panel.py
```

## 2) Configure environment variables

Set these on the hosting platform:

- `BRIDGE_BASE_URL=https://manager.subby.cloud`
- `BRIDGE_PROJECT_ID=<from manager External App setup>`
- `BRIDGE_API_KEY=<from manager External App setup>`
- `OPERATOR_ACCESS_TOKEN=<operator gate token>`
- `HOST=0.0.0.0`
- `PORT=8019` (or platform-provided port)

## 3) Get the live Trigger Panel URL

- After deploy, copy the public URL for this app.
- Open: `<live-url>/gate`
- Authenticate with `OPERATOR_ACCESS_TOKEN`.

## 4) Connect in manager dashboard

1. Open `https://manager.subby.cloud/admin/bridge`.
2. Select **Add External App**.
3. Paste the live Trigger Panel URL.
4. Copy generated Project ID and API Key into this app's host env:
   - `BRIDGE_PROJECT_ID`
   - `BRIDGE_API_KEY`

## 5) Verify bridge flow

1. In Trigger Panel, press **Send page_view**.
2. In manager dashboard, verify:
   - Accepted Payloads increments
   - Last Signal updates
