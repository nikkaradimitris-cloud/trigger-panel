# Trigger Panel Live V1

Trigger Panel is an internal operator test panel for controlled runtime signal testing.

## What It Is

- Internal/operator-only surface for safe test triggers.
- A payload builder and trigger interface for Universal Bridge-compatible runtime events.
- A staged system that starts with architecture audit before any implementation.

## What It Is Not

- Not a public customer page.
- Not Universal Bridge.
- Not Picwise.
- Not Subby core.
- Not a production revenue dashboard.

## Safety and Data Integrity Rules

- No fake metrics are allowed.
- Trigger payloads must use `source=trigger_panel`.
- Trigger payloads must use `test_mode=true`.
- Trigger payload metadata must include `operator_generated=true`.
- No fake ROI, fake ads, fake revenue, fake payments, or fake affiliate payouts.
- Excluded business metrics remain `disabled`, `not_connected`, `not_applicable`, or `data_not_yet` until proven real.

## Current Scope

Stage 0 audit is complete, and Trigger Panel Core stages 1-4 are implemented locally as an internal proof block.

### Implemented internal routes

- `GET /admin/trigger-panel` (protected operator shell)
- `POST /admin/trigger-panel/events/<event_type>` (runtime event triggers)
- `GET /admin/trigger-panel/summary` (local visibility proof)
- `GET /gate` (protected access fallback)

### Local run

```powershell
python .\run_trigger_panel.py
```

Then call the protected route with header:

- `X-Operator-Session: approved-operator`

## Dashboard Integration Status

Live Subby dashboard integration is not claimed in this repository. Current implementation proves local/operator test visibility only and requires a future adapter route for safe live integration.
