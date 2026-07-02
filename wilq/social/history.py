from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from wilq.schemas import ConnectorStatus

SOCIAL_HISTORY_REQUIRED_SOURCES = ["linkedin", "facebook"]
SOCIAL_HISTORY_MISSING_EVIDENCE_IDS = [
    "linkedin_historical_posts",
    "facebook_historical_posts",
]
SOCIAL_HISTORY_REQUIRED_METADATA_FIELDS = [
    "channel",
    "published_at",
    "topic",
    "service",
    "claim",
    "cta",
    "format",
    "post_url_or_id",
    "source_evidence_id",
]


class SocialHistoryInventorySource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: Literal["linkedin", "facebook"]
    connector_id: Literal["linkedin", "facebook"]
    inventory_status: Literal["missing"] = "missing"
    connector_access_status: Literal[
        "configured",
        "missing_credentials",
        "unavailable",
    ]
    required_evidence_id: str
    required_metadata_fields: list[str] = Field(
        default_factory=lambda: list(SOCIAL_HISTORY_REQUIRED_METADATA_FIELDS)
    )
    safe_collection_mode: Literal["metadata_only"] = "metadata_only"
    raw_post_body_allowed: Literal[False] = False


class SocialHistoryInventory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract: Literal["social_history_inventory_v1"] = "social_history_inventory_v1"
    read_only: Literal[True] = True
    status: Literal["missing"] = "missing"
    status_label: str = "brak spisu historycznych postów LinkedIn/Facebook"
    duplicate_risk_status: Literal[
        "blocked_until_social_history_review"
    ] = "blocked_until_social_history_review"
    required_sources: list[Literal["linkedin", "facebook"]] = Field(
        default_factory=lambda: list(SOCIAL_HISTORY_REQUIRED_SOURCES)
    )
    missing_evidence_ids: list[str] = Field(
        default_factory=lambda: list(SOCIAL_HISTORY_MISSING_EVIDENCE_IDS)
    )
    sources: list[SocialHistoryInventorySource]
    allowed_uses: list[str] = Field(
        default_factory=lambda: [
            "sprawdzenie czy temat, claim albo CTA powtarza wcześniejsze posty",
            "ocena kadencji i kąta komunikacji przed przygotowaniem szkicu",
            "brand-voice/cadence evidence po review metadanych",
        ]
    )
    blocked_uses: list[str] = Field(
        default_factory=lambda: [
            "twierdzenie że temat jest nowy bez historii postów",
            "twierdzenie że nie powielamy wcześniejszych postów",
            "automatyczne zatwierdzenie claimów prawnych, usługowych albo produktowych",
            "publikacja bez ActionObject review, preview, zgody i audytu",
        ]
    )
    dedupe_requirements: list[str] = Field(
        default_factory=lambda: [
            "porównać temat i usługę z historią LinkedIn/Facebook",
            "porównać claim i CTA z ostatnimi postami",
            "oznaczyć reuse jako dozwolony tylko z innym kątem albo po decyzji review",
        ]
    )
    operator_next_step: str = (
        "Zbierz albo zaimportuj metadata-only historię LinkedIn/Facebook: kanał, data, "
        "temat, usługa, claim, CTA, format i post ID. Do tego czasu WILQ może "
        "przygotować tylko review-only kierunki postów i nie może obiecać braku powtórzeń."
    )


def build_social_history_inventory(
    connector_status_by_id: dict[str, ConnectorStatus],
    missing_publish_access: dict[str, list[str]],
) -> SocialHistoryInventory:
    sources = []
    for channel in SOCIAL_HISTORY_REQUIRED_SOURCES:
        connector = connector_status_by_id.get(channel)
        connector_access_status: Literal[
            "configured",
            "missing_credentials",
            "unavailable",
        ] = (
            "missing_credentials"
            if channel in missing_publish_access
            else "configured"
            if connector and connector.configured
            else "unavailable"
        )
        sources.append(
            SocialHistoryInventorySource(
                channel=channel,
                connector_id=channel,
                connector_access_status=connector_access_status,
                required_evidence_id=f"{channel}_historical_posts",
            )
        )
    return SocialHistoryInventory(sources=sources)
