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

## Stage 0 Scope

Stage 0 is documentation and audit only. No Trigger Panel UI implementation is done in this stage.

## Future Deployment Direction

Live test URL direction is allowed in later stages for internal operators only, never as a public customer production surface.
