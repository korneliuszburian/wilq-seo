from datetime import UTC, datetime

from wilq.content.workflow import dev_draft_action, dev_draft_execution
from wilq.content.workflow.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionPageAssets,
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
from wilq.content.workflow.target_mapping import (
    ContentTargetMappingConfirmationCommand,
    ContentTargetMappingFieldBinding,
    ContentTargetMappingSelection,
    build_content_target_draft_preview,
    build_content_target_mapping_preview,
    new_content_target_mapping_confirmation,
)


def _native_revision() -> ContentDraftRevision:
    return ContentDraftRevision.model_construct(
        revision_id="revision_bdo_1",
        work_item_id="content_work_item_bdo",
        revision_number=1,
        content_digest="a" * 64,
        title="BDO — obowiązki przedsiębiorcy",
        page_assets=ContentDraftRevisionPageAssets(
            wordpress_title="BDO — obowiązki przedsiębiorcy",
            meta_title="BDO dla przedsiębiorcy",
            meta_description="Sprawdź obowiązki BDO.",
            h1="BDO — obowiązki przedsiębiorcy",
            lead="Praktyczny przewodnik po obowiązkach BDO.",
        ),
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
        official_source_references=[],
    )


def _native_discovery(revision: ContentDraftRevision) -> ContentTargetDiscovery:
    surface = ContentTargetAuthoringSurface(
        kind="wordpress_post_content",
        root_field="content",
        layouts=[
            ContentTargetAuthoringLayout(
                name="wordpress_post_content", fields=["title", "content_html"]
            )
        ],
    )
    target = ContentTargetContract(
        environment="staging",
        object_id="1353",
        url="https://ekologus.dev.proudsite.pl/bdo/",
        post_type="post",
        post_status="publish",
        modified="2026-08-05T12:00:00",
        authoring_surface=surface,
    )
    observation = ContentTargetObservationEvidence(
        evidence_id="ev_target_bdo",
        connector_id="wordpress_ekologus",
        object_id="1353",
        post_type="post",
        url=target.url,
        post_status="publish",
        modified=target.modified,
        observed_at="2026-08-05T12:00:01Z",
    )
    return ContentTargetDiscovery(
        work_item_id=revision.work_item_id,
        public_url="https://www.ekologus.pl/bdo/",
        relation_status="partial",
        label="Target dev",
        reason="Odczytano wpis dev.",
        target=ContentTargetDiscoveryTarget(
            object_id=target.object_id,
            url=target.url,
            post_type=target.post_type,
            post_status=target.post_status,
            target_contract=target,
            target_contract_digest="b" * 64,
            observation_evidence=observation,
        ),
    )


def _approved_review(revision: ContentDraftRevision) -> ContentDraftRevisionReview:
    return ContentDraftRevisionReview.model_construct(
        decision_id="review_bdo_1",
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revision_digest=revision.content_digest,
        decision="approved",
        reviewed_by="Wilku",
        created_at=datetime.now(UTC),
    )


def _confirmed_mapping(
    revision: ContentDraftRevision,
    review: ContentDraftRevisionReview,
    discovery: ContentTargetDiscovery,
):
    mapping = build_content_target_mapping_preview(
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revisions=[revision],
        human_review=review,
        discovery=discovery,
    )
    assert mapping.target is not None
    assert mapping.binding_digest is not None
    return mapping, new_content_target_mapping_confirmation(
        work_item_id=revision.work_item_id,
        preview=mapping,
        command=ContentTargetMappingConfirmationCommand(
            expected_revision_digest=revision.content_digest,
            expected_target_contract_digest=mapping.target.target_contract_digest,
            expected_binding_digest=mapping.binding_digest,
            confirmed_by="Wilku",
            selections=[
                ContentTargetMappingSelection(
                    component_id="document-title",
                    layout_name="wordpress_post_content",
                    field_bindings=[
                        ContentTargetMappingFieldBinding(
                            source_field="wordpress_title", target_field="title"
                        )
                    ],
                ),
                ContentTargetMappingSelection(
                    component_id="document-content",
                    layout_name="wordpress_post_content",
                    field_bindings=[
                        ContentTargetMappingFieldBinding(
                            source_field="document_html", target_field="content_html"
                        )
                    ],
                ),
            ],
        ),
        confirmation_number=1,
        created_at="2026-08-05T12:00:02Z",
    )


def test_native_post_content_mapping_builds_an_exact_draft_only_payload(monkeypatch) -> None:
    revision = _native_revision()
    mapping, confirmation = _confirmed_mapping(
        revision,
        _approved_review(revision),
        _native_discovery(revision),
    )
    assert [component.component_id for component in mapping.components] == [
        "document-title",
        "document-content",
    ]
    preview = build_content_target_draft_preview(
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revisions=[revision],
        mapping_preview=mapping,
        confirmation=confirmation,
    )
    action = dev_draft_action.create_content_target_draft_action(
        preview,
        dev_draft_action.ContentTargetDraftActionCommand(
            expected_revision_digest=revision.content_digest,
            expected_target_contract_digest=mapping.target.target_contract_digest,
            expected_confirmation_digest=confirmation.confirmation_digest,
            expected_payload_digest=preview.payload_digest or "",
            requested_by="Wilku",
        ),
    )
    payload = dev_draft_action.build_content_dev_draft_write_payload(action, preview=preview)

    assert payload.authoring_mode == "wordpress_post_content"
    assert payload.endpoint == "posts"
    assert payload.acf is None
    assert payload.content_html is not None
    assert "<h1>BDO — obowiązki przedsiębiorcy</h1>" not in payload.content_html
    assert payload.content_html.startswith("<p>Praktyczny przewodnik po obowiązkach BDO.</p>")
    document_component = next(
        component
        for component in preview.components
        if component.component_id == "document-content"
    )
    assert payload.content_html == document_component.fields[0].value
    assert "Kiedy sprawdzić obowiązki BDO" in payload.content_html
    assert payload.post_status == "draft"
    assert payload.create_only is True
    assert payload.publish_allowed is False
    assert payload.destructive_update_allowed is False

    created: list[tuple[str, str]] = []
    monkeypatch.setattr(dev_draft_execution, "_dev_draft_writes_enabled", lambda: True)
    monkeypatch.setattr(
        dev_draft_execution,
        "build_content_dev_draft_write_payload",
        lambda _action: payload,
    )
    monkeypatch.setattr(
        dev_draft_execution,
        "create_wordpress_draft_post",
        lambda value, *, connector_id: (
            created.append((value.content_html or "", connector_id)) or "draft_1354"
        ),
    )
    result, errors = dev_draft_execution.execute_content_target_draft_action(action)

    assert errors == []
    assert result is not None
    assert result["created_draft_id"] == "draft_1354"
    assert created == [(payload.content_html, "wordpress_ekologus")]
