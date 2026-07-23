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


class ContentTargetDiscoveryTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    object_id: str
    url: str
    post_type: str = "page"
    post_status: str
    template: str | None = None
    observed_surfaces: list[str] = Field(default_factory=list)
    target_contract_digest: str = Field(min_length=64, max_length=64)


class ContentTargetDiscovery(BaseModel):
    """Read-only observation of a dev object, never an authorization to write."""

    model_config = ConfigDict(extra="forbid")

    response_type: Literal["content_target_discovery"] = "content_target_discovery"
    contract_version: Literal["content_target_discovery_v1"] = "content_target_discovery_v1"
    work_item_id: str
    public_url: str | None = None
    relation_status: Literal["partial", "unavailable"]
    label: str
    reason: str
    target: ContentTargetDiscoveryTarget | None = None
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
    target_object = next(
        (item for item in profile.dev_content.items if _path(item.link) == _path(public_url)),
        None,
    )
    if target_object is None:
        return ContentTargetDiscovery(
            work_item_id=work_item_id,
            public_url=public_url,
            relation_status="unavailable",
            label="Nie znaleziono odpowiadającej strony na dev",
            reason="WILQ nie znalazł na dev strony o tym samym adresie.",
            evidence_ids=evidence_ids,
            caveats=[
                "Różny adres nie jest dowodem, że target nie istnieje; "
                "relacja wymaga późniejszego potwierdzenia."
            ],
        )
    return ContentTargetDiscovery(
        work_item_id=work_item_id,
        public_url=public_url,
        relation_status="partial",
        label="Znaleziono stronę dev do sprawdzenia",
        reason=(
            "WILQ odczytał konkretną stronę na dev o tym samym adresie, ale sama zgodność "
            "adresu nie potwierdza jeszcze relacji ani prawa do zapisu."
        ),
        target=_target(target_object),
        evidence_ids=evidence_ids,
        caveats=[
            "Szczegóły dotyczą odczytanego obiektu dev, nie mapowania zatwierdzonego dokumentu.",
            "Ten odczyt nie odblokowuje ACF, tworzenia draftu ani publikacji.",
        ],
    )


def _target(item: WordPressAuthoringDevContentObject) -> ContentTargetDiscoveryTarget:
    surfaces = ["acf_flexible_content"] if item.acf_field_name else []
    payload = {
        "object_id": item.post_id,
        "url": item.link,
        "post_type": item.content_type,
        "post_status": item.status,
        "template": item.template or None,
        "observed_surfaces": surfaces,
        "acf_field_name": item.acf_field_name,
        "sections": [
            {"layout_name": section.layout_name, "field_names": section.field_names}
            for section in item.sections
        ],
    }
    return ContentTargetDiscoveryTarget(
        object_id=item.post_id,
        url=item.link,
        post_type=item.content_type,
        post_status=item.status,
        template=item.template or None,
        observed_surfaces=surfaces,
        target_contract_digest=sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
        ).hexdigest(),
    )


def _path(value: str) -> str:
    path = urlparse(value).path.rstrip("/")
    return path or "/"


__all__ = ["ContentTargetDiscovery", "build_content_target_discovery"]
