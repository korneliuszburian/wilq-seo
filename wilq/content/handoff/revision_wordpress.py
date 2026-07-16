from __future__ import annotations

from collections.abc import Iterable

from wilq.content.canonical.urls import CONTENT_SOURCE_SITE_HOSTS, content_url_host
from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.handoff.wordpress import (
    ContentWordPressDraftHandoff,
    ContentWordPressDraftHandoffBlocker,
    ContentWordPressDraftHandoffResult,
)
from wilq.content.workflow.models import ContentWorkItem
from wilq.content.workflow.revision_binding import ContentDraftRevisionBinding
from wilq.content.workflow.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionReview,
    ContentDraftRevisionState,
    content_draft_package_digest,
)


def build_revision_bound_wordpress_draft_handoff(
    *,
    item: ContentWorkItem,
    draft_package: ContentDraftPackage | None,
    revision_state: ContentDraftRevisionState,
    planning_digest: str | None,
    planning_input_digest: str | None,
    service_card_id: str | None,
) -> ContentWordPressDraftHandoffResult:
    """Prepare a draft-only handoff from one exact approved immutable revision."""
    blockers = revision_bound_wordpress_draft_handoff_blockers(
        item=item,
        draft_package=draft_package,
        revision_state=revision_state,
        planning_digest=planning_digest,
        planning_input_digest=planning_input_digest,
        service_card_id=service_card_id,
    )
    if blockers:
        return ContentWordPressDraftHandoffResult(blockers=blockers)

    revision = revision_state.latest_revision
    approval = revision_state.latest_review
    if (
        revision is None
        or approval is None
        or draft_package is None
        or revision.planning_digest is None
    ):
        raise RuntimeError("Approved revision handoff passed blockers without exact inputs.")

    handoff_id = f"wordpress_draft_handoff_{item.id}_{revision.revision_id}"
    binding = ContentDraftRevisionBinding(
        work_item_id=item.id,
        handoff_id=handoff_id,
        revision_id=revision.revision_id,
        content_digest=revision.content_digest,
        draft_package_id=revision.draft_package_id,
        draft_package_digest=revision.draft_package_digest,
        planning_digest=revision.planning_digest,
        approval_decision_id=approval.decision_id,
        final_canonical_url=revision.final_canonical_url,
    )
    revision_evidence = _revision_evidence_ids(revision)
    return ContentWordPressDraftHandoffResult(
        handoff=ContentWordPressDraftHandoff(
            id=handoff_id,
            work_item_id=item.id,
            draft_package_id=draft_package.id,
            title=revision.title,
            final_canonical_url=revision.final_canonical_url,
            intended_final_url=item.intended_final_url,
            preview_url=item.preview_url,
            evidence_ids=revision_evidence,
            revision_binding=binding,
            revision_sections=[section.model_copy(deep=True) for section in revision.sections],
            revision_document=revision.model_copy(deep=True),
        )
    )


def revision_bound_wordpress_draft_handoff_blockers(
    *,
    item: ContentWorkItem,
    draft_package: ContentDraftPackage | None,
    revision_state: ContentDraftRevisionState,
    planning_digest: str | None,
    planning_input_digest: str | None,
    service_card_id: str | None,
) -> list[ContentWordPressDraftHandoffBlocker]:
    blockers: list[ContentWordPressDraftHandoffBlocker] = []
    revision = revision_state.latest_revision
    approval = revision_state.latest_review

    if revision is None:
        return [
            _blocker(
                "missing_revision",
                "Brakuje zapisanej wersji treści",
                "WordPress może otrzymać tylko dokładną zapisaną wersję tekstu.",
                "Zapisz wersję treści i przekaż ją do sprawdzenia.",
            )
        ]
    if revision_state.status != "approved" or approval is None:
        blockers.append(
            _blocker(
                "revision_not_approved",
                "Wersja nie jest zatwierdzona",
                "Przekazanie wymaga decyzji zatwierdzającej dokładnie tę wersję tekstu.",
                "Sprawdź zapisaną wersję i zapisz decyzję człowieka.",
            )
        )

    blockers.extend(_planning_binding_blockers(revision))

    if item.canonical_status != "resolved" or not item.final_canonical_url:
        blockers.append(
            _blocker(
                "missing_final_canonical",
                "Brakuje finalnego adresu",
                "Szkic WordPress wymaga publicznego finalnego adresu Ekologus.",
                "Ustal publiczny adres Ekologus przed przekazaniem szkicu.",
            )
        )
    elif content_url_host(item.final_canonical_url) not in CONTENT_SOURCE_SITE_HOSTS:
        blockers.append(
            _blocker(
                "invalid_final_canonical",
                "Adres podglądu nie może być canonical",
                "Finalny adres szkicu musi prowadzić do publicznego hosta Ekologus.",
                "Ustaw finalny adres na publiczny adres Ekologus.",
            )
        )

    if draft_package is None:
        blockers.append(
            _blocker(
                "missing_draft_package",
                "Brakuje paczki szkicu",
                "Nie można potwierdzić planu sekcji zatwierdzonej wersji.",
                "Odtwórz paczkę szkicu powiązaną z zapisaną wersją.",
            )
        )
    elif draft_package.publish_ready:
        blockers.append(
            _blocker(
                "draft_package_marked_publish_ready",
                "Szkic nie może udawać gotowości do publikacji",
                "Ten krok może utworzyć wyłącznie szkic WordPress.",
                "Pozostaw paczkę jako draft-only i przejdź przez bezpieczny zapis.",
            )
        )

    context_current = _revision_context_is_current(
        item=item,
        draft_package=draft_package,
        revision=revision,
        planning_digest=planning_digest,
        planning_input_digest=planning_input_digest,
        service_card_id=service_card_id,
    )
    if not context_current:
        blockers.append(
            _blocker(
                "revision_context_changed",
                "Kontekst zatwierdzonej wersji zmienił się",
                "Adres strony albo paczka sekcji nie odpowiada już zatwierdzonej wersji.",
                "Zapisz i zatwierdź nową wersję dla aktualnego adresu i planu sekcji.",
            )
        )

    revision_evidence = set(_revision_evidence_ids(revision))
    blockers.extend(_approval_evidence_blockers(approval, revision_evidence))
    return blockers


def _revision_context_is_current(
    *,
    item: ContentWorkItem,
    draft_package: ContentDraftPackage | None,
    revision: ContentDraftRevision,
    planning_digest: str | None,
    planning_input_digest: str | None,
    service_card_id: str | None,
) -> bool:
    baseline_current = bool(
        draft_package is not None
        and item.final_canonical_url
        and revision.work_item_id == item.id
        and draft_package.work_item_id == item.id
        and revision.draft_package_id == draft_package.id
        and revision.draft_package_digest == content_draft_package_digest(draft_package)
        and revision.planning_digest == planning_digest
        and revision.final_canonical_url == item.final_canonical_url
        and [(section.heading, section.evidence_ids) for section in revision.sections]
        == [(section.heading, section.evidence_ids) for section in draft_package.sections]
    )
    if not baseline_current or revision.schema_version == "wilq_content_draft_revision_v1":
        return baseline_current
    return bool(
        revision.planning_input_digest == planning_input_digest
        and revision.service_card_id == service_card_id
    )


def _planning_binding_blockers(
    revision: ContentDraftRevision,
) -> list[ContentWordPressDraftHandoffBlocker]:
    if revision.planning_digest is not None:
        return []
    return [
        _blocker(
            "missing_planning_binding",
            "Wersja nie jest powiązana z zatwierdzonym planem",
            "Starsza wersja nie wskazuje dokładnego zakresu i mapy sekcji.",
            "Zapisz nową wersję po zatwierdzeniu aktualnego zakresu i planu sekcji.",
        )
    ]


def _approval_evidence_blockers(
    approval: ContentDraftRevisionReview | None,
    revision_evidence: set[str],
) -> list[ContentWordPressDraftHandoffBlocker]:
    if approval is None or set(approval.evidence_ids).issubset(revision_evidence):
        return []
    return [
        _blocker(
            "revision_approval_mismatch",
            "Decyzja nie pasuje do dowodów wersji",
            "Zatwierdzenie wskazuje dowody spoza dokładnej zapisanej wersji.",
            "Sprawdź ponownie tę wersję, używając wyłącznie jej powiązanych dowodów.",
        )
    ]


def _revision_evidence_ids(revision: ContentDraftRevision) -> list[str]:
    return _unique(
        [
            *(evidence_id for section in revision.sections for evidence_id in section.evidence_ids),
            *(evidence_id for item in revision.faq for evidence_id in item.evidence_ids),
            *(evidence_id for item in revision.cta_blocks for evidence_id in item.evidence_ids),
            *(evidence_id for item in revision.internal_links for evidence_id in item.evidence_ids),
        ]
    )


def _unique(values: Iterable[str]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        if value and value not in unique_values:
            unique_values.append(value)
    return unique_values


def _blocker(
    code: str,
    label: str,
    reason: str,
    next_step: str,
) -> ContentWordPressDraftHandoffBlocker:
    return ContentWordPressDraftHandoffBlocker.model_validate(
        {
            "code": code,
            "label": label,
            "reason": reason,
            "next_step": next_step,
        }
    )
