from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from wilq.schemas import ConnectorStatus

SocialHistoryChannel = Literal["linkedin", "facebook"]
SocialHistoryInventoryStatus = Literal["missing", "invalid", "review_ready"]
SocialHistoryMetadataSourceStatus = Literal["not_configured", "invalid", "review_ready"]

SOCIAL_HISTORY_REQUIRED_SOURCES: tuple[SocialHistoryChannel, ...] = (
    "linkedin",
    "facebook",
)
SOCIAL_HISTORY_INVENTORY_FILE_ENV = "WILQ_SOCIAL_HISTORY_INVENTORY_FILE"
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
EKOLOGUS_LINKEDIN_PUBLIC_POSTS_URL = (
    "https://www.linkedin.com/company/"
    "ekologus-esg-eko-audyt-ochrona-srodowiska-dokumentacje-srodowiskowe-"
    "szkolenia-sorbenty/posts/?feedView=all"
)
EKOLOGUS_FACEBOOK_PUBLIC_POSTS_URL = "https://www.facebook.com/ekologus/?locale=pl_PL"
SOCIAL_HISTORY_FORBIDDEN_METADATA_FIELDS = [
    "raw_post_body",
    "post_body",
    "body",
    "content",
    "text",
    "comments",
    "comment_text",
    "comment_author",
    "author_email",
    "user_id",
    "profile_id",
    "access_token",
]


class SocialHistoryInventorySource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: SocialHistoryChannel
    connector_id: SocialHistoryChannel
    inventory_status: Literal["missing", "review_ready"] = "missing"
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


class SocialHistoryDiscoverySeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    channel: SocialHistoryChannel
    source_type: Literal["public_posts_url"]
    source_url: str
    status: Literal["seeded_not_collected"] = "seeded_not_collected"
    safe_collection_mode: Literal["metadata_only"] = "metadata_only"
    raw_post_body_allowed: Literal[False] = False
    required_review: Literal[True] = True
    operator_note: str


def _social_history_discovery_seeds() -> list[SocialHistoryDiscoverySeed]:
    return [
        SocialHistoryDiscoverySeed(
            id="social_history_seed_ekologus_linkedin_posts",
            channel="linkedin",
            source_type="public_posts_url",
            source_url=EKOLOGUS_LINKEDIN_PUBLIC_POSTS_URL,
            operator_note=(
                "Publiczny adres postów LinkedIn Ekologus jest tylko punktem "
                "startowym discovery. WILQ nie traktuje go jako gotowej historii "
                "postów, dopóki metadata-only inventory nie zostanie zebrane i "
                "sprawdzone."
            ),
        ),
        SocialHistoryDiscoverySeed(
            id="social_history_seed_ekologus_facebook_posts",
            channel="facebook",
            source_type="public_posts_url",
            source_url=EKOLOGUS_FACEBOOK_PUBLIC_POSTS_URL,
            operator_note=(
                "Publiczny adres strony Facebook Ekologus jest tylko punktem "
                "startowym discovery. WILQ nie traktuje go jako gotowej historii "
                "postów, dopóki metadata-only inventory nie zostanie zebrane i "
                "sprawdzone."
            ),
        ),
    ]


class SocialHistoryInventory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract: Literal["social_history_inventory_v1"] = "social_history_inventory_v1"
    read_only: Literal[True] = True
    status: SocialHistoryInventoryStatus = "missing"
    status_label: str = "brak spisu historycznych postów LinkedIn/Facebook"
    duplicate_risk_status: Literal[
        "blocked_until_social_history_review"
    ] = "blocked_until_social_history_review"
    required_sources: list[SocialHistoryChannel] = Field(
        default_factory=lambda: list(SOCIAL_HISTORY_REQUIRED_SOURCES)
    )
    missing_evidence_ids: list[str] = Field(
        default_factory=lambda: list(SOCIAL_HISTORY_MISSING_EVIDENCE_IDS)
    )
    metadata_source_configured: bool = False
    metadata_source_status: SocialHistoryMetadataSourceStatus = "not_configured"
    item_count: int = 0
    channel_counts: dict[str, int] = Field(default_factory=dict)
    import_errors: list[str] = Field(default_factory=list)
    source_evidence_ids: list[str] = Field(default_factory=list)
    sources: list[SocialHistoryInventorySource]
    discovery_seeds: list[SocialHistoryDiscoverySeed] = Field(
        default_factory=_social_history_discovery_seeds
    )
    input_template: dict[str, object] = Field(
        default_factory=lambda: social_history_input_example()
    )
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
    import_audit: SocialHistoryImportAudit | None = None,
    *,
    metadata_source_configured: bool = False,
) -> SocialHistoryInventory:
    channel_counts = (
        dict(import_audit.channel_counts)
        if import_audit is not None and import_audit.status == "review_ready"
        else {}
    )
    missing_evidence_ids = [
        f"{channel}_historical_posts"
        for channel in SOCIAL_HISTORY_REQUIRED_SOURCES
        if channel_counts.get(channel, 0) <= 0
    ]
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
                inventory_status=(
                    "review_ready" if channel_counts.get(channel, 0) > 0 else "missing"
                ),
                connector_access_status=connector_access_status,
                required_evidence_id=f"{channel}_historical_posts",
            )
        )
    status = _inventory_status(import_audit, metadata_source_configured)
    return SocialHistoryInventory(
        status=status,
        status_label=_inventory_status_label(status),
        missing_evidence_ids=missing_evidence_ids,
        metadata_source_configured=metadata_source_configured,
        metadata_source_status=_metadata_source_status(import_audit),
        item_count=import_audit.item_count if import_audit is not None else 0,
        channel_counts=channel_counts,
        import_errors=import_audit.errors if import_audit is not None else [],
        source_evidence_ids=(
            list(import_audit.source_evidence_ids)
            if import_audit is not None and import_audit.status == "review_ready"
            else []
        ),
        sources=sources,
        operator_next_step=_inventory_next_step(status),
    )


def build_social_history_inventory_from_env(
    connector_status_by_id: dict[str, ConnectorStatus],
    missing_publish_access: dict[str, list[str]],
) -> SocialHistoryInventory:
    configured_path = os.getenv(SOCIAL_HISTORY_INVENTORY_FILE_ENV)
    if not configured_path:
        return build_social_history_inventory(connector_status_by_id, missing_publish_access)

    audit = _audit_social_history_inventory_file(Path(configured_path))
    return build_social_history_inventory(
        connector_status_by_id,
        missing_publish_access,
        audit,
        metadata_source_configured=True,
    )


class SocialHistoryMetadataRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: SocialHistoryChannel
    published_at: str
    topic: str
    service: str
    claim: str
    cta: str
    format: str
    post_url_or_id: str
    source_evidence_id: str

    @field_validator(
        "published_at",
        "topic",
        "service",
        "claim",
        "cta",
        "format",
        "post_url_or_id",
        "source_evidence_id",
    )
    @classmethod
    def _non_blank(cls, value: str) -> str:
        text = value.strip()
        if not text or text.startswith("<") or text in {"-", "TODO", "todo"}:
            raise ValueError("field must be filled with reviewed metadata")
        return text


class SocialHistoryImportAudit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract: Literal["social_history_inventory_v1"] = "social_history_inventory_v1"
    read_only: Literal[True] = True
    status: Literal["invalid", "review_ready"]
    item_count: int
    channel_counts: dict[str, int]
    missing_required_sources: list[SocialHistoryChannel]
    required_metadata_fields: list[str] = Field(
        default_factory=lambda: list(SOCIAL_HISTORY_REQUIRED_METADATA_FIELDS)
    )
    forbidden_metadata_fields: list[str] = Field(
        default_factory=lambda: list(SOCIAL_HISTORY_FORBIDDEN_METADATA_FIELDS)
    )
    errors: list[str]
    source_evidence_ids: list[str] = Field(default_factory=list)
    duplicate_free_claim_allowed: Literal[False] = False
    publish_allowed: Literal[False] = False
    operator_next_step: str


def audit_social_history_metadata_payload(payload: object) -> SocialHistoryImportAudit:
    if not isinstance(payload, dict):
        return _invalid_social_history_import(["Root JSON must be an object"], item_count=0)
    items = payload.get("items")
    if not isinstance(items, list):
        return _invalid_social_history_import(["Field `items` must be a list"], item_count=0)

    errors: list[str] = []
    records: list[SocialHistoryMetadataRecord] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            errors.append(f"Item #{index}: must be an object")
            continue
        forbidden_fields = [
            field for field in SOCIAL_HISTORY_FORBIDDEN_METADATA_FIELDS if field in item
        ]
        if forbidden_fields:
            errors.append(
                f"Item #{index}: forbidden raw/private fields: "
                + ", ".join(forbidden_fields)
            )
            continue
        try:
            records.append(SocialHistoryMetadataRecord.model_validate(item))
        except ValidationError as error:
            for validation_error in error.errors():
                location = ".".join(str(part) for part in validation_error.get("loc", ()))
                message = str(validation_error.get("msg") or "invalid value")
                errors.append(f"Item #{index}: {location}: {message}")

    counts = Counter(record.channel for record in records)
    missing_sources: list[SocialHistoryChannel] = [
        channel for channel in SOCIAL_HISTORY_REQUIRED_SOURCES if counts[channel] == 0
    ]
    if missing_sources:
        errors.append(
            "Missing required social history sources: " + ", ".join(missing_sources)
        )
    status: Literal["invalid", "review_ready"] = "invalid" if errors else "review_ready"
    return SocialHistoryImportAudit(
        status=status,
        item_count=len(records),
        channel_counts=dict(sorted(counts.items())),
        missing_required_sources=missing_sources,
        errors=errors,
        source_evidence_ids=(
            sorted({record.source_evidence_id for record in records})
            if not errors
            else []
        ),
        operator_next_step=_social_history_import_next_step(status),
    )


def _audit_social_history_inventory_file(path: Path) -> SocialHistoryImportAudit:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        return _invalid_social_history_import(
            ["Could not read configured social history inventory file"],
            item_count=0,
        )
    except json.JSONDecodeError:
        return _invalid_social_history_import(
            ["Configured social history inventory file is not valid JSON"],
            item_count=0,
        )
    return audit_social_history_metadata_payload(payload)


def _inventory_status(
    import_audit: SocialHistoryImportAudit | None,
    metadata_source_configured: bool,
) -> SocialHistoryInventoryStatus:
    if import_audit is None:
        return "missing"
    if metadata_source_configured and import_audit.status == "review_ready":
        return "review_ready"
    return "invalid"


def _metadata_source_status(
    import_audit: SocialHistoryImportAudit | None,
) -> SocialHistoryMetadataSourceStatus:
    if import_audit is None:
        return "not_configured"
    return import_audit.status


def _inventory_status_label(status: SocialHistoryInventoryStatus) -> str:
    if status == "review_ready":
        return "spis historii social gotowy do oceny"
    if status == "invalid":
        return "spis historii social wymaga poprawy"
    return "brak spisu historycznych postów LinkedIn/Facebook"


def _inventory_next_step(status: SocialHistoryInventoryStatus) -> str:
    if status == "review_ready":
        return (
            "Porównaj temat, usługę, claim i CTA z metadanymi historii social. "
            "Dopiero po review zdecyduj, czy szkic jest powtórką, repurpose z innym "
            "kątem czy temat do odrzucenia. Publikacja nadal wymaga osobnej zgody."
        )
    if status == "invalid":
        return (
            "Popraw lokalny metadata-only JSON historii social. WILQ nie pokazuje "
            "ścieżki pliku ani raw treści, ale blokuje claim o braku powtórek do "
            "czasu poprawnej walidacji LinkedIn i Facebook."
        )
    return (
        "Zbierz albo zaimportuj metadata-only historię LinkedIn/Facebook: kanał, data, "
        "temat, usługa, claim, CTA, format i post ID. Do tego czasu WILQ może "
        "przygotować tylko review-only kierunki postów i nie może obiecać braku powtórzeń."
    )


def social_history_input_example() -> dict[str, object]:
    return {
        "contract": "social_history_inventory_v1",
        "collected_at": "<YYYY-MM-DD>",
        "reviewer": "<Wilku albo owner>",
        "items": [
            {
                "channel": "linkedin",
                "published_at": "2026-01-15",
                "topic": "BDO i sprawozdawczość środowiskowa",
                "service": "BDO",
                "claim": "Ekologus pomaga uporządkować obowiązki BDO",
                "cta": "kontakt z doradcą",
                "format": "post edukacyjny",
                "post_url_or_id": "https://www.linkedin.com/posts/...",
                "source_evidence_id": "linkedin_historical_posts",
            },
            {
                "channel": "facebook",
                "published_at": "2026-01-20",
                "topic": "BDO i sprawozdawczość środowiskowa",
                "service": "BDO",
                "claim": "Ekologus pomaga uporządkować obowiązki BDO",
                "cta": "kontakt z doradcą",
                "format": "post edukacyjny",
                "post_url_or_id": "facebook-post-id-or-url",
                "source_evidence_id": "facebook_historical_posts",
            },
        ],
        "_instruction": (
            "To jest metadata-only format. Nie dodawaj raw treści postów, komentarzy, "
            "danych użytkowników ani tokenów. Audit nadal nie pozwala WILQ obiecać "
            "braku powtórzeń bez osobnego review."
        ),
    }


def _invalid_social_history_import(
    errors: list[str],
    *,
    item_count: int,
) -> SocialHistoryImportAudit:
    return SocialHistoryImportAudit(
        status="invalid",
        item_count=item_count,
        channel_counts={},
        missing_required_sources=list(SOCIAL_HISTORY_REQUIRED_SOURCES),
        errors=errors,
        operator_next_step=_social_history_import_next_step("invalid"),
    )


def _social_history_import_next_step(status: str) -> str:
    if status == "review_ready":
        return (
            "Przekaż metadata-only historię do review dedupe. Nadal nie twierdź, "
            "że temat jest nowy albo bez powtórek, dopóki review nie porówna tematu, "
            "claimu, CTA i formatu z historią."
        )
    return (
        "Uzupełnij brakujące metadane i usuń raw/private fields. WILQ pozostaje "
        "w trybie review-only dla social i blokuje claim o braku powtórek."
    )
