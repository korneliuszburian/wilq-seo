"""Parent-safe source observer for source-fact authority attempt versioning."""

from __future__ import annotations

from pathlib import Path


def _source(root: Path, relative: str) -> str:
    try:
        return (root / relative).read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _section(source: str, start: str, end: str) -> str:
    start_at = source.find(start)
    end_at = source.find(end, start_at + len(start))
    return "" if start_at < 0 or end_at < 0 else source[start_at:end_at]


def test_source_fact_authority_attempt_contract() -> None:
    root = Path(__file__).resolve().parents[2]
    contracts = _source(root, "wilq/content/workflow/_source_fact_authority_contracts.py")
    runtime = _source(root, "wilq/content/workflow/_source_fact_authority_runtime.py")
    store = _source(root, "wilq/content/workflow/store/store_source_fact_authority.py")

    preview_command = _section(
        contracts,
        "class ContentSourceFactAuthorityPreviewCommand",
        "\n\nclass ContentSourceFactProvenance",
    )
    proposal = _section(
        contracts,
        "class ContentSourceFactAuthorityProposal",
        "\n\nclass ContentSourceFactAuthorityReceipt",
    )
    strict_field = "attempt: int = Field(default=0, ge=0, le=1000, strict=True)"
    assert strict_field in preview_command
    assert strict_field in proposal

    proposal_digest = _section(
        contracts,
        "def source_fact_authority_proposal_digest(",
        "\ndef source_fact_authority_action_id(",
    )
    action_id = _section(
        contracts,
        "def source_fact_authority_action_id(",
        "\ndef source_fact_authority_action_payload_digest(",
    )
    payload_digest = _section(
        contracts,
        "def source_fact_authority_action_payload_digest(",
        "\ndef source_fact_authority_receipt_digest(",
    )
    validator = _section(contracts, "def _validate_attempt(", "\n\n__all__")
    assert "attempt: int = 0" in proposal_digest
    assert "_validate_attempt(attempt)" in proposal_digest
    assert 'if attempt:\n        payload["attempt"] = attempt' in proposal_digest
    assert "return canonical_json_digest(payload)" in proposal_digest
    assert "attempt: int = 0" in action_id
    assert "_validate_attempt(attempt)" in action_id
    assert "base_id if attempt == 0 else" in action_id
    assert "_attempt_" in action_id
    assert "attempt = action.payload.get(\"attempt\", 0)" in payload_digest
    assert "_validate_attempt(attempt)" in payload_digest
    assert 'if attempt:\n        payload["attempt"] = attempt' in payload_digest
    assert "return canonical_json_digest(payload)" in payload_digest
    assert "if isinstance(attempt, bool) or not isinstance(attempt, int)" in validator
    assert "not 0 <= attempt <= 1000" in validator

    build_action = _section(
        runtime,
        "def build_source_fact_authority_action(",
        "\ndef validate_source_fact_authority_action_payload(",
    )
    validate_payload = _section(
        runtime,
        "def validate_source_fact_authority_action_payload(",
        "\ndef source_fact_authority_action_for_proposal(",
    )
    execute_authority = _section(
        runtime,
        "def execute_content_source_fact_authority(",
        "\ndef read_content_source_fact_authority(",
    )
    assert 'if proposal.attempt:\n        action_payload["attempt"] = proposal.attempt' in build_action
    assert '_validate_attempt(payload.get("attempt", 0))' in validate_payload
    assert '_validate_attempt(action.payload.get("attempt", 0))' in execute_authority

    record_proposal = _section(
        store,
        "def record_content_source_fact_authority_proposal(",
        "\n    def load_content_source_fact_authority_proposal(",
    )
    assert record_proposal.count("accepted.attempt") == 3
    assert "attempt=accepted.attempt," in record_proposal
