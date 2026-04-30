# Trigger Panel Deployment

This repository supports Vercel deployment as a standalone Python WSGI app.

## Vercel deployment steps

1. Import GitHub repo `nikkaradimitris-cloud/trigger-panel` into Vercel.
2. Keep the default Python build/runtime; the repo exposes `app` via `api/index.py`.
3. Add environment variables in Vercel Project Settings:
   - `BRIDGE_BASE_URL=https://manager.subby.cloud`
   - `OPERATOR_ACCESS_TOKEN=<secret>`
4. Deploy.
5. Open `<vercel-url>/gate` and authenticate with `OPERATOR_ACCESS_TOKEN`.
6. In manager dashboard, open `https://manager.subby.cloud/admin/bridge` and select **Add External App**.
7. Paste the Vercel Trigger Panel URL and create the external app.
8. Copy generated credentials back to Vercel env vars:
   - `BRIDGE_PROJECT_ID=bridge_...`
   - `BRIDGE_API_KEY=sbk_...`
9. Redeploy after adding those env vars.
10. Open Trigger Panel and press **Send page_view**.
11. In manager dashboard, verify:
    - Accepted Payloads increments
    - Last Signal updates

## Entrypoints included in this repo

- Local process entrypoint: `run_trigger_panel.py`
- Vercel runtime entrypoint: `api/index.py`
- Procfile command: `web: python run_trigger_panel.py`

## Required environment variables

- `BRIDGE_BASE_URL` (set to `https://manager.subby.cloud`)
- `OPERATOR_ACCESS_TOKEN`
- `BRIDGE_PROJECT_ID` (after Add External App)
- `BRIDGE_API_KEY` (after Add External App)
