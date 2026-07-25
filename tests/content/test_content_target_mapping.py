from datetime import UTC, datetime
from typing import cast

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers import content_target_mapping
from wilq.actions import action_validation, mutation_contract
from wilq.actions import audit_store as action_audit_store
from wilq.actions import payloads as action_payloads
from wilq.actions import service as action_service
from wilq.content.workflow import dev_draft_action, dev_draft_execution
from wilq.content.workflow.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionReview,
    ContentDraftRevisionSection,
)
from wilq.content.workflow.store import ContentWorkflowStore
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
from wilq.schemas import (
    ActionApplyRequest,
    ActionConfirmRequest,
    ActionImpactCheckRequest,
    ActionPreviewRequest,
    ActionReviewRequest,
    AuditEvent,
)
from wilq.storage.local_state import LocalStateStore


def _ready_preview():
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
                    ContentTargetAuthoringLayout(name="title_section", fields=["wordpress_title"]),
                    ContentTargetAuthoringLayout(
                        name="text_section", fields=["heading", "content_html"]
                    ),
                ],
            )
        ),
    )
    assert preview.target is not None
    assert preview.binding_digest is not None
    confirmation = new_content_target_mapping_confirmation(
        work_item_id=revision.work_item_id,
        preview=preview,
        command=ContentTargetMappingConfirmationCommand(
            expected_revision_digest=revision.content_digest,
            expected_target_contract_digest=preview.target.target_contract_digest,
            expected_binding_digest=preview.binding_digest,
            confirmed_by="Marta Kowalska",
            selections=[
                ContentTargetMappingSelection(
                    component_id="document-title",
                    layout_name="title_section",
                    field_bindings=[
                        ContentTargetMappingFieldBinding(
                            source_field="wordpress_title",
                            target_field="wordpress_title",
                        )
                    ],
                ),
                ContentTargetMappingSelection(
                    component_id="section:section_bdo",
                    layout_name="text_section",
                    field_bindings=[
                        ContentTargetMappingFieldBinding(
                            source_field="heading", target_field="heading"
                        ),
                        ContentTargetMappingFieldBinding(
                            source_field="content_html", target_field="content_html"
                        ),
                    ],
                ),
            ],
        ),
        confirmation_number=1,
        created_at="2026-07-25T10:00:00Z",
    )
    return revision, build_content_target_draft_preview(
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revisions=[revision],
        mapping_preview=preview,
        confirmation=confirmation,
    )


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


def test_target_mapping_binds_an_approved_revision_to_exact_observed_surface_without_guessing() -> (
    None
):
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
                    ContentTargetAuthoringLayout(name="text_section", fields=["title", "body"])
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
                    ContentTargetAuthoringLayout(name="text_section", fields=["title", "body"])
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
                    ContentTargetAuthoringLayout(name="text_section", fields=["title", "body"])
                ],
            )
        ),
    )

    assert preview.status == "blocked"
    assert preview.target is None
    assert preview.blockers[0].code == "revision_not_approved"


def test_target_mapping_confirmation_binds_every_observed_component_and_field() -> None:
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
                    ContentTargetAuthoringLayout(name="title_section", fields=["wordpress_title"]),
                    ContentTargetAuthoringLayout(
                        name="text_section", fields=["heading", "content_html"]
                    ),
                ],
            )
        ),
    )
    assert preview.target is not None
    assert preview.binding_digest is not None

    confirmation = new_content_target_mapping_confirmation(
        work_item_id=revision.work_item_id,
        preview=preview,
        command=ContentTargetMappingConfirmationCommand(
            expected_revision_digest=revision.content_digest,
            expected_target_contract_digest=preview.target.target_contract_digest,
            expected_binding_digest=preview.binding_digest,
            confirmed_by="Marta Kowalska",
            selections=[
                ContentTargetMappingSelection(
                    component_id="document-title",
                    layout_name="title_section",
                    field_bindings=[
                        ContentTargetMappingFieldBinding(
                            source_field="wordpress_title",
                            target_field="wordpress_title",
                        )
                    ],
                ),
                ContentTargetMappingSelection(
                    component_id="section:section_bdo",
                    layout_name="text_section",
                    field_bindings=[
                        ContentTargetMappingFieldBinding(
                            source_field="heading", target_field="heading"
                        ),
                        ContentTargetMappingFieldBinding(
                            source_field="content_html", target_field="content_html"
                        ),
                    ],
                ),
            ],
        ),
        confirmation_number=1,
        created_at="2026-07-25T10:00:00Z",
    )

    assert confirmation.revision == preview.revision
    assert confirmation.target_contract_digest == preview.target.target_contract_digest
    assert len(confirmation.selections) == 2


def test_target_draft_preview_uses_only_the_exact_confirmed_mapping() -> None:
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
                    ContentTargetAuthoringLayout(name="title_section", fields=["wordpress_title"]),
                    ContentTargetAuthoringLayout(
                        name="text_section", fields=["heading", "content_html"]
                    ),
                ],
            )
        ),
    )
    assert preview.target is not None
    assert preview.binding_digest is not None
    confirmation = new_content_target_mapping_confirmation(
        work_item_id=revision.work_item_id,
        preview=preview,
        command=ContentTargetMappingConfirmationCommand(
            expected_revision_digest=revision.content_digest,
            expected_target_contract_digest=preview.target.target_contract_digest,
            expected_binding_digest=preview.binding_digest,
            confirmed_by="Marta Kowalska",
            selections=[
                ContentTargetMappingSelection(
                    component_id="document-title",
                    layout_name="title_section",
                    field_bindings=[
                        ContentTargetMappingFieldBinding(
                            source_field="wordpress_title",
                            target_field="wordpress_title",
                        )
                    ],
                ),
                ContentTargetMappingSelection(
                    component_id="section:section_bdo",
                    layout_name="text_section",
                    field_bindings=[
                        ContentTargetMappingFieldBinding(
                            source_field="heading", target_field="heading"
                        ),
                        ContentTargetMappingFieldBinding(
                            source_field="content_html", target_field="content_html"
                        ),
                    ],
                ),
            ],
        ),
        confirmation_number=1,
        created_at="2026-07-25T10:00:00Z",
    )

    draft_preview = build_content_target_draft_preview(
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revisions=[revision],
        mapping_preview=preview,
        confirmation=confirmation,
    )

    assert draft_preview.status == "ready"
    assert draft_preview.root_field == "content_sections"
    assert draft_preview.payload_digest is not None
    assert draft_preview.components[0].fields[0].value == revision.title
    assert draft_preview.components[1].fields[1].value == "<p>Sprawdź działalność firmy.</p>"

    blocked = build_content_target_draft_preview(
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revisions=[revision],
        mapping_preview=preview,
        confirmation=None,
    )
    assert blocked.status == "blocked"
    assert blocked.blockers[0].code == "mapping_not_confirmed"


def test_content_dev_draft_action_binds_the_exact_confirmed_preview_and_fails_closed_when_stale(
    monkeypatch,
    tmp_path,
) -> None:
    revision, draft_preview = _ready_preview()
    assert draft_preview.status == "ready"
    assert draft_preview.target is not None
    assert draft_preview.confirmation is not None
    assert draft_preview.payload_digest is not None

    action = dev_draft_action.create_content_target_draft_action(
        draft_preview,
        dev_draft_action.ContentTargetDraftActionCommand(
            expected_revision_digest=revision.content_digest,
            expected_target_contract_digest=draft_preview.target.target_contract_digest,
            expected_confirmation_digest=draft_preview.confirmation.confirmation_digest,
            expected_payload_digest=draft_preview.payload_digest,
            requested_by="Marta Kowalska",
        ),
    )

    assert action.payload["action_type"] == dev_draft_action.CONTENT_DEV_DRAFT_ACTION_TYPE
    assert action.payload["apply_allowed"] is True
    assert action.payload["api_mutation_ready"] is True
    assert (
        action.payload["content_target_draft_binding"]["revision_digest"] == revision.content_digest
    )
    assert action_service._supported_mutation_adapter(action) == (
        "content_dev_draft_execution_boundary"
    )
    apply_contract = mutation_contract.mutation_apply_contract(
        action,
        action_service._supported_mutation_adapter(action),
    )
    assert apply_contract is not None
    assert apply_contract.allowed_operation == "create_wordpress_draft"
    assert apply_contract.publication_allowed is False
    assert apply_contract.destructive_allowed is False
    assert not any(
        blocker.startswith("blocked_claim:")
        for blocker in action_service._action_review_gate(action).apply_blockers
    )

    stale_preview = draft_preview.model_copy(update={"payload_digest": "f" * 64})
    monkeypatch.setattr(
        dev_draft_action,
        "current_content_target_draft_preview",
        lambda **_: stale_preview,
    )

    stale = dev_draft_action.refresh_content_target_draft_action(action)

    assert stale.status == "blocked"
    assert stale.payload["runtime_blockers"] == ["content_draft_action_stale"]

    state_store = LocalStateStore(tmp_path / "actions.sqlite3")
    monkeypatch.setattr(dev_draft_action, "local_state_store", lambda: state_store)
    monkeypatch.setattr(action_service, "local_state_store", lambda: state_store)
    monkeypatch.setattr(action_audit_store, "local_state_store", lambda: state_store)
    dev_draft_action.persist_content_target_draft_action(action)

    loaded = action_service.get_action(action.id)

    assert loaded is not None
    assert loaded.status == "blocked"
    assert loaded.payload["runtime_blockers"] == ["content_draft_action_stale"]


def test_content_dev_draft_write_payload_is_create_only_and_requires_one_exact_title(
    monkeypatch,
) -> None:
    revision, draft_preview = _ready_preview()
    assert draft_preview.target is not None
    assert draft_preview.confirmation is not None
    assert draft_preview.payload_digest is not None
    action = dev_draft_action.create_content_target_draft_action(
        draft_preview,
        dev_draft_action.ContentTargetDraftActionCommand(
            expected_revision_digest=revision.content_digest,
            expected_target_contract_digest=draft_preview.target.target_contract_digest,
            expected_confirmation_digest=draft_preview.confirmation.confirmation_digest,
            expected_payload_digest=draft_preview.payload_digest,
            requested_by="Marta Kowalska",
        ),
    )
    monkeypatch.setattr(
        dev_draft_action,
        "current_content_target_draft_preview",
        lambda **_: draft_preview,
    )

    payload = dev_draft_action.build_content_dev_draft_write_payload(action)

    assert payload.endpoint == "posts"
    assert payload.post_status == "draft"
    assert payload.create_only is True
    assert payload.publish_allowed is False
    assert payload.update_allowed is False
    assert payload.delete_allowed is False
    assert payload.title == revision.title
    assert payload.acf == {
        "content_sections": [
            {"acf_fc_layout": "title_section", "wordpress_title": revision.title},
            {
                "acf_fc_layout": "text_section",
                "heading": "Kiedy sprawdzić obowiązki BDO",
                "content_html": "<p>Sprawdź działalność firmy.</p>",
            },
        ]
    }

    no_title = draft_preview.model_copy(
        update={
            "components": [
                component
                for component in draft_preview.components
                if component.component_id != "document-title"
            ]
        }
    )
    monkeypatch.setattr(
        dev_draft_action,
        "current_content_target_draft_preview",
        lambda **_: no_title,
    )

    try:
        dev_draft_action.build_content_dev_draft_write_payload(action)
    except ValueError as error:
        assert "dokładnie jeden tytuł" in str(error)
    else:
        raise AssertionError("Payload bez jednoznacznego tytułu nie może powstać.")


def test_content_dev_draft_execution_uses_only_the_exact_acf_payload(monkeypatch) -> None:
    revision, draft_preview = _ready_preview()
    assert draft_preview.target is not None
    assert draft_preview.confirmation is not None
    assert draft_preview.payload_digest is not None
    action = dev_draft_action.create_content_target_draft_action(
        draft_preview,
        dev_draft_action.ContentTargetDraftActionCommand(
            expected_revision_digest=revision.content_digest,
            expected_target_contract_digest=draft_preview.target.target_contract_digest,
            expected_confirmation_digest=draft_preview.confirmation.confirmation_digest,
            expected_payload_digest=draft_preview.payload_digest,
            requested_by="Marta Kowalska",
        ),
    )
    monkeypatch.setattr(
        dev_draft_action,
        "current_content_target_draft_preview",
        lambda **_: draft_preview,
    )
    monkeypatch.setattr(dev_draft_execution, "_dev_draft_writes_enabled", lambda: True)
    received: dict[str, object] = {}

    def create(payload, **kwargs):
        received["payload"] = payload
        received["kwargs"] = kwargs
        return "draft_417"

    monkeypatch.setattr(dev_draft_execution, "create_wordpress_acf_draft", create)

    result, errors = dev_draft_execution.execute_content_target_draft_action(action)

    assert errors == []
    assert result is not None
    assert result["adapter"] == "content_dev_draft_execution_boundary"
    assert result["created_draft_id"] == "draft_417"
    assert result["endpoint"] == "posts"
    assert result["post_status"] == "draft"
    assert result["publish_allowed"] is False
    assert received["kwargs"] == {
        "connector_id": "wordpress_ekologus",
        "action_apply_authorized": True,
    }
    payload = received["payload"]
    assert payload.acf == {
        "content_sections": [
            {"acf_fc_layout": "title_section", "wordpress_title": revision.title},
            {
                "acf_fc_layout": "text_section",
                "heading": "Kiedy sprawdzić obowiązki BDO",
                "content_html": "<p>Sprawdź działalność firmy.</p>",
            },
        ]
    }


def test_content_dev_draft_prewrite_check_does_not_claim_public_measurement() -> None:
    revision, draft_preview = _ready_preview()
    assert draft_preview.target is not None
    assert draft_preview.confirmation is not None
    assert draft_preview.payload_digest is not None
    action = dev_draft_action.create_content_target_draft_action(
        draft_preview,
        dev_draft_action.ContentTargetDraftActionCommand(
            expected_revision_digest=revision.content_digest,
            expected_target_contract_digest=draft_preview.target.target_contract_digest,
            expected_confirmation_digest=draft_preview.confirmation.confirmation_digest,
            expected_payload_digest=draft_preview.payload_digest,
            requested_by="Marta Kowalska",
        ),
    )
    action.audit_events = [
        AuditEvent(
            id="audit_reviewed",
            action_id=action.id,
            event_type="human_review_approved_for_prepare",
            actor="operator_local_dashboard",
            summary="Zatwierdzono akcję.",
        ),
        AuditEvent(
            id="audit_confirmed",
            action_id=action.id,
            event_type="action_apply_confirmed",
            actor="operator_local_dashboard",
            summary="Potwierdzono podgląd.",
        )
    ]

    result = action_service.impact_check_action(
        action,
        ActionImpactCheckRequest(
            checked_by="Marta Kowalska",
            notes="Sprawdzono gotowość przed utworzeniem szkicu.",
        ),
    )

    assert result.status == "checked"
    assert result.metric_fact_count == 0
    assert result.audit_event.event_type == "action_impact_check_completed"
    assert "Kontrola gotowości szkicu" in result.audit_event.summary
    assert "rezultatu marketingowego" in result.audit_event.summary
    assert "Porównanie sprzed zmiany" not in result.audit_event.summary
    for forbidden in ("efekt", "pomiar", "okno przed", "okno po"):
        assert forbidden not in result.audit_event.event_type_label.lower()
        assert forbidden not in result.audit_event.summary.lower()


def test_content_dev_draft_apply_requires_the_full_action_chain_and_is_single_use(
    monkeypatch,
    tmp_path,
) -> None:
    revision, draft_preview = _ready_preview()
    assert draft_preview.target is not None
    assert draft_preview.confirmation is not None
    assert draft_preview.payload_digest is not None
    action = dev_draft_action.create_content_target_draft_action(
        draft_preview,
        dev_draft_action.ContentTargetDraftActionCommand(
            expected_revision_digest=revision.content_digest,
            expected_target_contract_digest=draft_preview.target.target_contract_digest,
            expected_confirmation_digest=draft_preview.confirmation.confirmation_digest,
            expected_payload_digest=draft_preview.payload_digest,
            requested_by="Marta Kowalska",
        ),
    )
    state_store = LocalStateStore(tmp_path / "actions.sqlite3")
    connector = type(
        "ConfiguredWordPressConnector",
        (),
        {
            "configured": True,
            "supported_actions": [dev_draft_action.CONTENT_DEV_DRAFT_ACTION_TYPE],
        },
    )()
    monkeypatch.setattr(action_validation, "local_state_store", lambda: state_store)
    monkeypatch.setattr(action_validation, "get_connector_status", lambda _: connector)
    monkeypatch.setattr(action_payloads, "get_connector_status", lambda _: connector)
    monkeypatch.setattr(action_service, "get_connector_status", lambda _: connector)
    current_preview = [draft_preview]
    monkeypatch.setattr(
        dev_draft_action,
        "current_content_target_draft_preview",
        lambda **_: current_preview[0],
    )
    draft_writes_enabled = [True]
    monkeypatch.setattr(
        dev_draft_execution,
        "_dev_draft_writes_enabled",
        lambda: draft_writes_enabled[0],
    )
    created_drafts: list[object] = []
    monkeypatch.setattr(
        dev_draft_execution,
        "create_wordpress_acf_draft",
        lambda payload, **_: created_drafts.append(payload) or "draft_417",
    )

    apply_request = ActionApplyRequest(confirm=True, confirmed_by="Marta Kowalska")
    assert not action_service.apply_action(action, apply_request).applied
    assert created_drafts == []

    assert action_service.validate_action(action).valid
    action_service.preview_action(action, ActionPreviewRequest(requested_by="Marta Kowalska"))
    assert not action_service.apply_action(action, apply_request).applied
    assert created_drafts == []

    action_service.record_action_review(
        action,
        ActionReviewRequest(
            outcome="approved_for_prepare",
            reviewed_by="Marta Kowalska",
            notes="Zatwierdzono dokładny szkic dev.",
        ),
    )
    assert action_service.confirm_action(
        action,
        ActionConfirmRequest(
            confirmed_by="Marta Kowalska",
            notes="Potwierdzam utworzenie jednego szkicu na dev.",
            preview_acknowledged=True,
        ),
    ).confirmed
    assert not action_service.apply_action(action, apply_request).applied
    assert created_drafts == []

    preflight = action_service.impact_check_action(
        action,
        ActionImpactCheckRequest(
            checked_by="Marta Kowalska",
            notes="Sprawdzono gotowość do utworzenia szkicu.",
        ),
    )
    assert preflight.status == "checked"

    changed_confirmation = draft_preview.confirmation.model_copy(
        update={"confirmation_digest": "f" * 64}
    )
    current_preview[0] = draft_preview.model_copy(update={"confirmation": changed_confirmation})
    assert not action_service.apply_action(action, apply_request).applied
    assert created_drafts == []

    current_preview[0] = draft_preview
    draft_writes_enabled[0] = False
    assert not action_service.apply_action(action, apply_request).applied
    assert created_drafts == []

    draft_writes_enabled[0] = True
    applied = action_service.apply_action(action, apply_request)
    assert applied.applied
    assert len(created_drafts) == 1

    repeated = action_service.apply_action(action, apply_request)
    assert not repeated.applied
    assert len(created_drafts) == 1


def test_content_dev_draft_payload_rechecks_the_confirmation_used_for_payload() -> None:
    revision, first_preview = _ready_preview()
    assert first_preview.target is not None
    assert first_preview.confirmation is not None
    assert first_preview.payload_digest is not None
    action = dev_draft_action.create_content_target_draft_action(
        first_preview,
        dev_draft_action.ContentTargetDraftActionCommand(
            expected_revision_digest=revision.content_digest,
            expected_target_contract_digest=first_preview.target.target_contract_digest,
            expected_confirmation_digest=first_preview.confirmation.confirmation_digest,
            expected_payload_digest=first_preview.payload_digest,
            requested_by="Marta Kowalska",
        ),
    )
    changed_confirmation = first_preview.confirmation.model_copy(
        update={"confirmation_digest": "f" * 64}
    )
    second_preview = first_preview.model_copy(update={"confirmation": changed_confirmation})
    try:
        dev_draft_action.build_content_dev_draft_write_payload(action, preview=second_preview)
    except ValueError as error:
        assert "Dokładna rewizja, mapowanie albo odczyt dev zmieniły się" in str(error)
    else:
        raise AssertionError("Payload nie może użyć nowszego potwierdzenia mapowania.")


def test_content_dev_draft_action_endpoint_persists_only_the_exact_preview(
    monkeypatch,
    tmp_path,
) -> None:
    revision, draft_preview = _ready_preview()
    assert draft_preview.target is not None
    assert draft_preview.confirmation is not None
    assert draft_preview.payload_digest is not None
    state_store = LocalStateStore(tmp_path / "actions.sqlite3")

    monkeypatch.setattr(
        content_target_mapping,
        "content_target_draft_preview_endpoint",
        lambda *_: draft_preview,
    )
    monkeypatch.setattr(dev_draft_action, "local_state_store", lambda: state_store)
    app = FastAPI()
    router = APIRouter()
    content_target_mapping.register_content_target_mapping_route(router)
    app.include_router(router)

    response = TestClient(app).post(
        (
            f"/api/content/work-items/{revision.work_item_id}/draft-revisions/"
            f"{revision.revision_id}/target-mapping/draft-action"
        ),
        json={
            "expected_revision_digest": revision.content_digest,
            "expected_target_contract_digest": draft_preview.target.target_contract_digest,
            "expected_confirmation_digest": draft_preview.confirmation.confirmation_digest,
            "expected_payload_digest": draft_preview.payload_digest,
            "requested_by": "Marta Kowalska",
        },
    )

    assert response.status_code == 200
    action = dev_draft_action.load_content_target_draft_action(response.json()["id"])
    assert action is not None
    assert response.json()["payload"]["content_target_draft_binding"]["payload_digest"] == (
        draft_preview.payload_digest
    )


def _confirmation_request(
    revision: ContentDraftRevision,
    review: ContentDraftRevisionReview,
    discovery: ContentTargetDiscovery,
) -> dict[str, object]:
    preview = build_content_target_mapping_preview(
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revisions=[revision],
        human_review=review,
        discovery=discovery,
    )
    return {
        "expected_revision_digest": revision.content_digest,
        "expected_target_contract_digest": "d" * 64,
        "expected_binding_digest": preview.binding_digest,
        "confirmed_by": "Marta Kowalska",
        "selections": [
            {
                "component_id": "document-title",
                "layout_name": "title_section",
                "field_bindings": [
                    {
                        "source_field": "wordpress_title",
                        "target_field": "wordpress_title",
                    }
                ],
            },
            {
                "component_id": "section:section_bdo",
                "layout_name": "text_section",
                "field_bindings": [
                    {"source_field": "heading", "target_field": "heading"},
                    {
                        "source_field": "content_html",
                        "target_field": "content_html",
                    },
                ],
            },
        ],
    }


def test_target_mapping_confirmation_endpoint_persists_only_the_exact_preview(
    monkeypatch,
    tmp_path,
) -> None:
    revision = _revision()
    review = _review(revision)
    discovery = _discovery(
        authoring_surface=ContentTargetAuthoringSurface(
            kind="acf_flexible_content",
            root_field="content_sections",
            layouts=[
                ContentTargetAuthoringLayout(name="title_section", fields=["wordpress_title"]),
                ContentTargetAuthoringLayout(
                    name="text_section", fields=["heading", "content_html"]
                ),
            ],
        )
    )
    backing_store = ContentWorkflowStore(tmp_path / "mapping.sqlite3")

    class RouteStore:
        def list_draft_revisions(self, work_item_id: str) -> list[ContentDraftRevision]:
            assert work_item_id == revision.work_item_id
            return [revision]

        def load_draft_revision_review(
            self, *, work_item_id: str, revision_id: str
        ) -> ContentDraftRevisionReview | None:
            assert work_item_id == revision.work_item_id
            return review if revision_id == revision.revision_id else None

        def record_target_mapping_confirmation(self, **kwargs):
            return backing_store.record_target_mapping_confirmation(**kwargs)

        def load_target_mapping_confirmation(self, **kwargs):
            return backing_store.load_target_mapping_confirmation(**kwargs)

    monkeypatch.setattr(
        content_target_mapping,
        "content_workflow_store",
        lambda: cast(object, RouteStore()),
    )
    monkeypatch.setattr(
        content_target_mapping,
        "build_content_target_discovery",
        lambda work_item_id: discovery,
    )
    app = FastAPI()
    router = APIRouter()
    content_target_mapping.register_content_target_mapping_route(router)
    app.include_router(router)
    path = (
        f"/api/content/work-items/{revision.work_item_id}/draft-revisions/"
        f"{revision.revision_id}/target-mapping/confirmation"
    )

    response = TestClient(app).post(
        path,
        json=_confirmation_request(revision, review, discovery),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "created"
    assert payload["confirmation"]["revision"]["revision_id"] == revision.revision_id
    assert payload["confirmation"]["target_contract_digest"] == "d" * 64

    draft_preview = TestClient(app).get(path.removesuffix("/confirmation") + "/draft-preview")

    assert draft_preview.status_code == 200
    draft_payload = draft_preview.json()
    assert draft_payload["status"] == "ready"
    assert draft_payload["root_field"] == "content_sections"
    assert (
        draft_payload["confirmation"]["confirmation_id"]
        == payload["confirmation"]["confirmation_id"]
    )
    assert draft_payload["components"][1]["fields"][1]["value"] == (
        "<p>Sprawdź działalność firmy.</p>"
    )
