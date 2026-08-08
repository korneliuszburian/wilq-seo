from datetime import UTC, datetime

from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionReview,
)
from wilq.content.workflow.target.target_discovery import (
    ContentTargetAuthoringLayout,
    ContentTargetAuthoringSurface,
    ContentTargetContract,
    ContentTargetDiscovery,
    ContentTargetDiscoveryTarget,
    ContentTargetObservationEvidence,
)
from wilq.content.workflow.target.target_mapping import build_content_target_mapping_preview


def test_observed_acf_without_an_exact_write_profile_cannot_reach_mapping() -> None:
    revision = ContentDraftRevision.model_construct(
        revision_id="revision_home_1",
        work_item_id="content_work_item_home",
        revision_number=1,
        content_digest="a" * 64,
        title="Strona główna Ekologus",
        sections=[],
        faq=[],
        cta_blocks=[],
        internal_links=[],
    )
    review = ContentDraftRevisionReview.model_construct(
        decision_id="review_home_1",
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revision_digest=revision.content_digest,
        decision="approved",
        reviewed_by="Wilku",
        created_at=datetime.now(UTC),
    )
    surface = ContentTargetAuthoringSurface(
        kind="acf_flexible_content",
        root_field="flexible-home",
        layouts=[
            ContentTargetAuthoringLayout(
                name="hero",
                fields=["heading_component"],
            )
        ],
        write_profile_status="unavailable",
        write_profile_reason="REST nie potwierdza typów ani wymaganych wartości layoutu.",
    )
    contract = ContentTargetContract(
        environment="staging",
        object_id="2",
        url="https://ekologus.dev.proudsite.pl/",
        post_type="page",
        post_status="publish",
        modified="2026-08-05T12:00:00Z",
        authoring_surface=surface,
    )
    observation = ContentTargetObservationEvidence(
        evidence_id="ev_target_home",
        connector_id="wordpress_ekologus",
        object_id="2",
        post_type="page",
        url=contract.url,
        post_status="publish",
        modified=contract.modified,
        observed_at="2026-08-05T12:00:01Z",
    )
    discovery = ContentTargetDiscovery(
        work_item_id=revision.work_item_id,
        public_url="https://www.ekologus.pl/",
        relation_status="partial",
        label="Target dev",
        reason="Odczytano stronę dev.",
        target=ContentTargetDiscoveryTarget(
            object_id=contract.object_id,
            url=contract.url,
            post_type=contract.post_type,
            post_status=contract.post_status,
            target_contract=contract,
            target_contract_digest="b" * 64,
            observation_evidence=observation,
        ),
    )

    preview = build_content_target_mapping_preview(
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revisions=[revision],
        human_review=review,
        discovery=discovery,
    )

    assert preview.status == "blocked"
    assert preview.binding_digest is None
    assert preview.blockers[0].code == "acf_write_profile_unavailable"
    assert {component.status for component in preview.components} == {"blocked"}
