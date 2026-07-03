from __future__ import annotations

from typing import Any, cast

from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
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


def _get_wordpress_write_readiness() -> dict[str, Any]:
    response = TestClient(app).get(
        "/api/content/wordpress/draft-write-readiness",
    )
    assert response.status_code == 200
    data = cast(dict[str, Any], response.json())
    assert data["response_type"] == "wordpress_draft_write_readiness"
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


def test_wordpress_execution_api_returns_draft_only_dry_run() -> None:
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


def test_wordpress_execution_api_blocks_live_write() -> None:
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
    assert [blocker["code"] for blocker in result["blockers"]] == [
        "live_write_not_enabled"
    ]


def test_wordpress_execution_api_live_write_requires_write_authorization(
    monkeypatch,
) -> None:
    def create_draft(_payload) -> str:  # type: ignore[no-untyped-def]
        raise AssertionError("adapter must not run without write authorization")

    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES", "true")
    monkeypatch.setattr(
        "wilq.content.workflow.api.create_wordpress_draft_post",
        create_draft,
    )

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
    assert result["boundary"]["live_adapter_configured"] is True
    assert result["boundary"]["publish_allowed"] is False
    assert result["boundary"]["destructive_update_allowed"] is False
    assert [blocker["code"] for blocker in result["blockers"]] == [
        "missing_write_authorization"
    ]


def test_wordpress_execution_api_live_write_rejects_unpersisted_authorization(
    monkeypatch,
) -> None:
    def create_draft(_payload) -> str:  # type: ignore[no-untyped-def]
        raise AssertionError("adapter must not run without persisted audit proof")

    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES", "true")
    monkeypatch.setattr(
        "wilq.content.workflow.api.create_wordpress_draft_post",
        create_draft,
    )

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
    assert result["boundary"]["live_adapter_configured"] is True
    assert result["boundary"]["publish_allowed"] is False
    assert result["boundary"]["destructive_update_allowed"] is False
    assert [blocker["code"] for blocker in result["blockers"]] == [
        "invalid_write_authorization"
    ]


def test_wordpress_execution_api_live_write_uses_persisted_authorization(
    monkeypatch,
    tmp_path,
) -> None:
    created_titles: list[str] = []

    def create_draft(payload) -> str:  # type: ignore[no-untyped-def]
        assert payload.post_status == "draft"
        assert payload.publish_allowed is False
        assert payload.destructive_update_allowed is False
        created_titles.append(payload.title)
        return "777"

    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "wordpress_write.sqlite3"))
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES", "true")
    monkeypatch.setattr(
        "wilq.content.workflow.api.create_wordpress_draft_post",
        create_draft,
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
    assert result["status"] == "created"
    assert result["mode"] == "live"
    assert result["wordpress_post_id"] == "777"
    assert result["external_write_attempted"] is True
    assert result["boundary"]["live_write_enabled"] is True
    assert result["boundary"]["live_adapter_configured"] is True
    assert result["boundary"]["publish_allowed"] is False
    assert result["boundary"]["destructive_update_allowed"] is False
    assert created_titles == ["BDO dla firm: co trzeba sprawdzić przed działaniem"]


def test_wordpress_execution_api_live_adapter_failure_is_blocked(
    monkeypatch,
    tmp_path,
) -> None:
    class AdapterFailure(RuntimeError):
        public_message = "WordPress odrzucił szkic testowy."

    def create_draft(_payload) -> str:  # type: ignore[no-untyped-def]
        raise AdapterFailure("secret technical details")

    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "wordpress_failure.sqlite3"))
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES", "true")
    monkeypatch.setattr(
        "wilq.content.workflow.api.create_wordpress_draft_post",
        create_draft,
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
    assert result["external_write_attempted"] is True
    assert result["boundary"]["live_write_enabled"] is True
    assert result["boundary"]["live_adapter_configured"] is True
    assert [blocker["code"] for blocker in result["blockers"]] == [
        "live_adapter_failed"
    ]
    assert result["blockers"][0]["reason"] == "WordPress odrzucił szkic testowy."
    assert "secret technical details" not in str(result)


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
    assert [requirement["satisfied"] for requirement in data["required_audit_events"]] == [
        False,
        False,
        False,
    ]


def test_wordpress_write_readiness_builds_authorization_from_audit_trail(
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

    assert data["ready"] is True
    assert data["live_write_enabled_by_env"] is True
    assert data["rest_adapter_configured"] is True
    assert data["blockers"] == []
    assert data["suggested_write_authorization"] == _write_authorization()
    assert [requirement["satisfied"] for requirement in data["required_audit_events"]] == [
        True,
        True,
        True,
    ]
    assert "gotowa" in data["operator_next_step"]


def _persist_write_authorization_events() -> None:
    for event_id, event_type, actor in [
        ("audit_preview_123", "action_preview_generated", "wilq_api"),
        ("audit_review_123", "human_review_approved_for_prepare", "wilku"),
        ("audit_confirm_123", "action_apply_confirmed", "wilku"),
    ]:
        local_state_store().save_audit_event(
            AuditEvent(
                id=event_id,
                action_id="act_prepare_wordpress_draft_handoff",
                event_type=event_type,
                actor=actor,
                summary="Testowy ślad audytu dla zapisu szkicu.",
                evidence_ids=["ev_gsc_bdo", "ev_wp_bdo"],
            )
        )
