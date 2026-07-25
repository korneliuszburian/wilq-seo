from datetime import UTC, datetime
from typing import cast

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers import content_target_mapping
from wilq.actions import audit_store as action_audit_store
from wilq.actions import service as action_service
from wilq.content.workflow import dev_draft_action
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
    assert action.payload["apply_allowed"] is False
    assert action.payload["api_mutation_ready"] is False
    assert (
        action.payload["content_target_draft_binding"]["revision_digest"] == revision.content_digest
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
