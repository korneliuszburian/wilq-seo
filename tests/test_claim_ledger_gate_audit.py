from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "claim_ledger_gate_audit.py"
    spec = importlib.util.spec_from_file_location("claim_ledger_gate_audit", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_claim_ledger_gate_audit_proves_content_generation_gates() -> None:
    audit = load_module()

    report = audit.build_report()

    assert report["pass"] is True
    assert report["check_count"] == 11
    assert report["failed_count"] == 0
    check_names = {check["name"] for check in report["checks"]}
    assert {
        "guarantee_claim_blocked",
        "measurement_claim_waits_for_window",
        "legal_claim_requires_human_review",
        "evidence_claim_requires_source_connector",
        "structured_generation_requires_claim_ledger",
        "structured_generation_respects_ledger_blockers",
        "structured_generation_blocks_claims_outside_ledger",
        "full_draft_requires_approved_knowledge",
        "valid_section_contract_stays_review_only",
        "removed_claims_are_visible_to_model_contract",
    } <= check_names
    assert "missing_source_connector" in report["claim_ledger_blocks"]
    assert {
        "missing_claim_ledger",
        "claim_ledger_blocks_generation",
        "draft_package_claim_outside_ledger",
        "review_required_knowledge_for_full_draft",
    } <= set(report["structured_generation_blocks"])
    assert report["publish_ready_locked"] is True
    assert "blokuje gwarancje" in report["co_pokazac_wilkowi"]
    assert "zamkniętych okien pomiaru" in report["co_nadal_brakuje"]


def test_claim_ledger_gate_markdown_is_wilku_readable() -> None:
    audit = load_module()
    report = audit.build_report()

    markdown = audit.render_markdown(report)

    assert "# WILQ Claim Ledger gate audit" in markdown
    assert "- Wynik: PASS" in markdown
    assert "## Co pokazać Wilkowi" in markdown
    assert "WILQ ma działające sprawdzenie twierdzeń" in markdown
    assert "`missing_claim_ledger`" in markdown
    assert "`review_required_knowledge_for_full_draft`" in markdown
    assert "claimów" not in markdown
