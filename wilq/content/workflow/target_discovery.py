from __future__ import annotations

import json
from hashlib import sha256
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field

from wilq.connectors.wordpress.authoring import (
    WordPressAuthoringDevContentObject,
    build_wordpress_authoring_profile,
)
from wilq.content.workflow.inventory_binding import inventory_decision_for_work_item
from wilq.schemas import utc_now


class ContentTargetAuthoringLayout(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    fields: list[str] = Field(default_factory=list)


class ContentTargetAuthoringSurface(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["acf_flexible_content"]
    root_field: str
    layouts: list[ContentTargetAuthoringLayout] = Field(default_factory=list)


class ContentTargetContract(BaseModel):
    """Exact observed target facts; never an authorization to deliver."""

    model_config = ConfigDict(extra="forbid")

    environment: str
    object_id: str
    url: str
    post_type: str
    post_status: str
    modified: str
    template: str | None = None
    authority: Literal["observation_only"] = "observation_only"
    write_authorized: Literal[False] = False
    authoring_surface: ContentTargetAuthoringSurface | None = None


class ContentTargetObservationEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    connector_id: str
    object_id: str
    post_type: str
    url: str
    post_status: str
    modified: str
    observed_at: str


class ContentTargetDiscoveryCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    object_id: str
    url: str
    post_type: str
    post_status: str
    observation_evidence: ContentTargetObservationEvidence


class ContentTargetDiscoveryTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    object_id: str
    url: str
    post_type: str = "page"
    post_status: str
    template: str | None = None
    observed_surfaces: list[str] = Field(default_factory=list)
    target_contract: ContentTargetContract
    target_contract_digest: str = Field(min_length=64, max_length=64)
    observation_evidence: ContentTargetObservationEvidence


class ContentTargetDiscovery(BaseModel):
    """Read-only observation of a dev object, never an authorization to write."""

    model_config = ConfigDict(extra="forbid")

    response_type: Literal["content_target_discovery"] = "content_target_discovery"
    contract_version: Literal["content_target_discovery_v2"] = "content_target_discovery_v2"
    work_item_id: str
    public_url: str | None = None
    relation_status: Literal["partial", "ambiguous", "unavailable"]
    label: str
    reason: str
    target: ContentTargetDiscoveryTarget | None = None
    candidates: list[ContentTargetDiscoveryCandidate] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)


def build_content_target_discovery(work_item_id: str) -> ContentTargetDiscovery | None:
    decision = inventory_decision_for_work_item(
        work_item_id,
        read_material=False,
        allow_material_pending=True,
        include_all_metric_facts=False,
    )
    if decision is None:
        return None
    public_url = next(
        (
            value.strip()
            for value in (
                decision.source_public_url,
                decision.final_canonical_url,
                decision.page,
            )
            if value and value.strip()
        ),
        None,
    )
    profile = build_wordpress_authoring_profile("wordpress_ekologus", include_dev_content=True)
    evidence_ids = sorted(set(profile.evidence_ids))
    if public_url is None:
        return ContentTargetDiscovery(
            work_item_id=work_item_id,
            relation_status="unavailable",
            label="Brakuje publicznego adresu do porównania",
            reason="Nie można sprawdzić relacji z dev bez publicznego adresu strony.",
            evidence_ids=evidence_ids,
            caveats=[
                "Brak adresu nie blokuje pracy nad dokumentem, ale blokuje rozpoznanie targetu."
            ],
        )
    matching_items = [
        item for item in profile.dev_content.items if _path(item.link) == _path(public_url)
    ]
    if not matching_items:
        return ContentTargetDiscovery(
            work_item_id=work_item_id,
            public_url=public_url,
            relation_status="unavailable",
            label="Nie znaleziono odpowiadającego obiektu na dev",
            reason="WILQ nie znalazł na dev obiektu o tym samym adresie.",
            evidence_ids=evidence_ids,
            caveats=[
                "Różny adres nie jest dowodem, że target nie istnieje; "
                "relacja wymaga późniejszego potwierdzenia."
            ],
        )
    observed_at = utc_now().isoformat()
    if len(matching_items) > 1:
        candidates = [
            _candidate(item, profile.authoring_target, observed_at) for item in matching_items
        ]
        return ContentTargetDiscovery(
            work_item_id=work_item_id,
            public_url=public_url,
            relation_status="ambiguous",
            label="Wykryto kilka obiektów dev o tym samym adresie",
            reason=(
                "WILQ nie wybiera samodzielnie między obiektami WordPress o tej samej ścieżce."
            ),
            candidates=candidates,
            evidence_ids=sorted(
                {
                    *evidence_ids,
                    *(item.observation_evidence.evidence_id for item in candidates),
                }
            ),
            caveats=[
                "Wybór konkretnego obiektu wymaga późniejszej decyzji człowieka.",
                "Ten odczyt nie odblokowuje ACF, tworzenia draftu ani publikacji.",
            ],
        )
    target = _target(matching_items[0], profile.authoring_target, observed_at)
    return ContentTargetDiscovery(
        work_item_id=work_item_id,
        public_url=public_url,
        relation_status="partial",
        label="Znaleziono stronę dev do sprawdzenia",
        reason=(
            "WILQ odczytał konkretną stronę na dev o tym samym adresie, ale sama zgodność "
            "adresu nie potwierdza jeszcze relacji ani prawa do zapisu."
        ),
        target=target,
        evidence_ids=sorted({*evidence_ids, target.observation_evidence.evidence_id}),
        caveats=[
            "Szczegóły dotyczą odczytanego obiektu dev, nie mapowania zatwierdzonego dokumentu.",
            "Ten odczyt nie odblokowuje ACF, tworzenia draftu ani publikacji.",
        ],
    )


def _target(
    item: WordPressAuthoringDevContentObject,
    environment: str,
    observed_at: str,
) -> ContentTargetDiscoveryTarget:
    contract = _target_contract(item, environment)
    digest = _digest(contract)
    observation = _observation_evidence(item, digest, observed_at)
    return ContentTargetDiscoveryTarget(
        object_id=item.post_id,
        url=item.link,
        post_type=item.content_type,
        post_status=item.status,
        template=item.template or None,
        observed_surfaces=[contract.authoring_surface.kind] if contract.authoring_surface else [],
        target_contract=contract,
        target_contract_digest=digest,
        observation_evidence=observation,
    )


def _candidate(
    item: WordPressAuthoringDevContentObject,
    environment: str,
    observed_at: str,
) -> ContentTargetDiscoveryCandidate:
    digest = _digest(_target_contract(item, environment))
    return ContentTargetDiscoveryCandidate(
        object_id=item.post_id,
        url=item.link,
        post_type=item.content_type,
        post_status=item.status,
        observation_evidence=_observation_evidence(item, digest, observed_at),
    )


def _target_contract(
    item: WordPressAuthoringDevContentObject,
    environment: str,
) -> ContentTargetContract:
    surface = None
    if item.acf_field_name:
        surface = ContentTargetAuthoringSurface(
            kind="acf_flexible_content",
            root_field=item.acf_field_name,
            layouts=[
                ContentTargetAuthoringLayout(
                    name=section.layout_name,
                    fields=section.field_names,
                )
                for section in item.sections
            ],
        )
    return ContentTargetContract(
        environment=environment,
        object_id=item.post_id,
        url=item.link,
        post_type=item.content_type,
        post_status=item.status,
        modified=item.modified,
        template=item.template or None,
        authoring_surface=surface,
    )


def _digest(contract: ContentTargetContract) -> str:
    return sha256(
        json.dumps(
            contract.model_dump(mode="json"),
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def _observation_evidence(
    item: WordPressAuthoringDevContentObject,
    target_contract_digest: str,
    observed_at: str,
) -> ContentTargetObservationEvidence:
    payload = {
        "connector_id": "wordpress_ekologus",
        "object_id": item.post_id,
        "post_type": item.content_type,
        "url": item.link,
        "post_status": item.status,
        "modified": item.modified,
        "target_contract_digest": target_contract_digest,
    }
    evidence_id = "ev_wordpress_target_observation_" + sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()[:24]
    return ContentTargetObservationEvidence(
        evidence_id=evidence_id,
        connector_id="wordpress_ekologus",
        object_id=item.post_id,
        post_type=item.content_type,
        url=item.link,
        post_status=item.status,
        modified=item.modified,
        observed_at=observed_at,
    )


def _path(value: str) -> str:
    path = urlparse(value).path.rstrip("/")
    return path or "/"


__all__ = ["ContentTargetDiscovery", "build_content_target_discovery"]
