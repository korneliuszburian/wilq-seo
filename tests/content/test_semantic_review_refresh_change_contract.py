"""Parent-safe source observer for the semantic refresh-review seam."""

from pathlib import Path


def test_semantic_refresh_source_contract() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (root / "apps/api/wilq_api/routers/content_workflow.py").read_text(encoding="utf-8")
    review_snapshot_start = source.index("def semantic_review_snapshot_for_work_item_or_404(")
    review_snapshot_end = source.index(
        "\ndef _binding_aware_revision_workspace(", review_snapshot_start
    )
    review_snapshot = source[review_snapshot_start:review_snapshot_end]

    assert "expected_planning_input_digest=authorization.planning_input_digest" in review_snapshot
    assert "refresh_preparation_authorization_id=binding.authorization_id" in review_snapshot
    assert (
        "expected_refresh_preparation_authorization_digest=binding.authorization_digest"
        in review_snapshot
    )
    assert "_canonical_refresh_binding_matches_authority(" in review_snapshot
    assert "_refresh_binding_matches_authority(" in review_snapshot
    assert "_fail_closed_semantic_review_snapshot(canonical)" in review_snapshot

    authority_start = source.index("def _persisted_refresh_authorization_for_binding(")
    authority_end = source.index("\ndef _binding_aware_revision_workspace(", authority_start)
    authority = source[authority_start:authority_end]
    assert "authorization.authorization_id != binding.authorization_id" in authority
    assert "authorization.authorization_digest != binding.authorization_digest" in authority
    assert "refresh_preparation_bindings_match_authority(" in authority

    fail_closed_start = source.index("def _fail_closed_semantic_review_snapshot(")
    fail_closed_end = source.index(
        "\ndef _canonical_refresh_binding_matches_authority(", fail_closed_start
    )
    fail_closed = source[fail_closed_start:fail_closed_end]
    assert '"planning_workspace": None' in fail_closed
    assert '"can_review": False' in fail_closed
    assert '"can_save": False' in fail_closed

    binding_start = source.index("def _canonical_refresh_binding_matches_authority(")
    binding_end = source.index("\ndef _persisted_refresh_authorization_for_binding(", binding_start)
    binding = source[binding_start:binding_end]
    assert "proposal_binding == binding" in binding
    assert "refresh_preparation_bindings_match_authority(" in binding
