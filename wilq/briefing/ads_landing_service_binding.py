from __future__ import annotations

import hashlib
from functools import lru_cache
from typing import Literal

from wilq.content.canonical.landing_identity import build_landing_page_identity
from wilq.content.knowledge.work_item_service_profile import (
    build_content_work_item_service_profile_context,
)
from wilq.content.workflow.catalog import build_content_inventory_catalog
from wilq.content.workflow.models import ContentWorkItem
from wilq.schemas import AdsLandingServiceBinding


@lru_cache(maxsize=256)
def resolve_ads_landing_service_binding(
    landing_identity_sha256: str | None,
) -> AdsLandingServiceBinding | None:
    """Resolve a private Ads landing hash through inventory and Service Profile.

    The returned contract intentionally contains no landing URL. A page match is
    not an approved service match: lifecycle and typed review status remain
    visible so Ads cannot silently feed a content plan.
    """
    if not landing_identity_sha256:
        return None
    catalog = build_content_inventory_catalog()
    matches = [
        item
        for item in catalog.items
        if _url_identity_hash(item.url) == landing_identity_sha256
    ]
    if not matches:
        return AdsLandingServiceBinding(
            status="unbound",
            reason="Landing Ads nie ma exact odpowiednika w aktualnym inventory WordPress.",
            next_step="Nie przypisuj termu do usługi; sprawdź landing w WILQ i odśwież inventory.",
        )
    if len(matches) > 1:
        return AdsLandingServiceBinding(
            status="ambiguous",
            reason="Hash landingu pasuje do więcej niż jednego wpisu inventory WordPress.",
            next_step="Rozstrzygnij kanoniczny adres w inventory przed użyciem Ads w planie.",
        )

    item = matches[0]
    work_item = ContentWorkItem(
        id=item.work_item_id,
        topic=item.title or item.path,
        source_public_url=item.url,
        final_canonical_url=item.url,
        intended_final_url=item.url,
        wordpress_title_or_h1=item.title,
        wordpress_section_count=item.section_count,
        wordpress_section_inventory_status=(
            "available" if item.section_count is not None else "missing"
        ),
        wordpress_content_summary=item.content_summary,
        wordpress_content_word_count=item.content_word_count,
        wordpress_content_inventory_status=(
            "available" if item.content_summary else "missing"
        ),
        wordpress_acf_section_count=item.acf_section_count,
        wordpress_acf_section_inventory_status=(
            "available" if item.acf_section_count is not None else "missing"
        ),
        evidence_ids=[item.evidence_id],
        source_connectors=[item.source_connector],
    )
    context = build_content_work_item_service_profile_context(work_item)
    candidates = context.service_candidates
    lifecycle_statuses: list[str] = [candidate.lifecycle_status for candidate in candidates]
    status: Literal["review_required", "approved_current"] = (
        "approved_current"
        if context.service_status == "approved_current"
        else "review_required"
    )
    return AdsLandingServiceBinding(
        status=status,
        inventory_work_item_id=item.work_item_id,
        service_candidate_ids=[candidate.service_card_id for candidate in candidates],
        service_candidate_labels=[candidate.service_label for candidate in candidates],
        service_lifecycle_statuses=lifecycle_statuses,
        reason=context.reason,
        next_step=context.safe_next_step,
    )


def _url_identity_hash(url: str) -> str | None:
    identity = build_landing_page_identity(url)
    if identity.status != "resolved" or not identity.canonical_url:
        return None
    return hashlib.sha256(identity.canonical_url.encode("utf-8")).hexdigest()
