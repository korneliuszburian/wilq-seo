from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from pydantic import BaseModel, Field

from wilq.content.canonical.urls import CONTENT_SOURCE_SITE_HOSTS, content_url_host
from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.review.human import (
    ContentHumanReview,
    content_human_review_allows_wordpress_handoff,
    content_human_review_blockers,
)
from wilq.content.workflow.models import ContentWorkItem
from wilq.content.workflow.revision_binding import ContentDraftRevisionBinding
from wilq.content.workflow.revisions import ContentDraftRevisionSection

ContentWordPressDraftActor = Literal["wilku", "system", "codex"]
ContentWordPressDraftHandoffStatus = Literal["prepared"]
ContentWordPressDraftHandoffBlockerCode = Literal[
    "missing_planning_binding",
    "missing_final_canonical",
    "invalid_final_canonical",
    "missing_draft_package",
    "draft_package_mismatch",
    "draft_package_marked_publish_ready",
    "missing_human_review",
    "human_review_not_approved",
    "missing_audit",
    "audit_human_review_mismatch",
    "missing_audit_evidence",
    "audit_evidence_mismatch",
    "missing_revision",
    "revision_not_approved",
    "revision_context_changed",
    "revision_approval_mismatch",
]


class ContentWordPressDraftAuditEnvelope(BaseModel):
    audit_id: str
    actor: ContentWordPressDraftActor
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)
    human_review_id: str


class ContentWordPressDraftHandoff(BaseModel):
    id: str
    work_item_id: str
    draft_package_id: str
    human_review_id: str | None = None
    audit_id: str | None = None
    connector: Literal["wordpress_ekologus"] = "wordpress_ekologus"
    operation_type: Literal["create_wordpress_draft"] = "create_wordpress_draft"
    status: ContentWordPressDraftHandoffStatus = "prepared"
    post_status: Literal["draft"] = "draft"
    title: str
    final_canonical_url: str
    intended_final_url: str | None = None
    preview_url: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    revision_binding: ContentDraftRevisionBinding | None = None
    revision_sections: list[ContentDraftRevisionSection] = Field(default_factory=list)
    publish_allowed: bool = False
    destructive_update_allowed: bool = False


class ContentWordPressDraftHandoffBlocker(BaseModel):
    code: ContentWordPressDraftHandoffBlockerCode
    label: str
    reason: str
    next_step: str


class ContentWordPressDraftHandoffResult(BaseModel):
    handoff: ContentWordPressDraftHandoff | None = None
    blockers: list[ContentWordPressDraftHandoffBlocker] = Field(default_factory=list)


def build_content_wordpress_draft_handoff(
    *,
    item: ContentWorkItem,
    draft_package: ContentDraftPackage | None,
    human_review: ContentHumanReview | None,
    audit: ContentWordPressDraftAuditEnvelope | None,
) -> ContentWordPressDraftHandoffResult:
    blockers = content_wordpress_draft_handoff_blockers(
        item=item,
        draft_package=draft_package,
        human_review=human_review,
        audit=audit,
    )
    if blockers:
        return ContentWordPressDraftHandoffResult(blockers=blockers)

    if draft_package is None:
        raise RuntimeError("Draft package passed WordPress handoff blockers as None.")
    if human_review is None:
        raise RuntimeError("Human review passed WordPress handoff blockers as None.")
    if audit is None:
        raise RuntimeError("Audit envelope passed WordPress handoff blockers as None.")
    if item.final_canonical_url is None:
        raise RuntimeError("Final canonical URL passed WordPress handoff blockers as None.")
    return ContentWordPressDraftHandoffResult(
        handoff=ContentWordPressDraftHandoff(
            id=f"wordpress_draft_handoff_{item.id}",
            work_item_id=item.id,
            draft_package_id=draft_package.id,
            human_review_id=human_review.id,
            audit_id=audit.audit_id,
            title=draft_package.title,
            final_canonical_url=item.final_canonical_url,
            intended_final_url=item.intended_final_url,
            preview_url=item.preview_url,
            evidence_ids=_unique([*item.evidence_ids, *draft_package_evidence(draft_package)]),
        )
    )


def content_wordpress_draft_handoff_blockers(
    *,
    item: ContentWorkItem,
    draft_package: ContentDraftPackage | None,
    human_review: ContentHumanReview | None,
    audit: ContentWordPressDraftAuditEnvelope | None,
) -> list[ContentWordPressDraftHandoffBlocker]:
    blockers: list[ContentWordPressDraftHandoffBlocker] = []
    blockers.extend(_final_url_blockers(item))
    blockers.extend(_draft_package_blockers(item, draft_package))
    blockers.extend(_human_review_blockers(item, draft_package, human_review))
    blockers.extend(_audit_blockers(audit, human_review, draft_package))
    return blockers


def apply_content_wordpress_draft_handoff_to_work_item(
    item: ContentWorkItem,
    handoff: ContentWordPressDraftHandoff,
    *,
    wordpress_post_id: str | None = None,
) -> ContentWorkItem:
    return item.model_copy(
        update={
            "wordpress_handoff_status": "draft_created" if wordpress_post_id else "prepared",
            "wordpress_post_id": wordpress_post_id,
        }
    )


def draft_package_evidence(draft_package: ContentDraftPackage) -> list[str]:
    evidence_ids: list[str] = []
    for mapping in draft_package.section_to_evidence_map:
        evidence_ids.extend(mapping.evidence_ids)
    return _unique(evidence_ids)


def _final_url_blockers(item: ContentWorkItem) -> list[ContentWordPressDraftHandoffBlocker]:
    if item.canonical_status != "resolved" or not item.final_canonical_url:
        return [
            _blocker(
                "missing_final_canonical",
                "Brakuje finalnego adresu",
                "Szkic WordPress nie może powstać bez publicznego finalnego adresu.",
                "Ustal publiczny adres Ekologus przed przekazaniem szkicu.",
            )
        ]
    if content_url_host(item.final_canonical_url) not in CONTENT_SOURCE_SITE_HOSTS:
        return [
            _blocker(
                "invalid_final_canonical",
                "Adres podglądu nie może być canonical",
                "Adres podglądu ani adres techniczny nie może być finalnym adresem "
                "szkicu WordPress.",
                "Ustaw finalny adres na publiczny adres Ekologus.",
            )
        ]
    return []


def _draft_package_blockers(
    item: ContentWorkItem,
    draft_package: ContentDraftPackage | None,
) -> list[ContentWordPressDraftHandoffBlocker]:
    if draft_package is None:
        return [
            _blocker(
                "missing_draft_package",
                "Brakuje paczki szkicu",
                "Przekazanie do WordPress wymaga gotowej paczki szkicu.",
                "Przygotuj paczkę szkicu przed przekazaniem do WordPress.",
            )
        ]
    blockers: list[ContentWordPressDraftHandoffBlocker] = []
    if draft_package.work_item_id != item.id or (
        item.draft_package_id is not None and draft_package.id != item.draft_package_id
    ):
        blockers.append(
            _blocker(
                "draft_package_mismatch",
                "Paczka szkicu nie pasuje do tematu",
                "Przekazanie do WordPress musi używać paczki szkicu dla tego samego tematu.",
                "Podaj paczkę szkicu zgodną z tematem.",
            )
        )
    if draft_package.publish_ready:
        blockers.append(
            _blocker(
                "draft_package_marked_publish_ready",
                "Szkic nie może udawać gotowości do publikacji",
                "Przekazanie do WordPress tworzy wyłącznie szkic; publikacja jest "
                "osobnym procesem.",
                "Zatrzymaj status publikacji i przejdź przez sprawdzenie człowieka.",
            )
        )
    return blockers


def _human_review_blockers(
    item: ContentWorkItem,
    draft_package: ContentDraftPackage | None,
    human_review: ContentHumanReview | None,
) -> list[ContentWordPressDraftHandoffBlocker]:
    if human_review is None:
        return [
            _blocker(
                "missing_human_review",
                "Brakuje decyzji człowieka",
                "Przekazanie do WordPress nie może ruszyć bez zatwierdzenia przez człowieka.",
                "Zatwierdź szkic i ryzykowne twierdzenia przed przekazaniem.",
            )
        ]
    if not content_human_review_allows_wordpress_handoff(
        item=item,
        review=human_review,
        draft_package=draft_package,
    ):
        details = content_human_review_blockers(
            item=item,
            review=human_review,
            draft_package=draft_package,
        )
        return [
            _blocker(
                "human_review_not_approved",
                "Decyzja człowieka nie odblokowuje WordPress",
                "Sprawdzenie musi mieć zatwierdzenie, checklistę, dowody i obsłużone "
                "ryzykowne twierdzenia.",
                "Rozwiąż sprawdzenie: "
                + ", ".join(_unique(blocker.label for blocker in details)),
            )
        ]
    return []


def _audit_blockers(
    audit: ContentWordPressDraftAuditEnvelope | None,
    human_review: ContentHumanReview | None,
    draft_package: ContentDraftPackage | None,
) -> list[ContentWordPressDraftHandoffBlocker]:
    if audit is None:
        return [
            _blocker(
                "missing_audit",
                "Brakuje audytu",
                "Każde przekazanie do WordPress musi mieć zapis audytu.",
                "Zapisz identyfikator audytu, osobę wykonującą, powód, dowody i "
                "powiązane sprawdzenie.",
            )
        ]
    blockers: list[ContentWordPressDraftHandoffBlocker] = []
    if not audit.evidence_ids:
        blockers.append(
            _blocker(
                "missing_audit_evidence",
                "Audyt nie ma dowodów",
                "Zapis audytu musi zachować dowody użyte przy decyzji.",
                "Dodaj dowody do audytu.",
            )
        )
    else:
        audit_evidence = set(audit.evidence_ids)
        if (
            human_review is not None
            and human_review.evidence_ids
            and audit_evidence.isdisjoint(human_review.evidence_ids)
        ):
            blockers.append(
                _blocker(
                    "audit_evidence_mismatch",
                    "Audyt nie wskazuje sprawdzonych dowodów",
                    "Audyt przekazania musi zachować dowody, które sprawdził człowiek.",
                    "Powiąż audyt z dowodami ze sprawdzenia człowieka.",
                )
            )
        if draft_package is not None:
            draft_evidence = set(draft_package_evidence(draft_package))
            if draft_evidence and audit_evidence.isdisjoint(draft_evidence):
                blockers.append(
                    _blocker(
                        "audit_evidence_mismatch",
                        "Audyt nie wskazuje dowodów szkicu",
                        "Audyt przekazania musi zachować dowody użyte w paczce szkicu.",
                        "Powiąż audyt z dowodami z paczki szkicu.",
                    )
                )
    if human_review is not None and audit.human_review_id != human_review.id:
        blockers.append(
            _blocker(
                "audit_human_review_mismatch",
                "Audyt wskazuje inne sprawdzenie",
                "Zapis audytu musi wskazywać sprawdzenie człowieka, które odblokowało przekazanie.",
                "Powiąż audyt z zatwierdzonym sprawdzeniem człowieka.",
            )
        )
    return blockers


def _unique(values: Iterable[str]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        if value and value not in unique_values:
            unique_values.append(value)
    return unique_values


def _blocker(
    code: ContentWordPressDraftHandoffBlockerCode,
    label: str,
    reason: str,
    next_step: str,
) -> ContentWordPressDraftHandoffBlocker:
    return ContentWordPressDraftHandoffBlocker(
        code=code,
        label=label,
        reason=reason,
        next_step=next_step,
    )
