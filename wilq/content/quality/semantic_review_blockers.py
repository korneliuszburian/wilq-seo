from __future__ import annotations

from collections.abc import Sequence
from typing import cast

from wilq.content.operator_copy import build_blocker
from wilq.content.quality.semantic_review_contracts import (
    ContentSemanticBlockerCode,
    ContentSemanticReviewBlocker,
)


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


__all__ = [
    "missing_revision_blocker",
    "planning_blocker",
    "semantic_blocker_code",
    "source_material_review_blocker",
    "storage_blocker",
]
