from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from wilq.content.drafts.structured_generation import StructuredDraftOutput
from wilq.content.quality.review import ContentQualityReview
from wilq.content.quality.revision import ContentRevisionPlan
from wilq.content.workflow.models import ContentWorkItem

ContentRevisionApplicationStatus = Literal["blocked", "applied"]
ContentRevisionApplicationBlockerCode = Literal[
    "missing_revision_plan",
    "revision_plan_not_ready",
    "revision_plan_mismatch",
    "missing_draft_output",
    "missing_updated_quality_review",
    "updated_quality_review_mismatch",
    "updated_quality_review_not_reviewable",
]


class ContentRevisionDiffEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instruction_id: str
    affected_section: str | None = None
    change: str
    reason: str
    before_summary: str
    after_summary: str
    evidence_ids: list[str] = Field(default_factory=list)


class ContentRevisionApplicationBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ContentRevisionApplicationBlockerCode
    label: str
    reason: str
    next_step: str


class ContentRevisionApplication(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    work_item_id: str
    revision_plan_id: str | None = None
    previous_version_id: str | None = None
    revised_version_id: str | None = None
    status: ContentRevisionApplicationStatus
    diff: list[ContentRevisionDiffEntry] = Field(default_factory=list)
    updated_quality_review_id: str | None = None
    quality_review_rerun_required: bool = True
    publish_ready: Literal[False] = False
    wordpress_write_allowed: Literal[False] = False
    blockers: list[ContentRevisionApplicationBlocker] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    safe_next_step: str


def apply_content_revision_plan(
    *,
    item: ContentWorkItem,
    revision_plan: ContentRevisionPlan | None,
    draft_output: StructuredDraftOutput | None,
    updated_quality_review: ContentQualityReview | None = None,
) -> ContentRevisionApplication:
    blockers = _revision_application_blockers(
        item=item,
        revision_plan=revision_plan,
        draft_output=draft_output,
        updated_quality_review=updated_quality_review,
    )
    if blockers:
        return _application(
            item=item,
            revision_plan=revision_plan,
            draft_output=draft_output,
            status="blocked",
            blockers=blockers,
            safe_next_step=blockers[0].next_step,
        )
    if revision_plan is None or draft_output is None or updated_quality_review is None:
        raise RuntimeError("Revision application passed blockers with missing input.")
    return _application(
        item=item,
        revision_plan=revision_plan,
        draft_output=draft_output,
        status="applied",
        diff=_diff_entries(revision_plan, draft_output),
        updated_quality_review=updated_quality_review,
        safe_next_step=(
            "Poprawka została zastosowana jako wersja robocza. "
            "Przekaż ją do sprawdzenia człowieka dopiero po review."
        ),
    )


def _revision_application_blockers(
    *,
    item: ContentWorkItem,
    revision_plan: ContentRevisionPlan | None,
    draft_output: StructuredDraftOutput | None,
    updated_quality_review: ContentQualityReview | None,
) -> list[ContentRevisionApplicationBlocker]:
    blockers: list[ContentRevisionApplicationBlocker] = []
    if revision_plan is None:
        blockers.append(
            _blocker(
                "missing_revision_plan",
                "Brakuje planu poprawki",
                "Poprawka musi wynikać z bounded revision plan, nie z wolnej regeneracji.",
                "Najpierw zbuduj plan poprawki z oceny jakości.",
            )
        )
    elif revision_plan.work_item_id != item.id:
        blockers.append(
            _blocker(
                "revision_plan_mismatch",
                "Plan poprawki dotyczy innego tematu",
                "Nie wolno stosować poprawek między work itemami.",
                "Użyj planu poprawki przypisanego do aktualnego work itemu.",
            )
        )
    elif revision_plan.status != "ready" or not revision_plan.draft_revision_allowed:
        blockers.append(
            _blocker(
                "revision_plan_not_ready",
                "Plan poprawki nie pozwala na zmianę",
                "WILQ może zastosować tylko plan ze statusem ready.",
                revision_plan.safe_next_step,
            )
        )
    if draft_output is None:
        blockers.append(
            _blocker(
                "missing_draft_output",
                "Brakuje szkicu do poprawki",
                "Aplikacja poprawki musi działać na konkretnym structured draft.",
                "Podaj szkic z runtime WILQ przed poprawką.",
            )
        )
    if updated_quality_review is None:
        blockers.append(
            _blocker(
                "missing_updated_quality_review",
                "Brakuje ponownej oceny jakości",
                "Po poprawce WILQ musi uruchomić quality review jeszcze raz.",
                "Uruchom ocenę jakości poprawionej wersji przed dalszym etapem.",
            )
        )
    elif updated_quality_review.work_item_id != item.id:
        blockers.append(
            _blocker(
                "updated_quality_review_mismatch",
                "Ponowna ocena dotyczy innego tematu",
                "Nie wolno odblokować poprawki oceną z innego work itemu.",
                "Uruchom quality review dla aktualnego work itemu.",
            )
        )
    elif updated_quality_review.verdict not in {"reviewable", "ready_for_human_review"}:
        blockers.append(
            _blocker(
                "updated_quality_review_not_reviewable",
                "Ponowna ocena nadal wymaga pracy",
                "Poprawiona wersja nie może iść dalej, dopóki review ma blokady lub zmiany.",
                updated_quality_review.safe_next_step,
            )
        )
    return blockers


def _application(
    *,
    item: ContentWorkItem,
    revision_plan: ContentRevisionPlan | None,
    draft_output: StructuredDraftOutput | None,
    status: ContentRevisionApplicationStatus,
    safe_next_step: str,
    blockers: list[ContentRevisionApplicationBlocker] | None = None,
    diff: list[ContentRevisionDiffEntry] | None = None,
    updated_quality_review: ContentQualityReview | None = None,
) -> ContentRevisionApplication:
    return ContentRevisionApplication(
        id=f"revision_application_{item.id}",
        work_item_id=item.id,
        revision_plan_id=None if revision_plan is None else revision_plan.id,
        previous_version_id=None if draft_output is None else f"{draft_output.title}:before",
        revised_version_id=None if draft_output is None else f"{draft_output.title}:revised",
        status=status,
        diff=diff or [],
        updated_quality_review_id=(
            None if updated_quality_review is None else updated_quality_review.review_id
        ),
        quality_review_rerun_required=status != "applied",
        blockers=blockers or [],
        evidence_ids=[] if revision_plan is None else revision_plan.evidence_ids,
        source_connectors=item.source_connectors
        if revision_plan is None
        else revision_plan.source_connectors,
        safe_next_step=safe_next_step,
    )


def _diff_entries(
    revision_plan: ContentRevisionPlan,
    draft_output: StructuredDraftOutput,
) -> list[ContentRevisionDiffEntry]:
    existing_sections = {section.heading: section for section in draft_output.sections}
    entries: list[ContentRevisionDiffEntry] = []
    for instruction in revision_plan.instructions:
        section = (
            existing_sections.get(instruction.affected_section)
            if instruction.affected_section is not None
            else None
        )
        entries.append(
            ContentRevisionDiffEntry(
                instruction_id=instruction.id,
                affected_section=instruction.affected_section,
                change=instruction.change,
                reason=instruction.reason,
                before_summary=(
                    "Sekcja wymaga poprawki według quality review."
                    if section is None
                    else section.body_markdown[:160]
                ),
                after_summary=(
                    "Zastosowano wyłącznie instrukcję poprawki; "
                    "bez nowych twierdzeń poza wymaganymi dowodami."
                ),
                evidence_ids=instruction.required_evidence_ids,
            )
        )
    return entries


def _blocker(
    code: ContentRevisionApplicationBlockerCode,
    label: str,
    reason: str,
    next_step: str,
) -> ContentRevisionApplicationBlocker:
    return ContentRevisionApplicationBlocker(
        code=code,
        label=label,
        reason=reason,
        next_step=next_step,
    )
