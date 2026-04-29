# Trigger Panel Architecture Audit (Stage 0)

## Project Identity

Trigger Panel Live V1 is an internal/operator-only test panel that prepares and sends runtime events through a Universal Bridge-compatible contract. It is not a public customer page and not a replacement for Subby core systems.

## Boundaries

- Work product in this stage is limited to docs and tests in `subby-trigger-panel`.
- No Trigger Panel UI implementation yet.
- No runtime event buttons yet.
- No bridge implementation cloning.
- No changes to `subby-universal-bridge` or `subby-contract-reference`.
- No claims of live Subby dashboard integration.

## Reference Folders Inspected

- `C:\Users\User\Desktop\subby-universal-bridge`
- `C:\Users\User\Desktop\subby-contract-reference`

## Universal Bridge Compatibility Requirements

### Bridge files inspected

- `contracts/universal_bridge_contract.schema.json`
- `src/subby_universal_bridge/contract.py`
- `src/subby_universal_bridge/validator.py`
- `src/subby_universal_bridge/normalizer.py`
- `src/subby_universal_bridge/router.py`
- `src/subby_universal_bridge/storage.py`
- `src/subby_universal_bridge/response.py`
- `src/subby_universal_bridge/anti_fake.py`
- `src/subby_universal_bridge/bridge.py`
- `src/subby_universal_bridge/test_data.py`
- `docs/BRIDGE_CONTRACT_SPECIFICATION.md`
- `docs/REQUIRED_FIELDS.md`
- `docs/OPTIONAL_CHANNELS.md`
- `docs/ANTI_FAKE_DATA_RULES.md`
- `docs/DASHBOARD_COMPATIBILITY_CONTRACT.md`
- `docs/TRIGGER_PANEL_COMPATIBILITY.md`
- `docs/SUBBY_COMPATIBILITY_SOURCE_AUDIT.md`
- `docs/V1_BRIDGE_FINAL_REPORT.md`
- `examples/payloads/trigger_panel_test_event.json`
- `examples/payloads/runtime_event.json`
- `examples/payloads/fake_revenue_rejected.json`
- `tests/test_validator.py`
- `tests/test_dashboard_compatibility_contract.py`
- `tests/test_subby_compatibility_contract.py`

### Required payload fields Trigger Panel must obey

Required for acceptance:

- `schema_version` = `1.0.0`
- `source_app`
- `source`
- `project_id`
- `timestamp` (valid ISO 8601)
- `test_mode`
- `payload` (object)
- at least one of `event_type` or `signal_type`

Trigger Panel-specific required values:

- `source=trigger_panel`
- `test_mode=true`
- `metadata.operator_generated=true`

### Optional fields Trigger Panel must handle honestly

Optional channels are allowed but not required:

- `revenue`, `cost`, `ads`, `ROI`, `affiliate_events`, `payments`, `campaigns`, `conversions`

If unknown/unavailable, Trigger Panel must keep explicit honest values only:

- `not_connected`
- `not_applicable`
- `empty`
- `data_not_yet`
- `null` where schema allows unknown values

### Fake-data rules Trigger Panel must obey

Trigger Panel must never create:

- fake revenue
- fake ROI
- fake ad spend
- fake payments
- fake affiliate payouts
- production-looking business data without proof
- no fake revenue
- no fake ROI
- no fake ads
- no fake payments

### Dashboard visibility expectations

Bridge compatibility expects a `dashboard_visibility` object with:

- `visible`
- `target_panels`
- `summary`
- `metrics`
- `empty_states`
- `test_mode`
- `not_connected_channels`
- `not_applicable_channels`
- `warnings`

This is compatibility/readiness output, not a claim that live dashboard writes already exist.
No live Subby dashboard integration is claimed.

### Trigger Panel compatibility rules

- Trigger Panel remains test-data isolated.
- Trigger Panel payload contract must match Universal Bridge V1; no separate Trigger Panel contract may be invented.
- Trigger Panel should build full runtime payloads where possible and keep unknowns honest.

### Exact risks if Trigger Panel does not follow bridge contract

- Payload rejection by validator for missing or invalid required fields.
- Rejection for fake channel data (revenue/ROI/ads/payments/affiliate).
- Loss of dashboard visibility compatibility object shape.
- Misleading operator interpretation if unknown data is fabricated.
- Unsafe mixing of test and production-looking data.

## Universal Bridge Required Payload Rules

- Required keys cannot be missing or empty.
- Timestamp must be valid and machine-parseable.
- Unknown schema versions are rejected.
- Missing both `event_type` and `signal_type` is rejected.
- Trigger Panel test data requires operator generation marker.

## Subby Dashboard / Runtime Compatibility Observations

### Reference files inspected

- `backend/app/api/main.py`
- `backend/app/admin/routes_subby_chat_ui.py`
- `backend/app/admin/templates/base.html`
- `backend/app/admin/templates/dashboard.html`
- `backend/app/runtime_api.py`
- `backend/app/runtime_events.py`
- `backend/app/runtime_registry.py`
- `backend/app/automation/outcomes.py`
- `backend/app/automation/hitl_registry.py`
- `backend/app/flags/persistence.py`
- `backend/tests/test_stage_runtime_real_event_ingestion.py`
- `backend/tests/test_stage_runtime_phase1_metrics_endpoint.py`
- `backend/tests/test_admin_login_dashboard_redirect.py`
- `backend/tests/test_stage_runtime_phase_c_surface.py`

### Known dashboard/admin/runtime surfaces

- Internal admin dashboard exists at `/admin/dashboard`.
- Admin modules exist for outputs, queue, approvals, runtime registry, library/archive, manager, flags, and chat.
- Runtime ingestion and retrieval APIs exist (`/api/runtime/event`, project events/metrics/funnel endpoints).
- Runtime registry exists via `_runtime_registry.json` abstraction and list/get/upsert flow.

### Known runtime event paths

- Runtime event ingestion is persisted through SQLite (`_runtime_events.sqlite`) in reference implementation.
- Summary/metrics/funnel endpoints derive from stored event records.
- Runtime event source/origin/type normalization is enforced.

### Known outputs/health/queue/approvals/flags/manager/registry/archive surfaces

- Outputs: recent runtime and automation outcomes surfaces are present.
- Health: `/health` and manager health references are present.
- Queue: HITL queue page exists, but queue feed is marked partial in reference UI.
- Approvals: route exists, but feed is placeholder/not fully connected.
- Flags: persistence exists and is file-backed with safe fallback paths.
- Manager: manager health is surfaced; decision feed is partial/not fully exposed.
- Registry: runtime registry is present and queryable.
- Archive/library: library/archive page reads template categories and counts.

### Unknown / not_connected areas

- Full live end-to-end dashboard propagation from Trigger Panel is not proven in this repo yet.
- Approval queue feed wiring is not fully exposed in reference.
- Manager decision event feed is not fully exposed in reference.
- Any external paid provider-backed economics channel is not proven for Trigger Panel stage 0.

Unknown areas must remain honest as `not_connected`, `not_applicable`, `empty`, `data_not_yet`, or `null`.

### Risks and blockers for future implementation

- Risk of contract drift if Trigger Panel payload builder diverges from bridge schema.
- Risk of false confidence if partial/placeholder surfaces are represented as live.
- Risk of test data pollution without strict source/test/operator markers.
- Blocker: must maintain dashboard compatibility shape without claiming live write integration.

## Protected Route Target

Planned protected route target: `/admin/trigger-panel`.

## Live Test Deployment Direction

A live test deployment is allowed later for internal operators, protected access only, and no public customer exposure.

## Internal / Operator-only Rule

Trigger Panel is strictly internal and operator-generated for testing only.

## First Closed Outcome Definition

Operator presses button in Trigger Panel -> full runtime event is built -> event is sent through Universal Bridge-compatible contract -> event is accepted/stored by backend or local proof layer -> event becomes visible in dashboard/summary proof -> no fake metrics are created.

## Excluded Metrics (Must Stay Disabled / Not Connected)

- Advertising performance
- ROI
- CAC
- LTV
- Paid campaign spend
- Affiliate payout
- Payment revenue
- Real customer conversion value

If these appear in future UI, they must remain `disabled`, `not_connected`, `not_applicable`, or `data_not_yet` until real providers and proofs exist.

## No Fake Data Rule

No fabricated business/economic/performance metrics are allowed at any stage.

## Proposed Implementation Path (Stages 1-16)

1. Protected Trigger Panel Shell
2. Full Runtime Event Payload Builder
3. Runtime Event Buttons
4. Dashboard Visibility Proof
5. Output Trigger Buttons
6. Health Trigger Buttons
7. Automation Outcome Buttons
8. Queue Trigger Buttons
9. Approvals Trigger Buttons
10. Flags Trigger Buttons
11. Manager Signal Buttons
12. Runtime Registry Probe
13. Library / Archive Probe
14. Unified Trigger Result Log
15. Test Data Cleanup Controls
16. Final Trigger Panel Audit Closure

## Allowed Changes for Future Stages

- New internal Trigger Panel docs/tests/code only in `subby-trigger-panel`.
- Payload builder and validators aligned to Universal Bridge contract.
- Internal proof tooling for acceptance/storage/visibility.
- Honest placeholder handling for unknown channels.

## Forbidden Changes for Future Stages

- Editing `subby-clean-v3`, `mision-comand-conektor`, `subby-universal-bridge`, or `subby-contract-reference`.
- Fake revenue/ROI/ads/payments/affiliate values.
- Public customer exposure of Trigger Panel.
- Claims of live dashboard integration without proof.

## Test Strategy

- Stage-level audit tests that enforce roadmap lock.
- Contract phrase checks for required source/test/operator fields.
- Negative checks for fake metric claims and unproven live integration claims.
- Later stages add payload schema, bridge-compatibility, and visibility proof tests.

## Final Closure Criteria

Stage 0 closes as PASSED only when:

- Architecture path and boundaries are documented.
- Required references were inspected.
- Universal Bridge compatibility is mandatory and explicit.
- Subby dashboard/runtime observations are documented with honest unknowns.
- Sections 1-16 remain Pending / Not started.
- No implementation for later stages is performed during Stage 0.
