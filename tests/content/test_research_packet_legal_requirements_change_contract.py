"""Parent-safe observer for legal requirement identifier validation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def _command_model() -> Any:
    try:
        from wilq.content.workflow.research_packet_contracts import (
            ContentResearchPacketCommand,
        )
    except ImportError:  # pragma: no cover - parent tree must stay collection-safe
        return None
    return ContentResearchPacketCommand


def _payload(requirements: tuple[str, ...]) -> dict[str, object]:
    return {
        "source_pack_binding_id": "pack",
        "source_pack_binding_digest": "a" * 64,
        "identity_binding_id": "identity",
        "identity_binding_digest": "b" * 64,
        "current_work_item_id": "work-item",
        "content_kind": "service",
        "legal_source_requirements": requirements,
        "recorded_by": "test_actor",
        "recorded_at": datetime(2026, 1, 1, tzinfo=UTC),
    }


def test_server_owned_validator_accepts_domain_ids_and_rejects_secret_like_values() -> None:
    command_model = _command_model()
    assert command_model is not None, "server-owned command model must exist"

    requirements = ("operat_2026_administrative_charges", "operat_validity")
    try:
        accepted = command_model.model_validate(_payload(requirements))
    except ValueError as error:
        raise AssertionError(
            "server-owned validator must accept a 32+ character domain requirement id"
        ) from error
    assert accepted.legal_source_requirements == requirements

    try:
        command_model.model_validate(_payload(("sk-" + "a" * 24,)))
    except ValueError:
        pass
    else:
        raise AssertionError("server-owned validator must reject a secret-like value")
