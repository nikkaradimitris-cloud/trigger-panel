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

Trigger Panel stages 0-16 are implemented in this repository as a local/operator proof system.

### Implemented internal routes

- `GET /admin/trigger-panel` (protected operator shell)
- `POST /admin/trigger-panel/events/<event_type>` (runtime event triggers)
- `POST /admin/trigger-panel/actions/<action_type>` (output/health/automation/queue/approval/flag/manager/probe triggers)
- `GET /admin/trigger-panel/summary` (local visibility proof)
- `GET /admin/trigger-panel/trigger-log` (unified trigger result log)
- `POST /admin/trigger-panel/cleanup` (safe operator test data cleanup)
- `GET /gate` (protected access fallback)

### Implemented roadmap actions

- `5. Output Trigger Buttons`: `output_created`, `output_delivered`, `output_failed`
- `6. Health Trigger Buttons`: `health_ok`, `health_degraded`, `health_error`, `runtime_ping`
- `7. Automation Outcome Buttons`: `automation_started`, `automation_succeeded`, `automation_failed`, `automation_requires_manual_intervention`
- `8. Queue Trigger Buttons`: `queue_item_created`, `queue_item_started`, `queue_item_completed`, `queue_item_failed`
- `9. Approvals Trigger Buttons`: `approval_requested`, `approval_approved`, `approval_rejected`, `approval_expired`
- `10. Flags Trigger Buttons`: `flag_info`, `flag_warning`, `flag_error`, `flag_resolved`
- `11. Manager Signal Buttons`: `manager_signal_observed`, `manager_decision_requested`, `manager_decision_suggested`, `manager_action_required`
- `12. Runtime Registry Probe`: `runtime_registry_probe`, `runtime_registry_available`, `runtime_registry_missing`, `runtime_registry_error`
- `13. Library / Archive Probe`: `library_archive_probe`, `library_item_found`, `library_item_missing`, `library_archive_error`

### Local run

```powershell
python .\run_trigger_panel.py
```

Then call the protected route with header:

- `X-Operator-Session: approved-operator`

## Dashboard Integration Status

Live Subby dashboard integration is not claimed in this repository. Current implementation proves local/operator test visibility only and requires a future adapter route for safe live integration.

## Data Integrity and Cleanup Safety

- Unified trigger result log is computed from stored trigger records only.
- Unknown/missing values remain honest (`null`, `not_connected`, `not_applicable`, `empty`, `data_not_yet`) instead of fabricated values.
- Cleanup only removes records that match all three markers:
  - `source=trigger_panel`
  - `test_mode=true`
  - `operator_generated=true`
- Cleanup does not remove non-test-looking records.
- No fake revenue/ROI/ads/payments/affiliate/customer data is generated.
