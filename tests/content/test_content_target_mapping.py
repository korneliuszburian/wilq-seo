from datetime import UTC, datetime

from wilq.content.workflow.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionReview,
    ContentDraftRevisionSection,
)
from wilq.content.workflow.target_discovery import (
    ContentTargetAuthoringLayout,
    ContentTargetAuthoringSurface,
    ContentTargetContract,
    ContentTargetDiscovery,
    ContentTargetDiscoveryTarget,
    ContentTargetObservationEvidence,
)
from wilq.content.workflow.target_mapping import build_content_target_mapping_preview


def _revision() -> ContentDraftRevision:
    return ContentDraftRevision.model_construct(
        revision_id="revision_bdo_11",
        work_item_id="content_work_item_bdo",
        revision_number=11,
        base_revision_id="revision_bdo_10",
        content_digest="a" * 64,
        draft_package_id="draft_package_bdo",
        draft_package_digest="b" * 64,
        planning_digest="c" * 64,
        final_canonical_url="https://www.ekologus.pl/bdo/",
        title="BDO — obowiązki przedsiębiorcy",
        sections=[
            ContentDraftRevisionSection(
                section_id="section_bdo",
                heading="Kiedy sprawdzić obowiązki BDO",
                body_markdown="Sprawdź działalność firmy.",
                content_html="<p>Sprawdź działalność firmy.</p>",
                evidence_ids=["ev_bdo"],
            )
        ],
        faq=[],
        cta_blocks=[],
        internal_links=[],
        created_by="operator_local_dashboard",
        created_at=datetime.now(UTC),
    )


def _review(revision: ContentDraftRevision) -> ContentDraftRevisionReview:
    return ContentDraftRevisionReview.model_construct(
        decision_id="review_bdo_11",
        decision_number=1,
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revision_digest=revision.content_digest,
        decision="approved",
        reviewed_by="operator_local_dashboard",
        created_at=datetime.now(UTC),
    )


def _discovery(
    *,
    authoring_surface: ContentTargetAuthoringSurface | None,
    target_contract_digest: str = "d" * 64,
) -> ContentTargetDiscovery:
    contract = ContentTargetContract(
        environment="dev",
        object_id="1353",
        url="https://ekologus.dev.proudsite.pl/bdo/",
        post_type="post",
        post_status="publish",
        modified="2026-07-24T10:00:00",
        authoring_surface=authoring_surface,
    )
    observation = ContentTargetObservationEvidence(
        evidence_id="ev_wordpress_target_observation_bdo",
        connector_id="wordpress_ekologus",
        object_id="1353",
        post_type="post",
        url=contract.url,
        post_status="publish",
        modified=contract.modified,
        observed_at="2026-07-24T10:00:01Z",
    )
    target = ContentTargetDiscoveryTarget(
        object_id=contract.object_id,
        url=contract.url,
        post_type=contract.post_type,
        post_status=contract.post_status,
        target_contract=contract,
        target_contract_digest=target_contract_digest,
        observation_evidence=observation,
    )
    return ContentTargetDiscovery(
        work_item_id="content_work_item_bdo",
        public_url="https://www.ekologus.pl/bdo/",
        relation_status="partial",
        label="Znaleziono obiekt dev do sprawdzenia",
        reason="Zgodność adresu pozostaje kandydatem relacji.",
        target=target,
        evidence_ids=[observation.evidence_id],
    )


def test_target_mapping_binds_an_approved_revision_to_exact_observed_surface_without_guessing(
) -> None:
    revision = _revision()
    preview = build_content_target_mapping_preview(
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revisions=[revision],
        human_review=_review(revision),
        discovery=_discovery(
            authoring_surface=ContentTargetAuthoringSurface(
                kind="acf_flexible_content",
                root_field="content_sections",
                layouts=[
                    ContentTargetAuthoringLayout(
                        name="text_section", fields=["title", "body"]
                    )
                ],
            )
        ),
    )

    assert preview.status == "ready_for_human_mapping"
    assert preview.revision.revision_id == revision.revision_id
    assert preview.revision.content_digest == revision.content_digest
    assert preview.target is not None
    assert preview.target.target_contract_digest == "d" * 64
    assert preview.binding_digest is not None
    assert {component.status for component in preview.components} == {"human_only"}
    assert all(
        component.target_root_field == "content_sections" for component in preview.components
    )
    assert all(component.available_layouts == ["text_section"] for component in preview.components)

    changed_target = build_content_target_mapping_preview(
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revisions=[revision],
        human_review=_review(revision),
        discovery=_discovery(
            authoring_surface=ContentTargetAuthoringSurface(
                kind="acf_flexible_content",
                root_field="content_sections",
                layouts=[
                    ContentTargetAuthoringLayout(
                        name="text_section", fields=["title", "body"]
                    )
                ],
            ),
            target_contract_digest="e" * 64,
        ),
    )

    assert changed_target.binding_digest != preview.binding_digest


def test_target_mapping_blocks_every_component_when_exact_object_has_unknown_surface() -> None:
    revision = _revision()
    preview = build_content_target_mapping_preview(
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revisions=[revision],
        human_review=_review(revision),
        discovery=_discovery(authoring_surface=None),
    )

    assert preview.status == "blocked"
    assert preview.binding_digest is None
    assert preview.target is not None
    assert preview.blockers[0].code == "authoring_surface_unknown"
    assert {component.status for component in preview.components} == {"blocked"}


def test_target_mapping_requires_an_exact_approved_human_review() -> None:
    revision = _revision()
    preview = build_content_target_mapping_preview(
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revisions=[revision],
        human_review=None,
        discovery=_discovery(
            authoring_surface=ContentTargetAuthoringSurface(
                kind="acf_flexible_content",
                root_field="content_sections",
                layouts=[
                    ContentTargetAuthoringLayout(
                        name="text_section", fields=["title", "body"]
                    )
                ],
            )
        ),
    )

    assert preview.status == "blocked"
    assert preview.target is None
    assert preview.blockers[0].code == "revision_not_approved"
