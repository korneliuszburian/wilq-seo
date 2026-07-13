from __future__ import annotations

from typing import Any, cast

from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from wilq.connectors.wordpress.client import (
    WordPressDraftPostReadback,
    WordPressDraftReadError,
)
from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.handoff.wordpress import ContentWordPressDraftHandoff
from wilq.content.handoff.wordpress_execution import (
    ContentWordPressDraftWriteAuthorization,
    execute_content_wordpress_draft_handoff,
)
from wilq.content.workflow.store import content_workflow_store
from wilq.schemas import AuditEvent
from wilq.storage.local_state import local_state_store


def _draft_package(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": "draft_package_content_work_item_bdo",
        "work_item_id": "content_work_item_bdo",
        "brief_id": "sales_brief_content_work_item_bdo",
        "claim_ledger_id": "claim_ledger_bdo",
        "draft_kind": "outline",
        "title": "BDO dla firm: co trzeba sprawdzić przed działaniem",
        "sections": [
            {
                "heading": "Kogo dotyczy BDO",
                "purpose": "Wyjaśnij, kiedy firma powinna sprawdzić obowiązki BDO.",
                "evidence_ids": ["ev_gsc_bdo", "ev_wp_bdo"],
                "draft_notes": ["CTA bez obietnicy wyniku."],
            }
        ],
        "section_to_evidence_map": [
            {
                "section_heading": "Kogo dotyczy BDO",
                "evidence_ids": ["ev_gsc_bdo", "ev_wp_bdo"],
            }
        ],
        "claims_used": ["Ekologus pomaga firmom uporządkować obowiązki BDO."],
        "claims_removed_or_blocked": [],
        "human_review_questions": ["Czy szkic brzmi jak Ekologus?"],
        "publish_ready": False,
    }
    payload.update(overrides)
    return payload


def _wordpress_handoff(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": "wordpress_draft_handoff_content_work_item_bdo",
        "work_item_id": "content_work_item_bdo",
        "draft_package_id": "draft_package_content_work_item_bdo",
        "human_review_id": "human_review_bdo",
        "audit_id": "audit_bdo",
        "title": "BDO dla firm: co trzeba sprawdzić przed działaniem",
        "final_canonical_url": "https://ekologus.pl/bdo/",
        "intended_final_url": "https://ekologus.pl/bdo/",
        "preview_url": "https://ekologus.dev.proudsite.pl/bdo/",
        "evidence_ids": ["ev_gsc_bdo", "ev_wp_bdo"],
        "publish_allowed": False,
        "destructive_update_allowed": False,
    }
    payload.update(overrides)
    return payload


def _post_wordpress_execution(payload: dict[str, Any]) -> dict[str, Any]:
    response = TestClient(app).post(
        "/api/content/work-items/wordpress-draft-execution",
        json=payload,
    )
    assert response.status_code == 200
    data = cast(dict[str, Any], response.json())
    assert sorted(data) == ["execution_result"]
    return data


def _get_wordpress_write_readiness(action_id: str | None = None) -> dict[str, Any]:
    response = TestClient(app).get(
        "/api/content/wordpress/draft-write-readiness",
        params={"action_id": action_id} if action_id is not None else None,
    )
    assert response.status_code == 200
    data = cast(dict[str, Any], response.json())
    assert data["response_type"] == "wordpress_draft_write_readiness"
    return data


def _get_wordpress_activation_packet(work_item_id: str | None = None) -> dict[str, Any]:
    params = {"work_item_id": work_item_id} if work_item_id is not None else None
    response = TestClient(app).get(
        "/api/content/wordpress/draft-activation-packet",
        params=params,
    )
    assert response.status_code == 200
    data = cast(dict[str, Any], response.json())
    assert data["response_type"] == "wordpress_draft_activation_packet"
    return data


def _write_authorization(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "action_id": "act_prepare_wordpress_draft_handoff",
        "preview_audit_id": "audit_preview_123",
        "review_audit_id": "audit_review_123",
        "confirmation_audit_id": "audit_confirm_123",
        "apply_audit_id": None,
        "confirmed_by": "wilku",
    }
    payload.update(overrides)
    return payload


def _human_review_from_snapshot(
    item: dict[str, Any],
    draft: dict[str, Any],
    **overrides: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": f"human_review_{item['id']}",
        "work_item_id": item["id"],
        "stage": "draft_package",
        "reviewed_by": "wilku",
        "decision": "approved",
        "notes": "Review zatwierdza wyłącznie szkic WordPress, bez publikacji.",
        "checked_items": [
            "Treść brzmi jak Ekologus.",
            "Claim Ledger i dowody zostały sprawdzone.",
            "Materiał zostaje szkicem WordPress, bez publikacji.",
        ],
        "evidence_ids": item["evidence_ids"],
        "blocked_claims_handled": draft["claims_removed_or_blocked"],
        "draft_package_id": draft["id"],
    }
    payload.update(overrides)
    return payload


def _audit_from_review(
    item: dict[str, Any],
    review: dict[str, object],
) -> dict[str, object]:
    return {
        "audit_id": f"audit_{item['id']}",
        "actor": "wilku",
        "reason": "Zatwierdzony materiał może trafić wyłącznie do szkicu WordPress.",
        "evidence_ids": item["evidence_ids"],
        "human_review_id": review["id"],
    }


def test_wordpress_activation_packet_shows_next_draft_only_blockers(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "activation_packet.sqlite3"))
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES", "false")

    data = _get_wordpress_activation_packet()

    assert data["contract"] == "wordpress_draft_activation_packet_v1"
    assert data["action_id"] == "act_apply_wordpress_draft_handoff"
    assert data["work_item_id"]
    assert data["draft_package_ready"] is True
    assert data["draft_package_id"]
    assert data["review_preview_ready"] is True
    assert (
        data["review_preview_status_label"]
        == "Paczka szkicu jest gotowa do review człowieka."
    )
    assert "generyczny artykuł SEO" in " ".join(data["human_review_checklist"])
    assert data["human_review_ready"] is False
    assert data["audit_ready"] is False
    assert data["handoff_ready"] is False
    assert data["dry_run_ready"] is False
    assert data["live_write_enabled_by_env"] is False
    assert data["publish_allowed"] is False
    assert data["destructive_update_allowed"] is False
    assert data["external_write_attempted"] is False
    assert data["handoff_blockers"] == ["missing_human_review", "missing_audit"]
    assert set(data["execution_blockers"]) == {"missing_handoff"}
    assert data["activation_missing_step"] == "human_review"
    assert data["activation_missing_step_label"] == "zapisz review człowieka"
    assert data["activation_missing_readiness_labels"] == [
        "review człowieka",
        "audit przekazania",
        "handoff WordPress",
        "podgląd dry-run",
    ]
    assert data["execution_result"]["status"] == "blocked"
    assert data["execution_result"]["external_write_attempted"] is False
    assert "review człowieka" in data["operator_next_step"]
    assert any("human review" in step for step in data["next_steps"])
    assert data["evidence_ids"]
    assert "wordpress_ekologus" in data["source_connectors"]


def test_wordpress_activation_packet_follows_saved_review_and_audit(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv(
        "WILQ_STATE_DB",
        str(tmp_path / "activation_packet_transition.sqlite3"),
    )
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES", "false")
    client = TestClient(app)

    initial_packet = _get_wordpress_activation_packet()
    work_item_id = initial_packet["work_item_id"]
    snapshot = client.get(f"/api/content/work-items/{work_item_id}/snapshot").json()
    item = snapshot["preflight"]["item"]
    draft = snapshot["draft_package"]["draft_package_result"]["draft_package"]
    assert draft is not None

    review = _human_review_from_snapshot(item, draft)
    review_response = client.post(
        f"/api/content/work-items/{work_item_id}/human-review",
        json={"review": review},
    )
    assert review_response.status_code == 200
    assert review_response.json()["wordpress_handoff_allowed"] is True

    after_review = _get_wordpress_activation_packet(work_item_id)
    assert after_review["human_review_ready"] is True
    assert after_review["audit_ready"] is False
    assert after_review["handoff_ready"] is False
    assert after_review["dry_run_ready"] is False
    assert after_review["external_write_attempted"] is False
    assert after_review["handoff_blockers"] == ["missing_audit"]
    assert after_review["execution_blockers"] == ["missing_handoff"]
    assert after_review["activation_missing_step"] == "audit"
    assert (
        after_review["activation_missing_step_label"]
        == "zapisz audit przekazania do WordPress"
    )
    assert after_review["activation_missing_readiness_labels"] == [
        "audit przekazania",
        "handoff WordPress",
        "podgląd dry-run",
    ]
    assert after_review["human_review_checklist"] == [
        "Review człowieka jest zapisane; teraz sprawdź audyt i handoff WordPress."
    ]

    audit_response = client.post(
        f"/api/content/work-items/{work_item_id}/audit",
        json={"audit": _audit_from_review(item, review)},
    )
    assert audit_response.status_code == 200
    assert audit_response.json()["handoff_result"]["blockers"] == []

    after_audit = _get_wordpress_activation_packet(work_item_id)
    assert after_audit["human_review_ready"] is True
    assert after_audit["audit_ready"] is True
    assert after_audit["handoff_ready"] is True
    assert after_audit["dry_run_ready"] is True
    assert after_audit["live_write_enabled_by_env"] is False
    assert after_audit["publish_allowed"] is False
    assert after_audit["destructive_update_allowed"] is False
    assert after_audit["external_write_attempted"] is False
    assert after_audit["handoff_blockers"] == []
    assert after_audit["execution_blockers"] == []
    assert after_audit["activation_missing_step"] == "ready"
    assert (
        after_audit["activation_missing_step_label"]
        == "podgląd draft-only jest gotowy do review"
    )
    assert after_audit["activation_missing_readiness_labels"] == []
    assert after_audit["execution_result"]["status"] == "dry_run_ready"
    assert after_audit["execution_result"]["payload"]["post_status"] == "draft"
    assert after_audit["execution_result"]["external_write_attempted"] is False


def test_wordpress_activation_packet_can_scope_to_selected_work_item(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv(
        "WILQ_STATE_DB",
        str(tmp_path / "activation_packet_selected.sqlite3"),
    )

    default_packet = _get_wordpress_activation_packet()
    selected_packet = _get_wordpress_activation_packet(default_packet["work_item_id"])

    assert selected_packet["work_item_id"] == default_packet["work_item_id"]
    assert selected_packet["topic"] == default_packet["topic"]
    assert selected_packet["external_write_attempted"] is False


def test_wordpress_activation_packet_returns_404_for_unavailable_work_item(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv(
        "WILQ_STATE_DB",
        str(tmp_path / "activation_packet_missing.sqlite3"),
    )

    response = TestClient(app).get(
        "/api/content/wordpress/draft-activation-packet",
        params={"work_item_id": "content_work_item_missing"},
    )

    assert response.status_code == 404


def test_wordpress_execution_api_returns_draft_only_dry_run(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "wordpress_dry_run.sqlite3"))
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES", "false")

    data = _post_wordpress_execution(
        {
            "handoff": _wordpress_handoff(),
            "draft_package": _draft_package(),
            "mode": "dry_run",
        }
    )

    result = data["execution_result"]
    assert result["status"] == "dry_run_ready"
    assert result["mode"] == "dry_run"
    assert result["external_write_attempted"] is False
    assert result["wordpress_post_id"] is None
    assert result["blockers"] == []
    assert result["boundary"] == {
        "allowed_operation": "create_wordpress_draft",
        "dry_run_default": True,
        "live_write_enabled": False,
        "live_adapter_configured": False,
        "publish_allowed": False,
        "destructive_update_allowed": False,
    }
    payload = result["payload"]
    assert payload["connector"] == "wordpress_ekologus"
    assert payload["endpoint_kind"] == "posts"
    assert payload["post_status"] == "draft"
    assert payload["publish_allowed"] is False
    assert payload["destructive_update_allowed"] is False
    assert payload["final_canonical_url"] == "https://ekologus.pl/bdo/"
    assert "# BDO dla firm: co trzeba sprawdzić przed działaniem" in payload[
        "content_markdown"
    ]


def test_wordpress_execution_api_uses_section_overrides_in_draft_payload(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "wordpress_section_overrides.sqlite3"))
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES", "false")

    data = _post_wordpress_execution(
        {
            "handoff": _wordpress_handoff(),
            "draft_package": _draft_package(),
            "mode": "dry_run",
            "section_overrides": [
                {
                    "heading": "Kogo dotyczy BDO",
                    "body_markdown": (
                        "BDO dotyczy firm, które wprowadzają produkty, "
                        "opakowania albo odpady do ewidencji."
                    ),
                    "evidence_ids": ["ev_gsc_bdo"],
                }
            ],
        }
    )

    result = data["execution_result"]
    assert result["status"] == "dry_run_ready"
    assert result["boundary"]["publish_allowed"] is False
    assert result["boundary"]["destructive_update_allowed"] is False
    markdown = result["payload"]["content_markdown"]
    assert "## Kogo dotyczy BDO" in markdown
    assert "BDO dotyczy firm, które wprowadzają produkty" in markdown
    assert "Wyjaśnij, kiedy firma powinna sprawdzić obowiązki BDO." not in markdown


def test_wordpress_execution_api_blocks_live_write(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "wordpress_live_blocked.sqlite3"))
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES", "false")

    data = _post_wordpress_execution(
        {
            "handoff": _wordpress_handoff(),
            "draft_package": _draft_package(),
            "mode": "live",
        }
    )

    result = data["execution_result"]
    assert result["status"] == "blocked"
    assert result["payload"] is None
    assert result["external_write_attempted"] is False
    assert result["boundary"]["live_write_enabled"] is False
    assert result["boundary"]["live_adapter_configured"] is False
    assert result["boundary"]["publish_allowed"] is False
    assert result["boundary"]["destructive_update_allowed"] is False
    assert [blocker["code"] for blocker in result["blockers"]] == ["action_apply_required"]


def test_wordpress_execution_api_live_write_requires_write_authorization(
    monkeypatch,
) -> None:
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES", "true")

    data = _post_wordpress_execution(
        {
            "handoff": _wordpress_handoff(),
            "draft_package": _draft_package(),
            "mode": "live",
        }
    )

    result = data["execution_result"]
    assert result["status"] == "blocked"
    assert result["external_write_attempted"] is False
    assert result["boundary"]["live_write_enabled"] is True
    assert result["boundary"]["live_adapter_configured"] is False
    assert result["boundary"]["publish_allowed"] is False
    assert result["boundary"]["destructive_update_allowed"] is False
    assert [blocker["code"] for blocker in result["blockers"]] == ["action_apply_required"]


def test_wordpress_execution_api_live_write_rejects_unpersisted_authorization(
    monkeypatch,
) -> None:
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES", "true")

    data = _post_wordpress_execution(
        {
            "handoff": _wordpress_handoff(),
            "draft_package": _draft_package(),
            "mode": "live",
            "write_authorization": _write_authorization(),
        }
    )

    result = data["execution_result"]
    assert result["status"] == "blocked"
    assert result["external_write_attempted"] is False
    assert result["boundary"]["live_write_enabled"] is True
    assert result["boundary"]["live_adapter_configured"] is False
    assert result["boundary"]["publish_allowed"] is False
    assert result["boundary"]["destructive_update_allowed"] is False
    assert [blocker["code"] for blocker in result["blockers"]] == ["action_apply_required"]


def test_wordpress_execution_api_rejects_persisted_prepare_authorization(
    monkeypatch,
    tmp_path,
) -> None:
    execution_arguments: dict[str, object] = {}
    real_execute = execute_content_wordpress_draft_handoff

    def capture_execution(**kwargs: object):  # type: ignore[no-untyped-def]
        execution_arguments.update(kwargs)
        return real_execute(**kwargs)  # type: ignore[arg-type]

    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "wordpress_write.sqlite3"))
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES", "true")
    monkeypatch.setattr(
        "wilq.content.workflow.api.execute_content_wordpress_draft_handoff",
        capture_execution,
    )
    _persist_write_authorization_events()

    data = _post_wordpress_execution(
        {
            "handoff": _wordpress_handoff(),
            "draft_package": _draft_package(),
            "mode": "live",
            "write_authorization": _write_authorization(),
        }
    )

    result = data["execution_result"]
    assert result["status"] == "blocked"
    assert result["mode"] == "live"
    assert result["wordpress_post_id"] is None
    assert result["external_write_attempted"] is False
    assert result["boundary"]["live_write_enabled"] is True
    assert result["boundary"]["live_adapter_configured"] is False
    assert result["boundary"]["publish_allowed"] is False
    assert result["boundary"]["destructive_update_allowed"] is False
    assert [blocker["code"] for blocker in result["blockers"]] == ["action_apply_required"]
    assert execution_arguments["create_draft"] is None
    assert execution_arguments["action_apply_authorized"] is False


def test_wordpress_activation_packet_remembers_created_dev_draft(
    monkeypatch,
    tmp_path,
) -> None:
    created_titles: list[str] = []

    def create_draft(payload) -> str:  # type: ignore[no-untyped-def]
        created_titles.append(payload.title)
        return "888"

    def read_draft(post_id: str) -> WordPressDraftPostReadback:
        assert post_id == "888"
        return WordPressDraftPostReadback(
            post_id=post_id,
            status="draft",
            title="BDO dla firm - szkic dev",
            link="https://ekologus.dev.proudsite.pl/?p=888",
            modified_gmt="2026-07-07T10:00:00",
            content_summary="Szkic opisuje obowiązki BDO i CTA do konsultacji.",
            content_word_count=86,
            acf_field_count=2,
            acf_field_names=["glowny_opis", "elementy"],
        )

    monkeypatch.setenv(
        "WILQ_STATE_DB",
        str(tmp_path / "activation_packet_created_draft.sqlite3"),
    )
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES", "true")
    monkeypatch.setattr(
        "wilq.content.workflow.stage_activation.read_wordpress_draft_post",
        read_draft,
    )
    _persist_write_authorization_events()
    client = TestClient(app)

    initial_packet = _get_wordpress_activation_packet()
    work_item_id = initial_packet["work_item_id"]
    snapshot = client.get(f"/api/content/work-items/{work_item_id}/snapshot").json()
    item = snapshot["preflight"]["item"]
    draft = snapshot["draft_package"]["draft_package_result"]["draft_package"]
    assert draft is not None

    review = _human_review_from_snapshot(item, draft)
    review_response = client.post(
        f"/api/content/work-items/{work_item_id}/human-review",
        json={"review": review},
    )
    assert review_response.status_code == 200
    audit_response = client.post(
        f"/api/content/work-items/{work_item_id}/audit",
        json={"audit": _audit_from_review(item, review)},
    )
    assert audit_response.status_code == 200

    ready_snapshot = client.get(f"/api/content/work-items/{work_item_id}/snapshot").json()
    handoff = ready_snapshot["wordpress_handoff"]["handoff_result"]["handoff"]
    execution_result = execute_content_wordpress_draft_handoff(
        handoff=ContentWordPressDraftHandoff.model_validate(handoff),
        draft_package=ContentDraftPackage.model_validate(draft),
        mode="live",
        live_write_enabled=True,
        create_draft=create_draft,
        action_apply_authorized=True,
        write_authorization=ContentWordPressDraftWriteAuthorization.model_validate(
            _write_authorization()
        ),
        write_authorization_verified=True,
    )
    assert execution_result.status == "created"
    content_workflow_store().save_wordpress_draft_execution(
        work_item_id,
        execution_result,
    )

    refreshed_packet = _get_wordpress_activation_packet(work_item_id)

    assert refreshed_packet["execution_result"]["status"] == "created"
    assert refreshed_packet["execution_result"]["mode"] == "live"
    assert refreshed_packet["execution_result"]["wordpress_post_id"] == "888"
    assert refreshed_packet["dry_run_ready"] is True
    assert refreshed_packet["live_write_enabled_by_env"] is True
    assert refreshed_packet["activation_missing_step"] == "ready"
    assert refreshed_packet["activation_missing_readiness_labels"] == []
    assert refreshed_packet["execution_result"]["boundary"]["publish_allowed"] is False
    assert refreshed_packet["execution_result"]["boundary"]["destructive_update_allowed"] is False
    assert refreshed_packet["execution_result"]["external_write_attempted"] is True
    assert refreshed_packet["draft_readback"]["status"] == "available"
    assert refreshed_packet["draft_readback"]["wordpress_post_id"] == "888"
    assert refreshed_packet["draft_readback"]["post_status"] == "draft"
    assert refreshed_packet["draft_readback"]["title"] == "BDO dla firm - szkic dev"
    assert refreshed_packet["draft_readback"]["content_word_count"] == 86
    assert refreshed_packet["draft_readback"]["acf_field_names"] == [
        "glowny_opis",
        "elementy",
    ]
    assert created_titles == [draft["title"]]


def test_wordpress_activation_packet_keeps_created_result_when_readback_fails(
    monkeypatch,
    tmp_path,
) -> None:
    def create_draft(_payload) -> str:  # type: ignore[no-untyped-def]
        return "889"

    def read_draft(_post_id: str) -> WordPressDraftPostReadback:
        raise WordPressDraftReadError("WordPress REST nie zwrócił szkicu.")

    monkeypatch.setenv(
        "WILQ_STATE_DB",
        str(tmp_path / "activation_packet_readback_failure.sqlite3"),
    )
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES", "true")
    monkeypatch.setattr(
        "wilq.content.workflow.stage_activation.read_wordpress_draft_post",
        read_draft,
    )
    _persist_write_authorization_events()
    client = TestClient(app)

    initial_packet = _get_wordpress_activation_packet()
    work_item_id = initial_packet["work_item_id"]
    snapshot = client.get(f"/api/content/work-items/{work_item_id}/snapshot").json()
    item = snapshot["preflight"]["item"]
    draft = snapshot["draft_package"]["draft_package_result"]["draft_package"]
    assert draft is not None

    review = _human_review_from_snapshot(item, draft)
    assert client.post(
        f"/api/content/work-items/{work_item_id}/human-review",
        json={"review": review},
    ).status_code == 200
    assert client.post(
        f"/api/content/work-items/{work_item_id}/audit",
        json={"audit": _audit_from_review(item, review)},
    ).status_code == 200

    ready_snapshot = client.get(f"/api/content/work-items/{work_item_id}/snapshot").json()
    handoff = ready_snapshot["wordpress_handoff"]["handoff_result"]["handoff"]
    execution_result = execute_content_wordpress_draft_handoff(
        handoff=ContentWordPressDraftHandoff.model_validate(handoff),
        draft_package=ContentDraftPackage.model_validate(draft),
        mode="live",
        live_write_enabled=True,
        create_draft=create_draft,
        action_apply_authorized=True,
        write_authorization=ContentWordPressDraftWriteAuthorization.model_validate(
            _write_authorization()
        ),
        write_authorization_verified=True,
    )
    assert execution_result.status == "created"
    content_workflow_store().save_wordpress_draft_execution(
        work_item_id,
        execution_result,
    )

    refreshed_packet = _get_wordpress_activation_packet(work_item_id)

    assert refreshed_packet["execution_result"]["status"] == "created"
    assert refreshed_packet["execution_result"]["wordpress_post_id"] == "889"
    assert refreshed_packet["dry_run_ready"] is True
    assert refreshed_packet["activation_missing_step"] == "ready"
    assert refreshed_packet["draft_readback"]["status"] == "blocked"
    assert refreshed_packet["draft_readback"]["wordpress_post_id"] == "889"
    assert refreshed_packet["draft_readback"]["blockers"][0]["code"] == (
        "wordpress_draft_read_failed"
    )


def test_wordpress_execution_adapter_failure_is_sanitized_after_action_apply(
    monkeypatch,
    tmp_path,
) -> None:
    class AdapterFailure(RuntimeError):
        public_message = "WordPress odrzucił szkic testowy."

    def create_draft(_payload) -> str:  # type: ignore[no-untyped-def]
        raise AdapterFailure("secret technical details")

    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "wordpress_failure.sqlite3"))
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES", "true")
    _persist_write_authorization_events()
    result = execute_content_wordpress_draft_handoff(
        handoff=ContentWordPressDraftHandoff.model_validate(_wordpress_handoff()),
        draft_package=ContentDraftPackage.model_validate(_draft_package()),
        mode="live",
        live_write_enabled=True,
        create_draft=create_draft,
        action_apply_authorized=True,
        write_authorization=ContentWordPressDraftWriteAuthorization.model_validate(
            _write_authorization()
        ),
        write_authorization_verified=True,
    )

    assert result.status == "blocked"
    assert result.external_write_attempted is True
    assert result.boundary.live_write_enabled is True
    assert result.boundary.live_adapter_configured is True
    assert [blocker.code for blocker in result.blockers] == ["live_adapter_failed"]
    assert result.blockers[0].reason == "WordPress odrzucił szkic testowy."
    assert "secret technical details" not in str(result.model_dump(mode="json"))


def test_wordpress_write_readiness_blocks_when_live_env_is_disabled(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "wordpress_readiness.sqlite3"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    monkeypatch.delenv("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES", raising=False)
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_URL", "https://example.test")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_USERNAME", "wilq")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_APP_PASSWORD", "app-password")

    data = _get_wordpress_write_readiness()

    assert data["ready"] is False
    assert data["live_write_enabled_by_env"] is False
    assert data["rest_adapter_configured"] is True
    assert data["suggested_write_authorization"] is None
    assert data["source_connectors"] == ["wordpress_ekologus"]
    assert data["evidence_ids"] == ["ev_connector_wordpress_ekologus_status"]
    assert "draft_writes_env_disabled" in [blocker["code"] for blocker in data["blockers"]]
    assert data["write_authorization_status"] == "missing_audit_trace"
    assert data["missing_audit_event_types"] == [
        "action_preview_generated",
        "human_review_*",
        "action_apply_confirmed",
    ]
    assert [requirement["satisfied"] for requirement in data["required_audit_events"]] == [
        False,
        False,
        False,
    ]


def test_wordpress_write_readiness_blocks_independent_authorization_from_audit_trail(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "wordpress_readiness_ready.sqlite3"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES", "true")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_URL", "https://example.test")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_USERNAME", "wilq")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_APP_PASSWORD", "app-password")
    _persist_write_authorization_events()

    data = _get_wordpress_write_readiness()

    assert data["ready"] is False
    assert data["live_write_enabled_by_env"] is True
    assert data["rest_adapter_configured"] is True
    assert [blocker["code"] for blocker in data["blockers"]] == ["actionobject_apply_path_required"]
    assert data["write_authorization_status"] == "blocked_outside_action_apply"
    assert data["missing_audit_event_types"] == []
    assert data["suggested_write_authorization"] is None
    assert [requirement["satisfied"] for requirement in data["required_audit_events"]] == [
        True,
        True,
        True,
    ]
    assert "apply-capable ActionObject" in data["operator_next_step"]


def test_wordpress_write_readiness_rejects_existing_update_prepare_audits(
    monkeypatch,
    tmp_path,
) -> None:
    action_id = "act_prepare_wordpress_existing_draft_update"
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "wrong_action.sqlite3"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES", "true")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_URL", "https://example.test")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_USERNAME", "wilq")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_APP_PASSWORD", "app-password")
    _persist_write_authorization_events(action_id=action_id)

    data = _get_wordpress_write_readiness(action_id)

    assert data["action_id"] == action_id
    assert data["ready"] is False
    assert data["write_authorization_status"] == "blocked_outside_action_apply"
    assert data["suggested_write_authorization"] is None
    assert "actionobject_apply_path_required" in [blocker["code"] for blocker in data["blockers"]]


def test_wordpress_write_readiness_reports_actor_mismatch(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv(
        "WILQ_STATE_DB",
        str(tmp_path / "wordpress_readiness_actor_mismatch.sqlite3"),
    )
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES", "true")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_URL", "https://example.test")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_USERNAME", "wilq")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_APP_PASSWORD", "app-password")
    for event_id, event_type, actor in [
        ("audit_preview_123", "action_preview_generated", "wilq_api"),
        ("audit_review_123", "human_review_approved_for_prepare", "wilku"),
        ("audit_confirm_123", "action_apply_confirmed", ""),
    ]:
        local_state_store().save_audit_event(
            AuditEvent(
                id=event_id,
                action_id="act_prepare_wordpress_draft_handoff",
                event_type=event_type,
                actor=actor,
                summary="Testowy ślad audytu z pustym aktorem confirm.",
                evidence_ids=["ev_gsc_bdo", "ev_wp_bdo"],
            )
        )

    data = _get_wordpress_write_readiness()

    assert data["ready"] is False
    assert data["write_authorization_status"] == "audit_actor_mismatch"
    assert data["missing_audit_event_types"] == []
    assert data["suggested_write_authorization"] is None
    assert [blocker["code"] for blocker in data["blockers"]] == [
        "actionobject_apply_path_required",
        "audit_actor_mismatch",
    ]


def _persist_write_authorization_events(
    *,
    action_id: str = "act_prepare_wordpress_draft_handoff",
) -> None:
    for event_id, event_type, actor in [
        ("audit_preview_123", "action_preview_generated", "wilq_api"),
        ("audit_review_123", "human_review_approved_for_prepare", "wilku"),
        ("audit_confirm_123", "action_apply_confirmed", "wilku"),
    ]:
        local_state_store().save_audit_event(
            AuditEvent(
                id=event_id,
                action_id=action_id,
                event_type=event_type,
                actor=actor,
                summary="Testowy ślad audytu dla zapisu szkicu.",
                evidence_ids=["ev_gsc_bdo", "ev_wp_bdo"],
            )
        )
