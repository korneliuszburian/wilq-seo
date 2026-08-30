from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftApprovedReview,
    ContentInitialDraftBlocker,
    ContentInitialDraftBlockerCode,
    ContentInitialDraftResponse,
    ContentInitialDraftReuseBinding,
)
from wilq.content.workflow.decisions.production import ClassificationLookupBasis
from wilq.content.workflow.decisions.production_reuse import ProductionReuseBlockCode
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionReview,
)

InitialDraftAuthorityConflictCode = Literal[
    "production_classification_missing",
    "production_classification_item_missing",
    "production_classification_digest_required",
    "stale_production_classification",
]
InitialDraftAuthorityBlockCode = (
    ProductionReuseBlockCode
    | Literal[
        "production_generation_disabled",
        "stale_production_classification",
    ]
)


@dataclass(frozen=True, slots=True)
class StatusRead:
    kind: Literal["status_read"] = field(default="status_read", init=False)


@dataclass(frozen=True, slots=True)
class SubmitExpectation:
    expected_production_classification_run_digest: str | None
    kind: Literal["submit_expectation"] = field(default="submit_expectation", init=False)


InitialDraftAuthorityIntent = StatusRead | SubmitExpectation


@dataclass(frozen=True, slots=True)
class InitialDraftAuthorityUnclassified:
    requested_work_item_id: str
    status: Literal["unclassified"] = field(default="unclassified", init=False)


@dataclass(frozen=True, slots=True)
class InitialDraftAuthorityConflict:
    requested_work_item_id: str
    code: InitialDraftAuthorityConflictCode
    status: Literal["conflict"] = field(default="conflict", init=False)


@dataclass(frozen=True, slots=True)
class InitialDraftAuthorityBlocked:
    requested_work_item_id: str
    code: InitialDraftAuthorityBlockCode
    reason_pl: str | None = None
    safe_next_step_pl: str | None = None
    source_codes: tuple[str, ...] = ()
    classification_decision: Literal["reuse", "refresh", "write", "blocked"] | None = None
    status: Literal["blocked"] = field(default="blocked", init=False)


@dataclass(frozen=True, slots=True)
class InitialDraftAuthorityReused:
    classification_run_id: str
    classification_run_digest: str
    decision_set_digest: str
    requested_work_item_id: str
    lookup_basis: ClassificationLookupBasis
    current_work_item_id: str
    retained_work_item_id: str | None
    revision_work_item_id: str
    identity_reconciliation_status: Literal["fork", "retained_missing"]
    revision: ContentDraftRevision
    approved_review: ContentDraftRevisionReview
    status: Literal["reused"] = field(default="reused", init=False)


InitialDraftAuthorityResolution = (
    InitialDraftAuthorityUnclassified
    | InitialDraftAuthorityConflict
    | InitialDraftAuthorityBlocked
    | InitialDraftAuthorityReused
)


def map_initial_draft_authority_response(
    resolution: InitialDraftAuthorityResolution,
) -> ContentInitialDraftResponse | None:
    if isinstance(resolution, InitialDraftAuthorityUnclassified):
        return None
    if isinstance(resolution, InitialDraftAuthorityReused):
        revision = resolution.revision
        binding = ContentInitialDraftReuseBinding(
            classification_run_id=resolution.classification_run_id,
            classification_run_digest=resolution.classification_run_digest,
            decision_set_digest=resolution.decision_set_digest,
            requested_work_item_id=resolution.requested_work_item_id,
            lookup_basis=resolution.lookup_basis,
            current_work_item_id=resolution.current_work_item_id,
            retained_work_item_id=resolution.retained_work_item_id,
            revision_work_item_id=resolution.revision_work_item_id,
            identity_reconciliation_status=resolution.identity_reconciliation_status,
            revision_id=revision.revision_id,
            revision_digest=revision.content_digest,
            approved_review=ContentInitialDraftApprovedReview.model_validate(
                resolution.approved_review.model_dump(mode="python")
            ),
            must_not_regenerate=True,
        )
        return ContentInitialDraftResponse(
            status="reused",
            work_item_id=resolution.current_work_item_id,
            proposal_id=None,
            run_id=None,
            revision=revision,
            reuse_binding=binding,
            blockers=[],
            safe_next_step=(
                "Otwórz dokładną zatwierdzoną rewizję do przeglądu; nie generuj nowej treści."
            ),
        )
    blocker = _authority_blocker(resolution)
    return ContentInitialDraftResponse(
        status="conflict" if isinstance(resolution, InitialDraftAuthorityConflict) else "blocked",
        work_item_id=resolution.requested_work_item_id,
        proposal_id=None,
        run_id=None,
        revision=None,
        reuse_binding=None,
        blockers=[blocker],
        safe_next_step=blocker.next_step,
    )


def _authority_blocker(
    resolution: InitialDraftAuthorityConflict | InitialDraftAuthorityBlocked,
) -> ContentInitialDraftBlocker:
    copy = _authority_blocker_copy(resolution)
    return ContentInitialDraftBlocker(
        code=resolution.code,
        label=copy[0],
        reason=copy[1],
        next_step=copy[2],
        source_codes=(
            []
            if isinstance(resolution, InitialDraftAuthorityConflict)
            else list(resolution.source_codes)
        ),
    )


def _authority_blocker_copy(
    resolution: InitialDraftAuthorityConflict | InitialDraftAuthorityBlocked,
) -> tuple[str, str, str]:
    if isinstance(resolution, InitialDraftAuthorityBlocked) and resolution.reason_pl:
        next_step = resolution.safe_next_step_pl or (
            "Sprawdź zaakceptowaną klasyfikację przed dalszą pracą."
        )
        return ("Generowanie treści jest wyłączone", resolution.reason_pl, next_step)
    copy: dict[ContentInitialDraftBlockerCode, tuple[str, str, str]] = {
        "production_classification_missing": (
            "Brakuje klasyfikacji produkcyjnej",
            "Żądanie ponownego użycia nie ma zaakceptowanej klasyfikacji produkcyjnej.",
            "Odśwież workspace i użyj aktualnego kontraktu dla niesklasyfikowanej pracy.",
        ),
        "production_classification_digest_required": (
            "Wymagany jest digest klasyfikacji",
            "Chroniona praca wymaga jawnego związania żądania z aktualną klasyfikacją.",
            "Odśwież workspace i ponów jako żądanie ponownego użycia.",
        ),
        "stale_production_classification": (
            "Klasyfikacja produkcyjna zmieniła się",
            "Żądanie wskazuje inną wersję klasyfikacji niż najnowsza zaakceptowana wersja.",
            "Odśwież workspace przed dalszą pracą.",
        ),
        "production_classification_item_missing": (
            "Brakuje pozycji w klasyfikacji",
            "Najnowsza klasyfikacja nie zawiera żądanej tożsamości pracy.",
            "Sprawdź zakres klasyfikacji i tożsamość pozycji przed dalszą pracą.",
        ),
    }
    if resolution.code in copy:
        return copy[resolution.code]
    return (
        "Nie można ponownie użyć zachowanego dokumentu",
        "Zachowana rewizja albo jej review nie odpowiada zaakceptowanej klasyfikacji.",
        "Wyjaśnij rozbieżność dokładnej rewizji i review; nie generuj treści zastępczej.",
    )


__all__ = [
    "InitialDraftAuthorityBlocked",
    "InitialDraftAuthorityConflict",
    "InitialDraftAuthorityIntent",
    "InitialDraftAuthorityResolution",
    "InitialDraftAuthorityReused",
    "InitialDraftAuthorityUnclassified",
    "StatusRead",
    "SubmitExpectation",
    "map_initial_draft_authority_response",
]
