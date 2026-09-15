"""Parent-safe source observer for the server-owned approval command."""

from pathlib import Path


def _source(root: Path, relative: str) -> str:
    path = root / relative
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def test_current_disposition_server_owned_approval_contract() -> None:
    root = Path(__file__).resolve().parents[2]
    approval = _source(root, "wilq/content/workflow/current_disposition_approval.py")
    router = _source(root, "apps/api/wilq_api/routers/content_current_disposition_authority.py")
    generic_actions = _source(root, "apps/api/wilq_api/routers/actions.py")
    chain = _source(root, "wilq/actions/action_chain.py")
    change_gate = _source(root, "scripts/_change_contract_observer.py")

    assert "def approve_current_disposition_authority(" in approval
    assert "with _action_serialization(action_id):" in approval
    assert "audit.list_audit_events(action_id=action_id)" in approval
    assert "def _matching_receipt(" in approval
    assert "action_service.record_action_review(" in approval
    assert "action_service.confirm_action(" in approval
    assert "action_service.impact_check_action(" in approval
    assert "action_service.apply_action(" in approval

    assert '"/api/content/current-disposition-authorities/{action_id}/approve"' in router
    assert "content_current_disposition_approve_endpoint" in router
    assert "status_code=409" in router

    assert "CURRENT_DISPOSITION_ACTION_TYPE" in generic_actions
    assert "current_disposition_approval_required" in generic_actions
    assert "canonical_endpoint" in generic_actions

    assert "key=lambda event: (event.created_at, event.id)" in chain

    assert "if candidate_presence is not True:" in change_gate
    assert '"mapping-missing-candidate"' in change_gate
