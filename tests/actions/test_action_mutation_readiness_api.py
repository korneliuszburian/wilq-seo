from __future__ import annotations

from typing import Any, cast

from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app


def _get_mutation_readiness(action_id: str) -> dict[str, Any]:
    response = TestClient(app).get(
        f"/api/actions/{action_id}/mutation-readiness",
    )
    assert response.status_code == 200
    data = cast(dict[str, Any], response.json())
    assert data["response_type"] == "action_mutation_readiness"
    return data


def _get_mutation_readiness_summary() -> dict[str, Any]:
    response = TestClient(app).get("/api/actions/mutation-readiness")
    assert response.status_code == 200
    data = cast(dict[str, Any], response.json())
    assert data["response_type"] == "action_mutation_readiness_summary"
    return data


def test_action_mutation_readiness_blocks_prepare_only_action(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "actions.sqlite3"))

    data = _get_mutation_readiness("act_prepare_wordpress_draft_handoff")

    assert data["ready_to_request_apply"] is False
    assert data["vendor_write_possible"] is False
    assert data["would_attempt_vendor_write"] is False
    assert data["mutation_adapter"] is None
    assert data["mode"] == "prepare"
    assert data["source_connectors"] == ["wordpress_ekologus"]
    assert data["evidence_ids"]
    apply_contract = data["apply_contract"]
    assert apply_contract["allowed_operation"] == "create_wordpress_draft"
    assert apply_contract["required_mode"] == "apply"
    assert apply_contract["draft_only"] is True
    assert apply_contract["publication_allowed"] is False
    assert apply_contract["destructive_allowed"] is False
    assert apply_contract["adapter_status"] == "not_implemented"
    assert "WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES" in apply_contract["required_env_flags"]
    assert "wordpress_publish" in apply_contract["blocked_outputs"]
    blocker_codes = [blocker["code"] for blocker in data["blockers"]]
    assert "missing_apply_mode" in blocker_codes
    assert "missing_mutation_adapter" in blocker_codes
    assert any(
        requirement["code"] == "mutation_adapter" and requirement["satisfied"] is False
        for requirement in data["requirements"]
    )
    assert "validate" in data["operator_next_step"]


def test_action_mutation_readiness_exposes_blocked_wordpress_apply_action(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "actions_apply.sqlite3"))
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES", "0")

    data = _get_mutation_readiness("act_apply_wordpress_draft_handoff")

    assert data["mode"] == "apply"
    assert data["ready_to_request_apply"] is False
    assert data["vendor_write_possible"] is False
    assert data["would_attempt_vendor_write"] is False
    assert data["mutation_adapter"] == "wordpress_draft_execution_boundary"
    assert data["apply_contract"]["allowed_operation"] == "create_wordpress_draft"
    assert data["apply_contract"]["adapter_status"] == "implemented"
    assert data["apply_contract"]["publication_allowed"] is False
    blocker_codes = [blocker["code"] for blocker in data["blockers"]]
    requirement_codes = {requirement["code"] for requirement in data["requirements"]}
    assert "missing_apply_mode" not in blocker_codes
    assert "missing_payload_apply_allowed" in blocker_codes
    assert "missing_mutation_adapter" not in blocker_codes
    assert "wordpress_draft_write_readiness" in requirement_codes
    assert "wordpress_draft_live_write_env" in requirement_codes
    assert "wordpress_write_authorization" in requirement_codes
    assert "missing_wordpress_draft_write_readiness" in blocker_codes
    assert "missing_wordpress_draft_live_write_env" in blocker_codes
    assert "missing_wordpress_write_authorization" in blocker_codes


def test_wordpress_apply_action_blocks_payload_before_vendor_write(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "actions_apply_block.sqlite3"))

    response = TestClient(app).post(
        "/api/actions/act_apply_wordpress_draft_handoff/apply",
        json={"confirm": True, "confirmed_by": "operator_test"},
    )

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["status"] == "blocked"
    assert detail["applied"] is False
    assert detail["mutation_audit"]["mutation_attempted"] is False
    assert detail["mutation_audit"]["mutation_adapter"] == "wordpress_draft_execution_boundary"
    assert detail["adapter_result"] is None
    serialized = str(detail)
    assert "Payload akcji nie pozwala jeszcze na zapis zmian." in serialized
    assert "Payload akcji nie jest gotowy do mutacji API." in serialized


def test_action_mutation_readiness_summary_reports_no_vendor_writes(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "actions_summary.sqlite3"))
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES", "0")

    data = _get_mutation_readiness_summary()

    assert data["action_count"] >= 1
    assert data["vendor_write_possible_count"] == 0
    assert data["would_attempt_vendor_write_count"] == 0
    assert data["missing_adapter_count"] == data["action_count"] - 1
    assert "missing_mutation_adapter" in data["top_blockers"]
    assert data["first_write_candidate"]["action_id"] == "act_apply_wordpress_draft_handoff"
    assert data["first_write_candidate"]["vendor_write_possible"] is False
    assert data["first_write_candidate"]["mutation_adapter"] == "wordpress_draft_execution_boundary"
    assert data["first_write_candidate"]["apply_contract"]["adapter_status"] == "implemented"
    assert "WordPress draft-only" in data["first_write_candidate_reason"]
    assert any("draft-only" in step for step in data["activation_plan_steps"])
    assert "apply-mode WordPress draft-only" in data["activation_next_step"]
    assert data["items"][0]["response_type"] == "action_mutation_readiness"
    assert "adapter" in data["operator_next_step"]


def test_action_mutation_readiness_returns_404_for_unknown_action() -> None:
    response = TestClient(app).get(
        "/api/actions/no-such-action/mutation-readiness",
    )

    assert response.status_code == 404
