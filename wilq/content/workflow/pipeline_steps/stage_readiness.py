from __future__ import annotations

from wilq.connectors.wordpress.authoring import build_wordpress_authoring_profile
from wilq.content.workflow.contracts.contracts import (
    ContentWordPressDraftWriteReadinessBlocker,
    ContentWordPressExistingDraftSectionDiff,
    ContentWordPressExistingDraftUpdateReadinessResponse,
    ContentWorkItemWorkflowSnapshotResponse,
)
from wilq.content.workflow.target.public_to_dev_mapping import (
    ContentPublicToDevMappingEvidence,
    build_content_public_to_dev_mapping,
)


def build_content_wordpress_existing_draft_update_readiness_response(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    *,
    relation_evidence: ContentPublicToDevMappingEvidence | None = None,
) -> ContentWordPressExistingDraftUpdateReadinessResponse:
    profile = build_wordpress_authoring_profile("wordpress_ekologus", include_dev_content=True)
    draft = snapshot.draft_package.draft_package_result.draft_package
    source_url = snapshot.preflight.item.source_public_url or ""
    mapping = build_content_public_to_dev_mapping(
        source_url,
        dev_content=profile.dev_content,
        relation_evidence=relation_evidence,
    )
    target = next(
        (
            item
            for item in profile.dev_content.items
            if mapping.mapping_status == "exact"
            and item.post_id == mapping.dev_post_id
            and item.link == mapping.dev_url
        ),
        None,
    )
    current_sections = target.sections if target is not None else []
    proposed_sections = draft.sections if draft is not None else []
    current_by_heading = {
        section.title or section.layout_label: section for section in current_sections
    }
    diff_preview: list[ContentWordPressExistingDraftSectionDiff] = []
    for section in proposed_sections[:8]:
        heading = section.heading or "Sekcja bez tytułu"
        current = current_by_heading.get(heading)
        proposed_summary = " ".join([section.purpose, *section.draft_notes]).strip()[:240]
        current_summary = current.text_summary[:240] if current is not None else ""
        diff_preview.append(
            ContentWordPressExistingDraftSectionDiff(
                heading=heading,
                current_summary=current_summary,
                proposed_summary=proposed_summary,
                status=(
                    "missing_current"
                    if current is None
                    else "unchanged"
                    if current_summary == proposed_summary
                    else "changed"
                ),
            )
        )
    blocker = ContentWordPressDraftWriteReadinessBlocker(
        code="existing_draft_update_contract_not_implemented",
        label="Aktualizacja istniejącego draftu wymaga osobnego kontraktu",
        reason=(
            "WILQ ma odczyt dev i podgląd proponowanych sekcji, ale nie wykonuje jeszcze "
            "aktualizacji istniejącego posta ani pól ACF."
        ),
        next_step=(
            "Pozostaw podgląd bez zapisu i przejdź przez review; dopiero po wdrożeniu "
            "ActionObject update preview/review/confirm można odblokować zapis dev."
        ),
    )
    return ContentWordPressExistingDraftUpdateReadinessResponse(
        work_item_id=snapshot.preflight.item.id,
        target_post_id=mapping.dev_post_id if target is not None else None,
        target_url=mapping.dev_url if target is not None else None,
        current_state_available=target is not None,
        current_section_count=len(current_sections),
        proposed_section_count=len(draft.sections) if draft is not None else 0,
        section_diff_preview=diff_preview,
        blockers=[blocker],
        operator_next_step=blocker.next_step,
        evidence_ids=mapping.evidence_ids,
        source_connectors=list(
            dict.fromkeys([*snapshot.preflight.item.source_connectors, *profile.source_connectors])
        ),
    )
