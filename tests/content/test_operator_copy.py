from wilq.content.drafts.codex_section_proposal_contracts import (
    ContentCodexSectionProposalBlocker,
)
from wilq.content.drafts.package import ContentDraftPackageBlocker
from wilq.content.operator_copy import build_blocker, unique


def test_unique_stringifies_skips_empty_and_preserves_first_occurrence() -> None:
    assert unique([1, "1", "", None, "x", "x", 2]) == ["1", "None", "x", "2"]


def test_unique_matches_string_only_keep_for_string_inputs() -> None:
    assert unique(["source_a", "source_a", "source_b", ""]) == [
        "source_a",
        "source_b",
    ]


def test_build_blocker_preserves_models_with_and_without_source_codes() -> None:
    with_source_codes = build_blocker(
        ContentCodexSectionProposalBlocker,
        code="runtime_failed",
        label="Niepowodzenie runtime",
        reason="Brakuje bezpiecznego wyniku.",
        next_step="Uruchom ponownie.",
        source_codes=("runtime_failed", "runtime_failed"),
    )
    without_source_codes = build_blocker(
        ContentDraftPackageBlocker,
        code="missing_sales_brief",
        label="Brakuje planu",
        reason="Nie ma planu.",
        next_step="Uzupełnij plan.",
        source_codes=["ignored_for_this_model"],
    )

    assert with_source_codes == ContentCodexSectionProposalBlocker(
        code="runtime_failed",
        label="Niepowodzenie runtime",
        reason="Brakuje bezpiecznego wyniku.",
        next_step="Uruchom ponownie.",
        source_codes=["runtime_failed", "runtime_failed"],
    )
    assert without_source_codes == ContentDraftPackageBlocker(
        code="missing_sales_brief",
        label="Brakuje planu",
        reason="Nie ma planu.",
        next_step="Uzupełnij plan.",
    )
