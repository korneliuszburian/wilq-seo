from __future__ import annotations

import pytest
from pydantic import ValidationError

from wilq.schemas import (
    ConnectorCapability,
    ConnectorStatus,
    ConnectorStatusValue,
    FreshnessState,
)
from wilq.social.history import (
    SOCIAL_HISTORY_REQUIRED_METADATA_FIELDS,
    SocialHistoryInventorySource,
    build_social_history_inventory,
)


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
