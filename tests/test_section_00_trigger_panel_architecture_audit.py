from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
ROADMAP = ROOT / "docs" / "ROADMAP.md"
ARCH_AUDIT = ROOT / "docs" / "TRIGGER_PANEL_ARCHITECTURE_AUDIT.md"
SECTION_AUDIT = ROOT / "docs" / "audits" / "section_00_trigger_panel_architecture_audit.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _all_docs_text() -> str:
    return "\n".join([_read(README), _read(ROADMAP), _read(ARCH_AUDIT), _read(SECTION_AUDIT)])


def test_required_files_exist() -> None:
    assert README.exists()
    assert ROADMAP.exists()
    assert ARCH_AUDIT.exists()
    assert SECTION_AUDIT.exists()


def test_readme_states_internal_operator_only() -> None:
    text = _read(README).lower()
    assert "internal/operator-only" in text


def test_roadmap_contains_sections_0_to_16() -> None:
    text = _read(ROADMAP)
    for i in range(17):
        assert f"- {i}." in text


def test_section_0_is_passed_and_stage_lines_exist() -> None:
    roadmap_text = _read(ROADMAP)
    assert "0. Trigger Panel Architecture Audit - PASSED" in roadmap_text
    for i in range(1, 17):
        assert f"{i}." in roadmap_text


def test_roadmap_stage_statuses_after_core_block() -> None:
    roadmap_text = _read(ROADMAP)
    assert "- 1. Protected Trigger Panel Shell - PASSED" in roadmap_text
    assert "- 2. Full Runtime Event Payload Builder - PASSED" in roadmap_text
    assert "- 3. Runtime Event Buttons - PASSED" in roadmap_text
    assert "- 4. Dashboard Visibility Proof - PASSED" in roadmap_text
    for i in range(5, 17):
        assert f"- {i}." in roadmap_text and "Pending / Not started" in roadmap_text


def test_docs_include_required_trigger_panel_contract_flags() -> None:
    text = _all_docs_text()
    assert "source=trigger_panel" in text
    assert "test_mode=true" in text
    assert "operator_generated=true" in text


def test_docs_include_no_fake_metrics_requirements() -> None:
    text = _all_docs_text().lower()
    assert "no fake roi" in text
    assert "no fake ads" in text
    assert "no fake revenue" in text
    assert "no fake payments" in text


def test_docs_include_universal_bridge_compatibility_and_reference_paths() -> None:
    text = _all_docs_text()
    assert "Universal Bridge compatibility" in text
    assert "subby-universal-bridge" in text
    assert "subby-contract-reference" in text


def test_docs_include_first_closed_outcome_definition() -> None:
    text = _all_docs_text().lower()
    assert "operator presses button" in text
    assert "full runtime event is built" in text
    assert "accepted/stored" in text or "accepted and stored" in text
    assert "dashboard/summary" in text


def test_docs_state_excluded_metrics_are_disabled_or_not_connected() -> None:
    text = _all_docs_text().lower()
    assert "excluded metrics" in text
    assert "disabled" in text
    assert "not_connected" in text


def test_no_false_claim_of_live_subby_dashboard_integration() -> None:
    text = _all_docs_text()
    assert "No live Subby dashboard integration is claimed." in text
    forbidden_claims = [
        "live subby dashboard integration is active",
        "live subby dashboard integration is complete",
        "trigger panel is live-integrated with subby dashboard",
    ]
    lowered = text.lower()
    for claim in forbidden_claims:
        assert claim not in lowered
