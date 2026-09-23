"""Exact read-only source-pack projection from current v2 reviewed authority."""

from __future__ import annotations

from contextlib import suppress
from datetime import UTC, date, datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.knowledge.cards import ContentKnowledgeCard, ekologus_content_knowledge_cards
from wilq.content.knowledge.source_facts import ContentSourceFact, ekologus_source_facts
from wilq.content.workflow.current_page_identity_v2 import (
    CurrentPageIdentityBlockerOwner,
    CurrentPageIdentityV2Response,
)
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.source_fact_authority_v2 import (
    ContentSourceFactAuthorityV2PreviewCommand,
    ContentSourceFactAuthorityV2Receipt,
    SourceFactAuthorityV2Blocked,
    prepare_source_fact_authority_v2,
)
from wilq.content.workflow.source_fact_candidate_projection import (
    ContentSourceFactAuthorityServiceBinding,
)
from wilq.content.workflow.source_fact_candidate_v2 import ContentSourceFactCandidateV2
from wilq.content.workflow.source_pack_binding import source_fact_registry_digest
from wilq.security.redaction import redact_mapping

_OWNER: CurrentPageIdentityBlockerOwner = "WILQ content workflow"


class SourcePackV2Fact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_fact_id: str = Field(min_length=1)
    fact_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    text: str = Field(min_length=1)
    source_reference: str = Field(min_length=1)
    freshness_date: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    source_connectors: tuple[str, ...] = Field(min_length=1)
    evidence_ids: tuple[str, ...] = Field(min_length=1)


class SourcePackV2Blocker(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(min_length=1)
    owner: CurrentPageIdentityBlockerOwner
    evidence_ids: tuple[str, ...] = ()
    safe_next_step: str = Field(min_length=1)


class SourcePackV2Preview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["ready", "blocked"]
    work_item_id: str
    source_pack_id: str | None = None
    source_pack_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    page_url: str | None = None
    canonical_path: str | None = None
    keep_receipt_id: str | None = None
    keep_receipt_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    material_meaning_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    authority_receipt_id: str | None = None
    authority_receipt_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    authority_snapshot_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    service_binding: ContentSourceFactAuthorityServiceBinding | None = None
    facts: tuple[SourcePackV2Fact, ...] = ()
    verification_evidence_ids: tuple[str, ...] = ()
    verification_registry_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    blocker: SourcePackV2Blocker | None = None
    generation_allowed: Literal[False] = False
    source_pack_write_allowed: Literal[False] = False

    @model_validator(mode="after")
    def validate_packet_state(self) -> Self:
        if self.status == "blocked":
            if self.blocker is None or self.source_pack_id or self.source_pack_hash or self.facts:
                raise ValueError("Blocked source pack cannot expose an artifact.")
            return self
        if (
            self.blocker is not None
            or not self.facts
            or self.page_url is None
            or self.canonical_path is None
            or self.keep_receipt_id is None
            or self.keep_receipt_digest is None
            or self.material_meaning_digest is None
            or self.authority_receipt_id is None
            or self.authority_receipt_digest is None
            or self.authority_snapshot_digest is None
            or self.service_binding is None
            or self.verification_registry_digest is None
        ):
            raise ValueError("Ready source pack requires complete exact lineage and facts.")
        digest = canonical_json_digest(self.semantic_payload())
        if self.source_pack_hash != digest or self.source_pack_id != f"source_pack_v2_{digest}":
            raise ValueError("Source pack identity does not match its exact artifact.")
        return self

    def semantic_payload(self) -> dict[str, object]:
        if (
            self.page_url is None
            or self.canonical_path is None
            or self.keep_receipt_id is None
            or self.keep_receipt_digest is None
            or self.material_meaning_digest is None
            or self.authority_receipt_id is None
            or self.authority_receipt_digest is None
            or self.authority_snapshot_digest is None
            or self.service_binding is None
        ):
            raise ValueError("Source pack semantic payload requires exact lineage.")
        return _semantic_pack_fields(
            work_item_id=self.work_item_id,
            page_url=self.page_url,
            canonical_path=self.canonical_path,
            keep_receipt_id=self.keep_receipt_id,
            keep_receipt_digest=self.keep_receipt_digest,
            material_meaning_digest=self.material_meaning_digest,
            authority_receipt_id=self.authority_receipt_id,
            authority_receipt_digest=self.authority_receipt_digest,
            authority_snapshot_digest=self.authority_snapshot_digest,
            service_binding=self.service_binding,
            facts=self.facts,
        )


def build_source_pack_v2_preview(
    work_item_id: str,
    *,
    identity: CurrentPageIdentityV2Response,
    authority_receipts: tuple[ContentSourceFactAuthorityV2Receipt, ...],
    facts: tuple[ContentSourceFact, ...] | None = None,
    cards: tuple[ContentKnowledgeCard, ...] | None = None,
) -> SourcePackV2Preview:
    evidence_ids = tuple(sorted(set(identity.current_evidence_ids)))
    if identity.status != "exact_current":
        return _blocked(
            work_item_id,
            identity.blocker_code or "current_keep_blocked",
            identity.blocker_owner or _OWNER,
            evidence_ids,
            identity.safe_next_step or "Odczytaj bieżący KEEP.",
        )
    if not authority_receipts:
        return _blocked(
            work_item_id,
            "source_fact_authority_receipt_missing",
            _OWNER,
            evidence_ids,
            "Przeprowadź exact human review źródeł dla bieżącego KEEP.",
        )
    authority = authority_receipts[-1]
    registry_facts = facts if facts is not None else tuple(ekologus_source_facts())
    registry_cards = cards if cards is not None else tuple(ekologus_content_knowledge_cards())
    authority_blocker = _current_authority_blocker(
        work_item_id,
        identity=identity,
        authority=authority,
        facts=registry_facts,
        cards=registry_cards,
        evidence_ids=evidence_ids,
    )
    if authority_blocker is not None:
        return authority_blocker
    by_id = {fact.source_id: fact for fact in registry_facts}
    packet_facts: list[SourcePackV2Fact] = []
    for selected in authority.snapshot.selected_facts:
        candidate = _packet_fact(selected, by_id.get(selected.source_fact_id))
        if isinstance(candidate, SourcePackV2Blocker):
            return SourcePackV2Preview(
                status="blocked", work_item_id=work_item_id, blocker=candidate
            )
        currency_blocker = _source_currency_blocker(
            selected, authority.snapshot.service_binding, registry_cards
        )
        if currency_blocker is not None:
            return SourcePackV2Preview(
                status="blocked", work_item_id=work_item_id, blocker=currency_blocker
            )
        packet_facts.append(candidate)
    return _ready_preview(
        work_item_id,
        identity,
        authority,
        tuple(packet_facts),
        source_fact_registry_digest(registry_facts),
    )


def _fact_digest(fact: ContentSourceFact) -> str:
    return canonical_json_digest(fact.model_dump(mode="json"))


def _current_authority_blocker(
    work_item_id: str,
    *,
    identity: CurrentPageIdentityV2Response,
    authority: ContentSourceFactAuthorityV2Receipt,
    facts: tuple[ContentSourceFact, ...],
    cards: tuple[ContentKnowledgeCard, ...],
    evidence_ids: tuple[str, ...],
) -> SourcePackV2Preview | None:
    snapshot = authority.snapshot
    if (
        snapshot.work_item_id != work_item_id
        or snapshot.keep_receipt_id != identity.receipt_id
        or snapshot.keep_receipt_digest != identity.receipt_digest
        or snapshot.material_meaning_digest != identity.material_meaning_digest
        or snapshot.page_url != identity.page_url
        or snapshot.canonical_path != identity.canonical_path
    ):
        return _blocked(
            work_item_id,
            "source_fact_authority_keep_or_material_changed",
            _OWNER,
            evidence_ids,
            "Odczytaj i zatwierdź źródła ponownie dla bieżącego KEEP i materiału.",
        )
    try:
        current = prepare_source_fact_authority_v2(
            ContentSourceFactAuthorityV2PreviewCommand(
                work_item_id=work_item_id,
                expected_keep_receipt_id=identity.receipt_id or "",
                expected_keep_receipt_digest=identity.receipt_digest or "0" * 64,
                expected_material_meaning_digest=identity.material_meaning_digest or "0" * 64,
                source_fact_ids=tuple(f.source_fact_id for f in snapshot.selected_facts),
            ),
            identity=identity,
            facts=facts,
            cards=cards,
        )
    except SourceFactAuthorityV2Blocked as error:
        return _blocked(
            work_item_id, error.code, error.owner, error.evidence_ids, error.safe_next_step
        )
    except (ValueError, TypeError):
        return _blocked(
            work_item_id,
            "source_fact_authority_revalidation_failed",
            _OWNER,
            evidence_ids,
            "Odczytaj aktualne source-fact candidates i authority dla bieżącego KEEP.",
        )
    if (
        current.snapshot.selected_facts != snapshot.selected_facts
        or current.snapshot.service_binding != snapshot.service_binding
    ):
        selected_ids = tuple(e for fact in snapshot.selected_facts for e in fact.evidence_ids)
        return _blocked(
            work_item_id,
            "source_fact_authority_selection_changed",
            _OWNER,
            tuple(sorted(set(evidence_ids + selected_ids))),
            "Przeprowadź ponowny review dokładnego wyboru źródeł.",
        )
    return None


def _packet_fact(
    selected: ContentSourceFactCandidateV2,
    source: ContentSourceFact | None,
) -> SourcePackV2Fact | SourcePackV2Blocker:
    if (
        source is None
        or _fact_digest(source) != selected.fact_digest
        or source.review_status != "approved"
    ):
        return SourcePackV2Blocker(
            code="selected_source_fact_changed_or_not_approved",
            owner=_OWNER,
            evidence_ids=selected.evidence_ids,
            safe_next_step="Odczytaj ponownie zatwierdzony exact source fact dla tego packetu.",
        )
    if source.privacy_class != "commit_safe":
        return SourcePackV2Blocker(
            code="selected_source_fact_not_commit_safe",
            owner=_OWNER,
            evidence_ids=selected.evidence_ids,
            safe_next_step="Przygotuj zatwierdzoną zredagowaną kartę wiedzy przed packetem.",
        )
    safe = redact_mapping({"text": source.extracted_fact, "source_url": source.source_url_or_path})
    if (
        safe.get("text") != source.extracted_fact
        or safe.get("source_url") != source.source_url_or_path
    ):
        return SourcePackV2Blocker(
            code="selected_source_fact_redaction_required",
            owner=_OWNER,
            evidence_ids=selected.evidence_ids,
            safe_next_step="Zatwierdź bezpieczny publiczny tekst i adres źródła przed packetem.",
        )
    return SourcePackV2Fact(
        source_fact_id=source.source_id,
        fact_digest=selected.fact_digest,
        text=source.extracted_fact,
        source_reference=source.source_url_or_path,
        freshness_date=source.freshness_date,
        source_type=source.source_type,
        source_connectors=tuple(sorted(set(source.source_connectors))),
        evidence_ids=tuple(sorted(set(source.evidence_ids))),
    )


def _source_currency_blocker(
    selected: ContentSourceFactCandidateV2,
    binding: ContentSourceFactAuthorityServiceBinding,
    cards: tuple[ContentKnowledgeCard, ...],
) -> SourcePackV2Blocker | None:
    if selected.source_type == "legal_update":
        # The authority revalidation above applies the exact regulatory profile age rule.
        return None
    if selected.source_type == "official_guidance":
        return SourcePackV2Blocker(
            code="official_guidance_currency_policy_missing",
            owner=_OWNER,
            evidence_ids=selected.evidence_ids,
            safe_next_step=(
                "Zarejestruj dokładne oficjalne źródło do review aktualności dla tego URL-a."
            ),
        )
    card = next((item for item in cards if item.id == binding.card_id), None)
    evidence_ids = tuple(sorted(set(selected.evidence_ids + binding.card_evidence_ids)))
    fact_date: date | None = None
    card_date: date | None = None
    with suppress(ValueError):
        fact_date = date.fromisoformat(selected.freshness_date)
    if card is not None and card.freshness.startswith("reviewed_"):
        reviewed_date = card.freshness.removeprefix("reviewed_")
        if len(reviewed_date) == 10:
            with suppress(ValueError):
                card_date = date.fromisoformat(reviewed_date)
    if (
        card is None
        or card.lifecycle_status != "approved_current"
        or selected.source_fact_id not in card.source_fact_ids
        or card.freshness != binding.card_freshness
        or fact_date is None
        or card_date is None
        or card_date > datetime.now(UTC).date()
    ):
        return SourcePackV2Blocker(
            code="source_currency_policy_missing",
            owner=_OWNER,
            evidence_ids=evidence_ids,
            safe_next_step="Przygotuj review aktualności faktu w dokładnej karcie usługi.",
        )
    if fact_date < card_date:
        return SourcePackV2Blocker(
            code="source_fact_older_than_current_service_card",
            owner=_OWNER,
            evidence_ids=evidence_ids,
            safe_next_step="Przygotuj odświeżony fakt do review bieżącej karty usługi.",
        )
    return SourcePackV2Blocker(
        code="source_currency_policy_missing",
        owner=_OWNER,
        evidence_ids=evidence_ids,
        safe_next_step="Zarejestruj zatwierdzony termin ważności tego źródła.",
    )


def _semantic_pack_fields(
    *,
    work_item_id: str,
    page_url: str,
    canonical_path: str,
    keep_receipt_id: str,
    keep_receipt_digest: str,
    material_meaning_digest: str,
    authority_receipt_id: str,
    authority_receipt_digest: str,
    authority_snapshot_digest: str,
    service_binding: ContentSourceFactAuthorityServiceBinding,
    facts: tuple[SourcePackV2Fact, ...],
) -> dict[str, object]:
    return {
        "contract": "wilq_source_pack_v2",
        "work_item_id": work_item_id,
        "keep": {
            "receipt_id": keep_receipt_id,
            "receipt_digest": keep_receipt_digest,
            "material_meaning_digest": material_meaning_digest,
            "page_url": page_url,
            "canonical_path": canonical_path,
        },
        "authority": {
            "receipt_id": authority_receipt_id,
            "receipt_digest": authority_receipt_digest,
            "snapshot_digest": authority_snapshot_digest,
        },
        "service_binding": service_binding.model_dump(mode="json"),
        "facts": [fact.model_dump(mode="json") for fact in facts],
    }


def _ready_preview(
    work_item_id: str,
    identity: CurrentPageIdentityV2Response,
    authority: ContentSourceFactAuthorityV2Receipt,
    packet_facts: tuple[SourcePackV2Fact, ...],
    registry_digest: str,
) -> SourcePackV2Preview:
    snapshot = authority.snapshot
    current_ids = tuple(sorted(set(identity.current_evidence_ids)))
    if (
        identity.page_url is None
        or identity.canonical_path is None
        or identity.receipt_id is None
        or identity.receipt_digest is None
        or identity.material_meaning_digest is None
    ):
        raise ValueError("Ready source pack requires exact current KEEP identity.")
    fields = {
        "status": "ready",
        "work_item_id": work_item_id,
        "source_pack_id": "pending",
        "source_pack_hash": "0" * 64,
        "page_url": identity.page_url,
        "canonical_path": identity.canonical_path,
        "keep_receipt_id": identity.receipt_id,
        "keep_receipt_digest": identity.receipt_digest,
        "material_meaning_digest": identity.material_meaning_digest,
        "authority_receipt_id": authority.receipt_id,
        "authority_receipt_digest": authority.receipt_digest,
        "authority_snapshot_digest": snapshot.context_digest,
        "service_binding": snapshot.service_binding,
        "facts": packet_facts,
        "verification_evidence_ids": tuple(
            sorted(set(current_ids + authority.verification_evidence_ids))
        ),
        "verification_registry_digest": registry_digest,
    }
    digest = canonical_json_digest(
        _semantic_pack_fields(
            work_item_id=work_item_id,
            page_url=identity.page_url,
            canonical_path=identity.canonical_path,
            keep_receipt_id=identity.receipt_id,
            keep_receipt_digest=identity.receipt_digest,
            material_meaning_digest=identity.material_meaning_digest,
            authority_receipt_id=authority.receipt_id,
            authority_receipt_digest=authority.receipt_digest,
            authority_snapshot_digest=snapshot.context_digest,
            service_binding=snapshot.service_binding,
            facts=packet_facts,
        )
    )
    return SourcePackV2Preview.model_validate(
        fields | {"source_pack_id": f"source_pack_v2_{digest}", "source_pack_hash": digest}
    )


def _blocked(
    work_item_id: str,
    code: str,
    owner: CurrentPageIdentityBlockerOwner,
    evidence_ids: tuple[str, ...],
    next_step: str,
) -> SourcePackV2Preview:
    return SourcePackV2Preview(
        status="blocked",
        work_item_id=work_item_id,
        blocker=SourcePackV2Blocker(
            code=code,
            owner=owner,
            evidence_ids=tuple(sorted(set(evidence_ids))),
            safe_next_step=next_step,
        ),
    )


__all__ = ["SourcePackV2Preview", "build_source_pack_v2_preview"]
