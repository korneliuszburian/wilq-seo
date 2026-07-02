from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.api.wilq_api.main import app
from wilq.schemas import (
    ConnectorCapability,
    ConnectorStatus,
    ConnectorStatusValue,
    FreshnessState,
)
from wilq.social.history import (
    EKOLOGUS_LINKEDIN_PUBLIC_POSTS_URL,
    SOCIAL_HISTORY_REQUIRED_METADATA_FIELDS,
    SocialHistoryInventorySource,
    audit_social_history_metadata_payload,
    build_social_history_inventory,
    social_history_input_example,
)

client = TestClient(app)


def _connector_status(
    connector_id: str,
    *,
    configured: bool,
) -> ConnectorStatus:
    return ConnectorStatus(
        id=connector_id,
        label=connector_id,
        status=(
            ConnectorStatusValue.configured
            if configured
            else ConnectorStatusValue.missing_credentials
        ),
        configured=configured,
        missing_credentials=[] if configured else [f"{connector_id.upper()}_TOKEN"],
        freshness=FreshnessState(state="unknown"),
        capabilities=ConnectorCapability(read=True, write=False),
        health_check="credential_presence",
    )


def test_social_history_inventory_is_metadata_only_and_read_only() -> None:
    inventory = build_social_history_inventory(
        {
            "linkedin": _connector_status("linkedin", configured=False),
            "facebook": _connector_status("facebook", configured=False),
        },
        {
            "linkedin": ["LINKEDIN_ACCESS_TOKEN"],
            "facebook": ["FACEBOOK_PAGE_ACCESS_TOKEN"],
        },
    )

    payload = inventory.model_dump(mode="json")

    assert payload["contract"] == "social_history_inventory_v1"
    assert payload["read_only"] is True
    assert payload["status"] == "missing"
    assert payload["duplicate_risk_status"] == "blocked_until_social_history_review"
    assert payload["required_sources"] == ["linkedin", "facebook"]
    assert payload["missing_evidence_ids"] == [
        "linkedin_historical_posts",
        "facebook_historical_posts",
    ]
    assert {source["channel"] for source in payload["sources"]} == {
        "linkedin",
        "facebook",
    }
    assert {
        source["connector_access_status"] for source in payload["sources"]
    } == {"missing_credentials"}
    assert all(
        source["required_metadata_fields"] == SOCIAL_HISTORY_REQUIRED_METADATA_FIELDS
        for source in payload["sources"]
    )
    assert all(
        source["safe_collection_mode"] == "metadata_only"
        for source in payload["sources"]
    )
    assert all(source["raw_post_body_allowed"] is False for source in payload["sources"])
    assert "twierdzenie że temat jest nowy bez historii postów" in payload[
        "blocked_uses"
    ]
    assert "automatyczne zatwierdzenie" in " ".join(payload["blocked_uses"])
    assert payload["discovery_seeds"] == [
        {
            "id": "social_history_seed_ekologus_linkedin_posts",
            "channel": "linkedin",
            "source_type": "public_posts_url",
            "source_url": EKOLOGUS_LINKEDIN_PUBLIC_POSTS_URL,
            "status": "seeded_not_collected",
            "safe_collection_mode": "metadata_only",
            "raw_post_body_allowed": False,
            "required_review": True,
            "operator_note": (
                "Publiczny adres postów LinkedIn Ekologus jest tylko punktem "
                "startowym discovery. WILQ nie traktuje go jako gotowej historii "
                "postów, dopóki metadata-only inventory nie zostanie zebrane i "
                "sprawdzone."
            ),
        }
    ]


def test_social_history_inventory_rejects_raw_post_body_contract_fields() -> None:
    with pytest.raises(ValidationError):
        SocialHistoryInventorySource(
            channel="linkedin",
            connector_id="linkedin",
            connector_access_status="configured",
            required_evidence_id="linkedin_historical_posts",
            raw_post_body_allowed=True,
        )

    with pytest.raises(ValidationError):
        SocialHistoryInventorySource(
            channel="linkedin",
            connector_id="linkedin",
            connector_access_status="configured",
            required_evidence_id="linkedin_historical_posts",
            raw_post_body_required=True,
        )


def test_social_history_metadata_audit_accepts_complete_metadata_only_history() -> None:
    audit = audit_social_history_metadata_payload(social_history_input_example())

    payload = audit.model_dump(mode="json")

    assert payload["contract"] == "social_history_inventory_v1"
    assert payload["read_only"] is True
    assert payload["status"] == "review_ready"
    assert payload["item_count"] == 2
    assert payload["channel_counts"] == {"facebook": 1, "linkedin": 1}
    assert payload["missing_required_sources"] == []
    assert payload["errors"] == []
    assert payload["duplicate_free_claim_allowed"] is False
    assert payload["publish_allowed"] is False
    assert "bez powtórek" in payload["operator_next_step"]


def test_social_history_metadata_audit_blocks_missing_channel() -> None:
    example = social_history_input_example()
    example["items"] = [example["items"][0]]  # type: ignore[index]

    audit = audit_social_history_metadata_payload(example).model_dump(mode="json")

    assert audit["status"] == "invalid"
    assert audit["channel_counts"] == {"linkedin": 1}
    assert audit["missing_required_sources"] == ["facebook"]
    assert any("Missing required social history sources" in error for error in audit["errors"])
    assert audit["duplicate_free_claim_allowed"] is False


def test_social_history_metadata_audit_rejects_raw_private_fields() -> None:
    example = social_history_input_example()
    example["items"][0]["raw_post_body"] = "Pełna treść posta"  # type: ignore[index]
    example["items"][1]["comments"] = ["komentarz"]  # type: ignore[index]

    audit = audit_social_history_metadata_payload(example).model_dump(mode="json")

    assert audit["status"] == "invalid"
    assert audit["item_count"] == 0
    assert audit["missing_required_sources"] == ["linkedin", "facebook"]
    assert any("raw_post_body" in error for error in audit["errors"])
    assert any("comments" in error for error in audit["errors"])


def test_social_history_inventory_endpoint_exposes_public_discovery_seed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "social_history.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "social_history.duckdb"))
    monkeypatch.delenv("LINKEDIN_ORGANIZATION_ID", raising=False)
    monkeypatch.delenv("LINKEDIN_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("FACEBOOK_PAGE_ID", raising=False)
    monkeypatch.delenv("FACEBOOK_PAGE_ACCESS_TOKEN", raising=False)

    response = client.get("/api/social/history-inventory")

    assert response.status_code == 200
    payload = response.json()
    assert payload["contract"] == "social_history_inventory_v1"
    assert payload["status"] == "missing"
    assert payload["required_sources"] == ["linkedin", "facebook"]
    assert {
        source["connector_access_status"] for source in payload["sources"]
    } == {"missing_credentials"}
    assert payload["discovery_seeds"][0]["source_url"] == EKOLOGUS_LINKEDIN_PUBLIC_POSTS_URL
    assert payload["discovery_seeds"][0]["safe_collection_mode"] == "metadata_only"
    assert payload["discovery_seeds"][0]["raw_post_body_allowed"] is False
