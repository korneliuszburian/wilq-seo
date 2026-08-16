from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace

from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from tests.content.test_new_page_draft_action import _command, _ready_readiness
from wilq.actions import apply_lifecycle, wordpress_draft_readback
from wilq.actions import service as action_service
from wilq.content.workflow.store.store_new_page_apply import NewPageApplyPersistedResult
from wilq.content.workflow.target.new_page_draft_action import (
    create_new_page_draft_action,
    persist_new_page_draft_action,
)
from wilq.schemas import (
    ActionApplyRequest,
    ActionConfirmRequest,
    ActionImpactCheckRequest,
    ActionPreviewRequest,
    ActionReviewRequest,
)


class _ClaimStore:
    def __init__(self) -> None:
        self.claims: list[tuple[str, str]] = []
        self.finished: list[tuple[str, str, str, str, dict | None]] = []
        self.persisted_result: NewPageApplyPersistedResult | None = None

    def claim_new_page_revision_apply(self, binding, *, action_id: str, claimed_by: str) -> str:
        self.claims.append((binding.revision_id, action_id))
        return "acquired"

    def finish_new_page_revision_apply_claim(
        self,
        binding,
        *,
        status: str,
        audit_event,
        mutation_audit,
        adapter_result=None,
    ) -> None:
        self.finished.append(
            (
                binding.revision_id,
                status,
                audit_event.id,
                mutation_audit.id,
                adapter_result,
            )
        )
        if status == "applied" and adapter_result is not None:
            self.persisted_result = NewPageApplyPersistedResult(
                wordpress_post_id=str(adapter_result["wordpress_post_id"]),
                status=str(adapter_result["status"]),
                link=str(adapter_result.get("link") or ""),
                edit_link=str(adapter_result.get("edit_link") or ""),
            )

    def result_for_action(self, action_id: str) -> NewPageApplyPersistedResult | None:
        return self.persisted_result


def _configured_connector() -> SimpleNamespace:
    return SimpleNamespace(
        configured=True,
        label="WordPress Ekologus",
        status=SimpleNamespace(value="configured"),
    )


def test_uncertain_new_page_apply_claim_has_typed_recovery_blocker() -> None:
    blocker = apply_lifecycle._new_page_apply_claim_blocker("uncertain")

    assert blocker.code == "new_page_revision_apply_result_uncertain"
    assert "duplikat" in blocker.reason
    assert "nie ponawiaj" in blocker.next_step


def test_new_page_action_requires_the_full_lifecycle_before_one_exact_dev_draft(
    monkeypatch,
) -> None:
    action = create_new_page_draft_action(_ready_readiness(), _command())
    claim_store = _ClaimStore()
    executed: list[str] = []

    def execute(current, capability):
        executed.append(current.id)
        return (
            {
                "adapter": "content_new_page_draft_execution_boundary",
                "external_write_attempted": True,
                "created_draft_id": "draft_42",
                "wordpress_post_id": "42",
                "status": "draft",
                "link": "https://ekologus.dev.proudsite.pl/?p=42",
                "edit_link": (
                    "https://ekologus.dev.proudsite.pl/wp-admin/"
                    "post.php?post=42&action=edit"
                ),
            },
            [],
        )

    monkeypatch.setattr(
        action_service,
        "get_connector_status",
        lambda _: _configured_connector(),
    )
    monkeypatch.setattr(apply_lifecycle, "new_page_apply_claim_store", lambda: claim_store)
    monkeypatch.setattr(
        wordpress_draft_readback, "new_page_apply_claim_store", lambda: claim_store
    )
    monkeypatch.setattr(apply_lifecycle, "execute_new_page_draft_action", execute)

    binding = action.payload["new_page_draft_binding"]
    initial = action_service.apply_action(
        action,
        ActionApplyRequest(confirm=True, confirmed_by="Wilku", new_page_draft=binding),
    )
    assert initial.applied is False
    assert executed == []

    assert action_service.validate_action(action).valid
    action_service.preview_action(action, ActionPreviewRequest(requested_by="Wilku"))
    action_service.record_action_review(
        action,
        ActionReviewRequest(
            outcome="approved_for_prepare",
            reviewed_by="Wilku",
            notes="Zatwierdzam dokładną rewizję nowej strony.",
        ),
    )
    assert action_service.confirm_action(
        action,
        ActionConfirmRequest(
            confirmed_by="Wilku",
            notes="Potwierdzam utworzenie jednego szkicu na dev.",
            preview_acknowledged=True,
        ),
    ).confirmed
    assert action_service.impact_check_action(
        action,
        ActionImpactCheckRequest(
            checked_by="Wilku",
            notes="Kontrola gotowości szkicu zakończona.",
        ),
    ).status == "checked"

    result = action_service.apply_action(
        action,
        ActionApplyRequest(confirm=True, confirmed_by="Wilku", new_page_draft=binding),
    )

    assert result.applied is True
    assert result.mutation_audit.new_page_draft_binding is not None
    assert result.mutation_audit.new_page_draft_binding.revision_id == binding["revision_id"]
    assert executed == [action.id]
    assert claim_store.claims == [(binding["revision_id"], action.id)]
    assert claim_store.finished == [
        (
            binding["revision_id"],
            "applied",
            result.audit_event.id,
            result.mutation_audit.id,
            result.adapter_result,
        )
    ]


def test_new_page_action_rejects_stale_confirm_before_claim_or_executor(monkeypatch) -> None:
    action = create_new_page_draft_action(_ready_readiness(), _command())
    claim_store = _ClaimStore()
    executed: list[str] = []
    monkeypatch.setattr(action_service, "get_connector_status", lambda _: _configured_connector())
    monkeypatch.setattr(apply_lifecycle, "new_page_apply_claim_store", lambda: claim_store)
    monkeypatch.setattr(
        apply_lifecycle,
        "execute_new_page_draft_action",
        lambda current, capability: executed.append(current.id) or (None, []),
    )
    binding = action.payload["new_page_draft_binding"]
    assert action_service.validate_action(action).valid
    action_service.preview_action(action, ActionPreviewRequest(requested_by="Wilku"))
    action_service.record_action_review(
        action,
        ActionReviewRequest(
            outcome="approved_for_prepare",
            reviewed_by="Wilku",
            notes="Zatwierdzam dokładną rewizję nowej strony.",
        ),
    )
    action_service.confirm_action(
        action,
        ActionConfirmRequest(
            confirmed_by="Wilku",
            notes="Potwierdzam utworzenie jednego szkicu na dev.",
            preview_acknowledged=True,
        ),
    )
    action_service.impact_check_action(
        action,
        ActionImpactCheckRequest(
            checked_by="Wilku",
            notes="Kontrola gotowości szkicu zakończona.",
        ),
    )
    preview = next(
        event
        for event in action.audit_events
        if event.event_type == "action_preview_generated"
    )
    confirmation = next(
        event
        for event in action.audit_events
        if event.event_type == "action_apply_confirmed"
    )
    preview.created_at = confirmation.created_at + timedelta(seconds=1)

    result = action_service.apply_action(
        action,
        ActionApplyRequest(confirm=True, confirmed_by="Wilku", new_page_draft=binding),
    )

    assert result.applied is False
    assert [blocker.code for blocker in result.wordpress_revision_blockers] == [
        "wordpress_action_chain_order_invalid"
    ]
    assert result.mutation_audit.external_write_attempted is False
    assert claim_store.claims == []
    assert executed == []


def test_new_page_action_rejects_a_changed_apply_binding_before_claim_or_executor(
    monkeypatch,
) -> None:
    action = create_new_page_draft_action(_ready_readiness(), _command())
    claim_store = _ClaimStore()
    monkeypatch.setattr(
        action_service,
        "get_connector_status",
        lambda _: _configured_connector(),
    )
    monkeypatch.setattr(apply_lifecycle, "new_page_apply_claim_store", lambda: claim_store)
    monkeypatch.setattr(
        wordpress_draft_readback, "new_page_apply_claim_store", lambda: claim_store
    )
    monkeypatch.setattr(
        apply_lifecycle,
        "execute_new_page_draft_action",
        lambda current, capability: (_ for _ in ()).throw(
            AssertionError("executor must not run")
        ),
    )
    changed = {**action.payload["new_page_draft_binding"], "revision_digest": "f" * 64}

    result = action_service.apply_action(
        action,
        ActionApplyRequest(confirm=True, confirmed_by="Wilku", new_page_draft=changed),
    )

    assert result.applied is False
    assert claim_store.claims == []
    assert [blocker.code for blocker in result.wordpress_revision_blockers] == [
        "new_page_revision_binding_mismatch"
    ]


def test_new_page_action_consumes_its_claim_after_a_failed_executor(monkeypatch) -> None:
    action = create_new_page_draft_action(_ready_readiness(), _command())
    claim_store = _ClaimStore()
    monkeypatch.setattr(
        action_service,
        "get_connector_status",
        lambda _: _configured_connector(),
    )
    monkeypatch.setattr(apply_lifecycle, "new_page_apply_claim_store", lambda: claim_store)
    monkeypatch.setattr(
        apply_lifecycle,
        "execute_new_page_draft_action",
        lambda current, capability: (None, ["Adapter dev odmówił utworzenia szkicu."]),
    )
    binding = action.payload["new_page_draft_binding"]
    assert action_service.validate_action(action).valid
    action_service.preview_action(action, ActionPreviewRequest(requested_by="Wilku"))
    action_service.record_action_review(
        action,
        ActionReviewRequest(
            outcome="approved_for_prepare",
            reviewed_by="Wilku",
            notes="Zatwierdzam dokładną rewizję nowej strony.",
        ),
    )
    action_service.confirm_action(
        action,
        ActionConfirmRequest(
            confirmed_by="Wilku",
            notes="Potwierdzam utworzenie jednego szkicu na dev.",
            preview_acknowledged=True,
        ),
    )
    action_service.impact_check_action(
        action,
        ActionImpactCheckRequest(
            checked_by="Wilku",
            notes="Kontrola gotowości szkicu zakończona.",
        ),
    )

    result = action_service.apply_action(
        action,
        ActionApplyRequest(confirm=True, confirmed_by="Wilku", new_page_draft=binding),
    )

    assert result.applied is False
    assert result.adapter_result is None
    assert claim_store.finished == [
        (
            binding["revision_id"],
            "failed",
            result.audit_event.id,
            result.mutation_audit.id,
            result.adapter_result,
        )
    ]


def test_new_page_action_is_reachable_through_the_public_actions_lifecycle(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "new-page-action-api.sqlite3"))
    action = persist_new_page_draft_action(
        create_new_page_draft_action(_ready_readiness(), _command())
    )
    binding = action.payload["new_page_draft_binding"]
    claim_store = _ClaimStore()
    monkeypatch.setattr(
        action_service,
        "get_connector_status",
        lambda _: _configured_connector(),
    )
    monkeypatch.setattr(apply_lifecycle, "new_page_apply_claim_store", lambda: claim_store)
    monkeypatch.setattr(
        wordpress_draft_readback, "new_page_apply_claim_store", lambda: claim_store
    )
    monkeypatch.setattr(
        apply_lifecycle,
        "execute_new_page_draft_action",
        lambda current, capability: (
            {
                "adapter": "content_new_page_draft_execution_boundary",
                "external_write_attempted": True,
                "created_draft_id": "draft_42",
                "wordpress_post_id": "42",
                "status": "draft",
                "link": "https://ekologus.dev.proudsite.pl/?p=42",
                "edit_link": (
                    "https://ekologus.dev.proudsite.pl/wp-admin/"
                    "post.php?post=42&action=edit"
                ),
            },
            [],
        ),
    )
    client = TestClient(app)

    assert client.post(f"/api/actions/{action.id}/validate").status_code == 200
    assert client.post(
        f"/api/actions/{action.id}/preview", json={"requested_by": "Wilku"}
    ).status_code == 200
    assert client.post(
        f"/api/actions/{action.id}/review",
        json={
            "outcome": "approved_for_prepare",
            "reviewed_by": "Wilku",
            "notes": "Zatwierdzam dokładną rewizję nowej strony.",
        },
    ).status_code == 200
    assert client.post(
        f"/api/actions/{action.id}/confirm",
        json={
            "confirmed_by": "Wilku",
            "notes": "Potwierdzam utworzenie jednego szkicu na dev.",
            "preview_acknowledged": True,
        },
    ).status_code == 200
    assert client.post(
        f"/api/actions/{action.id}/impact-check",
        json={
            "checked_by": "Wilku",
            "notes": "Kontrola gotowości szkicu zakończona.",
        },
    ).status_code == 200

    response = client.post(
        f"/api/actions/{action.id}/apply",
        json={"confirm": True, "confirmed_by": "Wilku", "new_page_draft": binding},
    )

    assert response.status_code == 200
    assert response.json()["mutation_audit"]["new_page_draft_binding"] == binding
    assert claim_store.finished[0][:2] == (binding["revision_id"], "applied")
    assert claim_store.finished[0][4] == response.json()["adapter_result"]
    recovered = wordpress_draft_readback.last_created_wordpress_draft_readback(
        action, []
    )
    assert recovered is not None
    assert recovered.wordpress_post_id == "42"
    assert recovered.post_status == "draft"
    assert recovered.link == "https://ekologus.dev.proudsite.pl/?p=42"
    assert recovered.edit_link == (
        "https://ekologus.dev.proudsite.pl/wp-admin/post.php?post=42&action=edit"
    )
    assert recovered.verification_status == "blocked"
    assert recovered.blockers[0].code == "wordpress_draft_verification_unavailable"
