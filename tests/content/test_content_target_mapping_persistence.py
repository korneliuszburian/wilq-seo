from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import httpx
import pytest
from fastapi import APIRouter, FastAPI

from apps.api.wilq_api.routers import content_target_mapping
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionReview,
    ContentDraftRevisionSection,
)
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.content.workflow.target.target_discovery import (
    ContentTargetAuthoringLayout,
    ContentTargetAuthoringSurface,
    ContentTargetContract,
    ContentTargetDiscovery,
    ContentTargetDiscoveryTarget,
    ContentTargetObservationEvidence,
)
from wilq.content.workflow.target.target_mapping import (
    ContentTargetMappingConfirmationCommand,
    ContentTargetMappingFieldBinding,
    ContentTargetMappingPreview,
    ContentTargetMappingSelection,
    build_content_target_mapping_preview,
    new_content_target_mapping_confirmation,
)
from wilq.content.workflow.target.target_mapping_persistence import (
    ContentTargetMappingPersistenceError,
    content_target_mapping_confirmation_scalars,
)


def _revision() -> ContentDraftRevision:
    return ContentDraftRevision.model_construct(
        revision_id="revision_bdo_persisted_1",
        work_item_id="content_work_item_bdo_persisted",
        revision_number=1,
        base_revision_id=None,
        content_digest="a" * 64,
        draft_package_id="draft_package_bdo_persisted",
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
        created_at=datetime(2026, 8, 29, 8, 0, tzinfo=UTC),
    )


def _review(revision: ContentDraftRevision) -> ContentDraftRevisionReview:
    return ContentDraftRevisionReview(
        decision_id="review_bdo_persisted_1",
        decision_number=1,
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revision_digest=revision.content_digest,
        decision="approved",
        reviewed_by="operator_local_dashboard",
        checked_items=["Sprawdzono dokładną rewizję dokumentu."],
        evidence_ids=["ev_bdo"],
        created_at=datetime(2026, 8, 29, 8, 5, tzinfo=UTC),
    )


def _discovery() -> ContentTargetDiscovery:
    surface = ContentTargetAuthoringSurface(
        kind="acf_flexible_content",
        root_field="content_sections",
        source_acf_digest="1" * 64,
        source_acf_fields_digest="2" * 64,
        source_acf_root_field_count=2,
        source_acf_row_count=2,
        layouts=[
            ContentTargetAuthoringLayout(
                name="title_section",
                section_index=1,
                fields=["wordpress_title"],
                writable_fields=["wordpress_title"],
            ),
            ContentTargetAuthoringLayout(
                name="text_section",
                section_index=2,
                fields=["heading", "content_html"],
                writable_fields=["heading", "content_html"],
            ),
        ],
    )
    contract = ContentTargetContract(
        environment="dev",
        object_id="1353",
        url="https://ekologus.dev.proudsite.pl/bdo/",
        post_type="post",
        rest_endpoint="posts",
        post_status="publish",
        modified="2026-08-29T07:55:00Z",
        authoring_surface=surface,
    )
    observation = ContentTargetObservationEvidence(
        evidence_id="ev_wordpress_target_observation_bdo_persisted",
        connector_id="wordpress_ekologus",
        object_id=contract.object_id,
        post_type=contract.post_type,
        url=contract.url,
        post_status=contract.post_status,
        modified=contract.modified,
        observed_at="2026-08-29T07:56:00Z",
    )
    target = ContentTargetDiscoveryTarget(
        object_id=contract.object_id,
        url=contract.url,
        post_type=contract.post_type,
        post_status=contract.post_status,
        target_contract=contract,
        target_contract_digest="d" * 64,
        observation_evidence=observation,
    )
    return ContentTargetDiscovery(
        work_item_id=_revision().work_item_id,
        public_url="https://www.ekologus.pl/bdo/",
        relation_status="partial",
        label="Znaleziono dokładny obiekt dev",
        reason="Odczyt wskazuje jeden obiekt dev.",
        target=target,
        evidence_ids=[observation.evidence_id],
    )


def _preview_and_command() -> tuple[
    ContentDraftRevision,
    ContentDraftRevisionReview,
    ContentTargetDiscovery,
    ContentTargetMappingPreview,
    ContentTargetMappingConfirmationCommand,
]:
    revision = _revision()
    review = _review(revision)
    discovery = _discovery()
    preview = build_content_target_mapping_preview(
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revisions=[revision],
        human_review=review,
        discovery=discovery,
    )
    assert preview.target is not None
    assert preview.binding_digest is not None
    command = ContentTargetMappingConfirmationCommand(
        expected_revision_digest=revision.content_digest,
        expected_target_contract_digest=preview.target.target_contract_digest,
        expected_binding_digest=preview.binding_digest,
        confirmed_by="Marta Kowalska",
        selections=[
            _selection("document-title", "title_section", 1, "wordpress_title"),
            _selection(
                "section:section_bdo",
                "text_section",
                2,
                "heading",
                "content_html",
            ),
        ],
    )
    return revision, review, discovery, preview, command


def _selection(
    component_id: str,
    layout_name: str,
    section_index: int,
    *field_names: str,
) -> ContentTargetMappingSelection:
    return ContentTargetMappingSelection(
        component_id=component_id,
        layout_name=layout_name,
        target_section_index=section_index,
        field_bindings=[
            ContentTargetMappingFieldBinding(source_field=name, target_field=name)
            for name in field_names
        ],
    )


def _canonical_digest(value: object) -> str:
    return sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _confirmation_row_count(path: Path) -> int:
    with sqlite3.connect(path) as connection:
        row = connection.execute(
            "SELECT COUNT(*) FROM content_target_mapping_confirmations"
        ).fetchone()
    assert row is not None
    return int(row[0])


class _RouteStore(ContentWorkflowStore):
    def __init__(
        self,
        path: Path,
        *,
        revision: ContentDraftRevision,
        review: ContentDraftRevisionReview,
    ) -> None:
        super().__init__(path)
        self.revision = revision
        self.review = review

    def list_draft_revisions(self, work_item_id: str) -> list[ContentDraftRevision]:
        return [self.revision] if work_item_id == self.revision.work_item_id else []

    def load_draft_revision_review(
        self,
        *,
        work_item_id: str,
        revision_id: str,
    ) -> ContentDraftRevisionReview | None:
        if work_item_id == self.revision.work_item_id and revision_id == self.revision.revision_id:
            return self.review
        return None


def _route_app() -> FastAPI:
    app = FastAPI()
    router = APIRouter()
    content_target_mapping.register_content_target_mapping_route(router)
    app.include_router(router)
    return app


def _target_mapping_path(revision: ContentDraftRevision) -> str:
    return (
        f"/api/content/work-items/{revision.work_item_id}/draft-revisions/"
        f"{revision.revision_id}/target-mapping"
    )


def _route_request(
    app: FastAPI,
    method: str,
    path: str,
    *,
    payload: dict[str, object] | None = None,
) -> httpx.Response:
    async def exercise() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, json=payload)

    return asyncio.run(exercise())


def _assert_legacy_action_blocked(
    app: FastAPI,
    path: str,
    revision: ContentDraftRevision,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_action_persistence(_: object) -> object:
        raise AssertionError("A legacy confirmation must not authorize an action.")

    monkeypatch.setattr(
        content_target_mapping,
        "persist_content_target_draft_action",
        fail_action_persistence,
    )
    response = _route_request(
        app,
        "POST",
        path + "/draft-action",
        payload={
            "expected_revision_digest": revision.content_digest,
            "expected_target_contract_digest": "0" * 64,
            "expected_confirmation_digest": "0" * 64,
            "expected_payload_digest": "0" * 64,
            "requested_by": "Marta Kowalska",
        },
    )
    assert response.status_code == 409


def _insert_legacy_confirmation(
    store: ContentWorkflowStore,
    *,
    preview: ContentTargetMappingPreview,
    command: ContentTargetMappingConfirmationCommand,
    confirmation_number: int = 1,
    created_at: str = "2026-08-01T10:00:00+00:00",
    require_empty: bool = True,
) -> str:
    confirmation = new_content_target_mapping_confirmation(
        work_item_id=preview.work_item_id,
        preview=preview,
        command=command,
        confirmation_number=confirmation_number,
        created_at=created_at,
    )
    if require_empty:
        assert (
            store.load_target_mapping_draft_state(
                work_item_id=preview.work_item_id,
                revision_id=preview.revision.revision_id,
            )
            is None
        )
    with sqlite3.connect(store.path) as connection:
        connection.execute(
            """
            INSERT INTO content_target_mapping_confirmations (
              confirmation_id, work_item_id, revision_id, revision_digest,
              target_contract_digest, binding_digest, confirmation_number,
              confirmation_digest, created_at, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                confirmation.confirmation_id,
                confirmation.work_item_id,
                confirmation.revision.revision_id,
                confirmation.revision.content_digest,
                confirmation.target_contract_digest,
                confirmation.binding_digest,
                confirmation.confirmation_number,
                confirmation.confirmation_digest,
                confirmation.created_at,
                json.dumps(
                    confirmation.model_dump(mode="json"),
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            ),
        )
    return confirmation.confirmation_id


def _corrupt_latest_record(path: Path, corruption: str) -> None:
    with sqlite3.connect(path) as connection:
        row = connection.execute(
            """
            SELECT confirmation_id, payload_json
            FROM content_target_mapping_confirmations
            ORDER BY created_at DESC, confirmation_id DESC
            LIMIT 1
            """
        ).fetchone()
        assert row is not None
        confirmation_id = str(row[0])
        if corruption == "scalar_mismatch":
            connection.execute(
                "UPDATE content_target_mapping_confirmations SET revision_digest = ? "
                "WHERE confirmation_id = ?",
                ("e" * 64, confirmation_id),
            )
            return
        if corruption == "blob_payload":
            serialized: object = sqlite3.Binary(b"\xffprivate-payload")
        else:
            payload = json.loads(str(row[1]))
            if corruption == "unknown_version":
                payload["version"] = "private_packet_v2"
            elif corruption == "malformed_aggregate":
                payload.pop("confirmation")
            elif corruption == "preview_digest_mismatch":
                payload["preview_snapshot_digest"] = "f" * 64
            elif corruption == "binding_digest_mismatch":
                payload["preview_snapshot"]["components"][0]["label"] = "Zmieniona etykieta"
                payload["preview_snapshot_digest"] = _canonical_digest(payload["preview_snapshot"])
            elif corruption == "confirmation_digest_mismatch":
                payload["confirmation"]["confirmation_digest"] = "0" * 64
                connection.execute(
                    "UPDATE content_target_mapping_confirmations "
                    "SET confirmation_digest = ? WHERE confirmation_id = ?",
                    ("0" * 64, confirmation_id),
                )
            elif corruption == "selection_mismatch":
                payload["confirmation"]["selections"][0]["layout_name"] = "not_observed"
            else:
                raise AssertionError(f"Unknown test corruption: {corruption}")
            serialized = json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        connection.execute(
            "UPDATE content_target_mapping_confirmations SET payload_json = ? "
            "WHERE confirmation_id = ?",
            (serialized, confirmation_id),
        )


def test_confirmation_roundtrip_persists_exact_preview_and_coherent_scalars(
    tmp_path: Path,
) -> None:
    revision, _, _, preview, command = _preview_and_command()
    store = ContentWorkflowStore(tmp_path / "mapping.sqlite3")

    result = store.record_target_mapping_confirmation(
        work_item_id=revision.work_item_id,
        preview=preview,
        command=command,
    )
    assert preview.target is not None
    assert preview.binding_digest is not None
    loaded_confirmation = store.load_target_mapping_confirmation(
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        target_contract_digest=preview.target.target_contract_digest,
        binding_digest=preview.binding_digest,
    )
    state = store.load_target_mapping_draft_state(
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
    )

    assert result.status == "created"
    assert loaded_confirmation == result.confirmation
    assert state is not None
    assert state.status == "snapshot_available"
    assert state.confirmation == result.confirmation
    assert state.preview_snapshot == preview.model_copy(update={"confirmation": None}, deep=True)

    with sqlite3.connect(store.path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute("SELECT * FROM content_target_mapping_confirmations").fetchone()
    assert row is not None
    payload = json.loads(row["payload_json"])
    assert payload["record_type"] == "content_target_mapping_confirmation"
    assert payload["version"] == 1
    assert payload["preview_snapshot"]["confirmation"] is None
    assert payload["preview_snapshot_digest"] == _canonical_digest(payload["preview_snapshot"])
    expected_scalars = content_target_mapping_confirmation_scalars(result.confirmation)
    assert {key: row[key] for key in expected_scalars} == expected_scalars


def test_confirmation_retry_keeps_original_id_and_snapshot(tmp_path: Path) -> None:
    revision, _, _, preview, command = _preview_and_command()
    store = ContentWorkflowStore(tmp_path / "mapping.sqlite3")

    first = store.record_target_mapping_confirmation(
        work_item_id=revision.work_item_id,
        preview=preview,
        command=command,
    )
    retry_preview = preview.model_copy(deep=True)
    retry_preview.caveats.append("Nowszy tekst informacyjny nie zmienia decyzji człowieka.")
    retried = store.record_target_mapping_confirmation(
        work_item_id=revision.work_item_id,
        preview=retry_preview,
        command=command,
    )
    state = store.load_target_mapping_draft_state(
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
    )

    assert first.status == "created"
    assert retried.status == "idempotent"
    assert retried.confirmation.confirmation_id == first.confirmation.confirmation_id
    assert state is not None
    assert state.status == "snapshot_available"
    assert state.preview_snapshot == preview.model_copy(update={"confirmation": None}, deep=True)
    assert state.preview_snapshot != retry_preview
    assert _confirmation_row_count(store.path) == 1


def test_stale_confirmation_command_leaves_no_row(tmp_path: Path) -> None:
    revision, _, _, preview, command = _preview_and_command()
    store = ContentWorkflowStore(tmp_path / "stale.sqlite3")
    stale_command = command.model_copy(update={"expected_revision_digest": "e" * 64})

    with pytest.raises(ValueError, match="Rewizja dokumentu zmieniła się"):
        store.record_target_mapping_confirmation(
            work_item_id=revision.work_item_id,
            preview=preview,
            command=stale_command,
        )

    assert _confirmation_row_count(store.path) == 0


def test_mismatched_store_work_item_cannot_reuse_another_aggregate(tmp_path: Path) -> None:
    _, _, _, preview, command = _preview_and_command()
    store = ContentWorkflowStore(tmp_path / "mismatched-work-item.sqlite3")
    other_work_item_id = "content_work_item_other"
    other_preview = preview.model_copy(
        update={"work_item_id": other_work_item_id},
        deep=True,
    )
    store.record_target_mapping_confirmation(
        work_item_id=other_work_item_id,
        preview=other_preview,
        command=command,
    )

    with pytest.raises(ValueError, match="nie pasuje do podglądu"):
        store.record_target_mapping_confirmation(
            work_item_id=other_work_item_id,
            preview=preview,
            command=command,
        )

    assert _confirmation_row_count(store.path) == 1


def test_failed_atomic_insert_leaves_no_partial_row(tmp_path: Path) -> None:
    revision, _, _, preview, command = _preview_and_command()
    store = ContentWorkflowStore(tmp_path / "failed-insert.sqlite3")
    assert (
        store.load_target_mapping_draft_state(
            work_item_id=revision.work_item_id,
            revision_id=revision.revision_id,
        )
        is None
    )
    with sqlite3.connect(store.path) as connection:
        connection.execute(
            """
            CREATE TRIGGER force_target_mapping_insert_failure
            BEFORE INSERT ON content_target_mapping_confirmations
            BEGIN
              SELECT RAISE(FAIL, 'forced target mapping insert failure');
            END
            """
        )

    with pytest.raises(sqlite3.IntegrityError, match="forced target mapping insert failure"):
        store.record_target_mapping_confirmation(
            work_item_id=revision.work_item_id,
            preview=preview,
            command=command,
        )

    assert _confirmation_row_count(store.path) == 0


def test_legacy_confirmation_blocks_draft_until_explicit_snapshot_confirmation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision, review, discovery, preview, command = _preview_and_command()
    store = _RouteStore(
        tmp_path / "legacy.sqlite3",
        revision=revision,
        review=review,
    )
    legacy_confirmation_id = _insert_legacy_confirmation(
        store,
        preview=preview,
        command=command,
    )
    state = store.load_target_mapping_draft_state(
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
    )
    assert state is not None
    assert state.status == "legacy_confirmation"
    assert state.preview_snapshot is None

    live_discovery_allowed = False
    discovery_calls = 0

    def controlled_discovery(work_item_id: str) -> ContentTargetDiscovery:
        nonlocal discovery_calls
        discovery_calls += 1
        if not live_discovery_allowed:
            raise AssertionError("Legacy draft preview must not call vendor discovery.")
        assert work_item_id == revision.work_item_id
        return discovery

    monkeypatch.setattr(content_target_mapping, "content_workflow_store", lambda: store)
    monkeypatch.setattr(
        content_target_mapping,
        "build_content_target_discovery",
        controlled_discovery,
    )
    path = _target_mapping_path(revision)

    app = _route_app()
    draft_response = _route_request(app, "GET", path + "/draft-preview")

    assert draft_response.status_code == 200
    blocked = draft_response.json()
    assert blocked["status"] == "blocked"
    assert [blocker["code"] for blocker in blocked["blockers"]] == ["mapping_stale"]
    assert blocked["confirmation"] is None
    assert blocked["components"] == []
    assert blocked["root_field"] is None
    assert blocked["payload_digest"] is None
    assert discovery_calls == 0

    live_discovery_allowed = True
    _assert_legacy_action_blocked(app, path, revision, monkeypatch)

    created_response = _route_request(
        app,
        "POST",
        path + "/confirmation",
        payload=command.model_dump(mode="json"),
    )
    retry_response = _route_request(
        app,
        "POST",
        path + "/confirmation",
        payload=command.model_dump(mode="json"),
    )

    assert created_response.status_code == 200
    assert created_response.json()["status"] == "created"
    created = created_response.json()["confirmation"]
    assert created["confirmation_number"] == 2
    assert created["confirmation_id"] != legacy_confirmation_id
    assert retry_response.status_code == 200
    assert retry_response.json()["status"] == "idempotent"
    assert retry_response.json()["confirmation"]["confirmation_id"] == created["confirmation_id"]
    assert _confirmation_row_count(store.path) == 2
    latest = store.load_target_mapping_draft_state(
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
    )
    assert latest is not None
    assert latest.status == "snapshot_available"


@pytest.mark.parametrize(
    "corruption",
    "unknown_version malformed_aggregate preview_digest_mismatch binding_digest_mismatch "  # noqa: SIM905 -- compact case table stays within the changed-file budget.
    "confirmation_digest_mismatch selection_mismatch scalar_mismatch blob_payload".split(),
)
def test_corrupt_latest_record_fails_closed_without_discovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    corruption: str,
) -> None:
    revision, _, _, preview, command = _preview_and_command()
    store = ContentWorkflowStore(tmp_path / f"corrupt-{corruption}.sqlite3")
    store.record_target_mapping_confirmation(
        work_item_id=revision.work_item_id,
        preview=preview,
        command=command,
    )
    _corrupt_latest_record(store.path, corruption)
    discovery_calls = 0

    def fail_discovery(_: str) -> ContentTargetDiscovery:
        nonlocal discovery_calls
        discovery_calls += 1
        raise AssertionError("Corrupt local state must not fall back to vendor discovery.")

    monkeypatch.setattr(content_target_mapping, "content_workflow_store", lambda: store)
    monkeypatch.setattr(
        content_target_mapping,
        "build_content_target_discovery",
        fail_discovery,
    )

    with pytest.raises(ContentTargetMappingPersistenceError) as caught:
        _route_request(
            _route_app(),
            "GET",
            _target_mapping_path(revision),
        )

    assert discovery_calls == 0
    assert "private_packet_v2" not in str(caught.value)


def test_mapping_and_draft_preview_gets_survive_restart_without_discovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision, review, discovery, _, command = _preview_and_command()
    path = tmp_path / "snapshot-read.sqlite3"
    store = _RouteStore(path, revision=revision, review=review)
    monkeypatch.setattr(content_target_mapping, "content_workflow_store", lambda: store)
    monkeypatch.setattr(
        content_target_mapping,
        "build_content_target_discovery",
        lambda work_item_id: discovery,
    )
    app = _route_app()
    route = _target_mapping_path(revision)
    created_response = _route_request(
        app,
        "POST",
        route + "/confirmation",
        payload=command.model_dump(mode="json"),
    )
    assert created_response.status_code == 200
    created = created_response.json()["confirmation"]

    restarted = _RouteStore(path, revision=revision, review=review)
    discovery_calls = 0

    def fail_discovery(_: str) -> ContentTargetDiscovery:
        nonlocal discovery_calls
        discovery_calls += 1
        raise AssertionError("Persisted snapshot reads must not call vendor discovery.")

    monkeypatch.setattr(content_target_mapping, "content_workflow_store", lambda: restarted)
    monkeypatch.setattr(
        content_target_mapping,
        "build_content_target_discovery",
        fail_discovery,
    )

    mapping_response = _route_request(app, "GET", route)
    draft_response = _route_request(app, "GET", route + "/draft-preview")

    assert mapping_response.status_code == 200
    mapping = mapping_response.json()
    assert mapping["status"] == "ready_for_human_mapping"
    assert mapping["confirmation"]["confirmation_id"] == created["confirmation_id"]
    assert draft_response.status_code == 200
    draft = draft_response.json()
    assert draft["status"] == "ready"
    assert draft["confirmation"]["confirmation_id"] == created["confirmation_id"]
    assert draft["components"][1]["fields"][1]["value"] == ("<p>Sprawdź działalność firmy.</p>")
    assert discovery_calls == 0

    restarted.review = review.model_copy(
        update={
            "decision_id": "review_bdo_persisted_2",
            "decision_number": 2,
            "decision": "needs_changes",
            "notes": "Dokument wymaga ponownej korekty.",
        }
    )
    revoked_mapping_response = _route_request(app, "GET", route)
    revoked_draft_response = _route_request(app, "GET", route + "/draft-preview")

    assert revoked_mapping_response.status_code == 200
    revoked_mapping = revoked_mapping_response.json()
    assert revoked_mapping["status"] == "blocked"
    assert revoked_mapping["blockers"][0]["code"] == "revision_not_approved"
    assert revoked_mapping["confirmation"] is None
    assert revoked_draft_response.status_code == 200
    revoked_draft = revoked_draft_response.json()
    assert revoked_draft["status"] == "blocked"
    assert revoked_draft["blockers"][0]["code"] == "mapping_stale"
    assert discovery_calls == 0


def test_draft_action_requires_live_discovery_even_when_snapshot_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision, review, discovery, _, command = _preview_and_command()
    store = _RouteStore(
        tmp_path / "draft-action-live.sqlite3",
        revision=revision,
        review=review,
    )
    monkeypatch.setattr(content_target_mapping, "content_workflow_store", lambda: store)
    monkeypatch.setattr(
        content_target_mapping,
        "build_content_target_discovery",
        lambda work_item_id: discovery,
    )
    app = _route_app()
    route = _target_mapping_path(revision)
    created_response = _route_request(
        app,
        "POST",
        route + "/confirmation",
        payload=command.model_dump(mode="json"),
    )
    assert created_response.status_code == 200
    draft_response = _route_request(app, "GET", route + "/draft-preview")
    assert draft_response.status_code == 200
    draft = draft_response.json()
    assert draft["status"] == "ready"

    discovery_calls = 0
    action_persisted = False

    def unavailable_discovery(_: str) -> None:
        nonlocal discovery_calls
        discovery_calls += 1
        return None

    def fail_action_persistence(_: object) -> object:
        nonlocal action_persisted
        action_persisted = True
        raise AssertionError("Unavailable live discovery must not create an action.")

    monkeypatch.setattr(
        content_target_mapping,
        "build_content_target_discovery",
        unavailable_discovery,
    )
    monkeypatch.setattr(
        content_target_mapping,
        "persist_content_target_draft_action",
        fail_action_persistence,
    )
    action_response = _route_request(
        app,
        "POST",
        route + "/draft-action",
        payload={
            "expected_revision_digest": revision.content_digest,
            "expected_target_contract_digest": draft["target"]["target_contract_digest"],
            "expected_confirmation_digest": draft["confirmation"]["confirmation_digest"],
            "expected_payload_digest": draft["payload_digest"],
            "requested_by": "Marta Kowalska",
        },
    )

    assert action_response.status_code == 404
    assert discovery_calls == 1
    assert action_persisted is False
