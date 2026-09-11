from __future__ import annotations

from collections.abc import Sequence
from typing import cast

from wilq.content.operator_copy import build_blocker
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.quality.deterministic_revision_gate import (
    ContentDeterministicRevisionGate,
    deterministic_gate_for_snapshot,
)
from wilq.content.quality.semantic_review_contracts import (
    ContentSemanticBlockerCode,
    ContentSemanticReviewBlocker,
)
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.documents.revisions import ContentDraftRevision


def semantic_blocker_code(code: str) -> ContentSemanticBlockerCode:
    return cast(ContentSemanticBlockerCode, code)


def missing_revision_blocker() -> ContentSemanticReviewBlocker:
    return build_blocker(
        ContentSemanticReviewBlocker,
        code=semantic_blocker_code("missing_revision"),
        label="Brakuje pełnej wersji do review",
        reason="Review semantyczne wymaga zapisanej exact revision.",
        next_step="Najpierw wygeneruj pełny dokument.",
    )


def planning_blocker(source_codes: Sequence[str] | None = None) -> ContentSemanticReviewBlocker:
    return build_blocker(
        ContentSemanticReviewBlocker,
        code=semantic_blocker_code("missing_planning_input"),
        label="Brakuje aktualnego wejścia strategicznego",
        reason="Review musi porównać rewizję z tym samym planem, usługą, inventory i metrykami.",
        next_step="Odśwież albo wygeneruj aktualny plan przed review semantycznym.",
        source_codes=source_codes,
    )


def source_material_review_blocker(
    source_codes: Sequence[str],
) -> ContentSemanticReviewBlocker:
    return build_blocker(
        ContentSemanticReviewBlocker,
        code=semantic_blocker_code("source_material_review_required"),
        label="Materiał źródłowy wymaga potwierdzenia",
        reason="Rewizja korzysta z publicznego materiału WordPress, którego pochodzenie "
        "nie zostało jeszcze zatwierdzone do pełnego dokumentu.",
        next_step=(
            "Zakończ kontrolowany import/redakcję i owner review materiału, "
            "potem uruchom review ponownie."
        ),
        source_codes=source_codes,
    )


def storage_blocker() -> ContentSemanticReviewBlocker:
    return build_blocker(
        ContentSemanticReviewBlocker,
        code=semantic_blocker_code("storage_activation_required"),
        label="Storage review czeka na maintenance window",
        reason="Realny local state nie ma jeszcze aktywowanej tabeli immutable semantic review.",
        next_step="Użyj tymczasowego storage do proof albo zatwierdź backup i maintenance window.",
    )


def deterministic_quality_gate_blocker(
    gate: ContentDeterministicRevisionGate,
) -> ContentSemanticReviewBlocker:
    codes = [item.code for item in gate.findings if item.severity != "info"]
    return build_blocker(
        ContentSemanticReviewBlocker,
        code=semantic_blocker_code("deterministic_quality_gate_failed"),
        label="Deterministyczna bramka jakości zatrzymała review",
        reason=(
            "Exact revision nie może przejść do judge/model review. "
            + ("; ".join(codes) or "gate_failed")
        ),
        next_step=gate.safe_next_step,
        source_codes=[item.code for item in gate.findings],
    )


def deterministic_quality_gate_for_snapshot(
    *,
    snapshot: object,
    revision: ContentDraftRevision,
    planning_input: ContentPlanningInput,
    planning_proposal: ContentPlanningProposal,
) -> ContentSemanticReviewBlocker | None:
    gate = deterministic_gate_for_snapshot(
        snapshot=snapshot,
        revision=revision,
        planning_input=planning_input,
        planning_proposal=planning_proposal,
    )
    if gate is None or gate.status != "blocked":
        return None
    return deterministic_quality_gate_blocker(gate)


def semantic_planning_input_blocker(
    planning_result: object,
    expected_digest: str | None,
) -> ContentSemanticReviewBlocker | None:
    planning_input = getattr(planning_result, "planning_input", None)
    blockers = list(getattr(planning_result, "blockers", []))
    if (
        planning_input is None
        or blockers
        or planning_input.planning_input_digest != expected_digest
    ):
        source_codes = [item.code for item in blockers]
        return (
            source_material_review_blocker(source_codes)
            if "wordpress_material_review_required" in source_codes
            else planning_blocker(source_codes)
        )
    return None


__all__ = [
    "missing_revision_blocker",
    "planning_blocker",
    "semantic_blocker_code",
    "source_material_review_blocker",
    "storage_blocker",
    "deterministic_quality_gate_blocker",
    "deterministic_quality_gate_for_snapshot",
    "semantic_planning_input_blocker",
]
