from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from wilq.content.canonical.landing_identity import (
    LandingPageCandidate,
    landing_page_metric_lookup_path,
    landing_page_metric_lookup_urls,
    match_landing_page,
)
from wilq.content.canonical.urls import (
    CONTENT_SOURCE_SITE_HOSTS,
    content_is_safe_public_url,
    content_normalized_url,
    content_url_host,
)
from wilq.storage.metric_store import DuckDbMetricStore, metric_store


class ContentPlanningInternalLinkCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_url: str = Field(min_length=1)
    anchor_hint: str = Field(min_length=1)
    source_connector: Literal["wordpress_ekologus"] = "wordpress_ekologus"
    evidence_ids: list[str] = Field(min_length=1)

    @field_validator("target_url")
    @classmethod
    def require_safe_public_target(cls, value: str) -> str:
        if not content_is_safe_public_url(value):
            raise ValueError("Internal-link candidate requires a safe public Ekologus URL.")
        return value


def load_content_internal_link_candidates(
    directions: Iterable[str],
    *,
    allowed_evidence_ids: Iterable[str],
    store: DuckDbMetricStore | None = None,
) -> list[ContentPlanningInternalLinkCandidate]:
    allowed_evidence = set(allowed_evidence_ids)
    if not allowed_evidence:
        return []
    source = store or metric_store()
    if not source.path.exists():
        return []
    candidates: list[ContentPlanningInternalLinkCandidate] = []
    for direction in dict.fromkeys(directions):
        if (
            content_url_host(direction) not in CONTENT_SOURCE_SITE_HOSTS
            or not content_is_safe_public_url(direction)
        ):
            continue
        candidate = _candidate_for_direction(
            direction,
            allowed_evidence_ids=allowed_evidence,
            store=source,
        )
        if candidate is not None and candidate.target_url not in {
            item.target_url for item in candidates
        }:
            candidates.append(candidate)
    return candidates


def _candidate_for_direction(
    direction: str,
    *,
    allowed_evidence_ids: set[str],
    store: DuckDbMetricStore,
) -> ContentPlanningInternalLinkCandidate | None:
    facts = [
        fact
        for lookup_url in landing_page_metric_lookup_urls(direction)
        for fact in store.list_metric_facts_for_content_url(
            ["wordpress_ekologus"],
            lookup_url,
            content_path=landing_page_metric_lookup_path(direction),
        )
    ]
    for fact in facts:
        target_url = fact.dimensions.get("canonical_url") or fact.dimensions.get(
            "content_url"
        )
        match = match_landing_page(
            direction,
            LandingPageCandidate(candidate_id=fact.evidence_id, url=target_url),
        )
        if (
            fact.name != "content_object_seen"
            or fact.evidence_id not in allowed_evidence_ids
            or fact.dimensions.get("status") not in {"published", "indexed"}
            or not match.matched
            or match.tier not in {"exact", "host_alias"}
            or content_url_host(target_url) not in CONTENT_SOURCE_SITE_HOSTS
            or not content_is_safe_public_url(target_url)
        ):
            continue
        normalized_target = content_normalized_url(target_url)
        if not normalized_target:
            continue
        return ContentPlanningInternalLinkCandidate(
            target_url=normalized_target,
            anchor_hint=fact.dimensions.get("title_or_h1") or normalized_target,
            source_connector="wordpress_ekologus",
            evidence_ids=[fact.evidence_id],
        )
    return None


__all__ = [
    "ContentPlanningInternalLinkCandidate",
    "load_content_internal_link_candidates",
]
