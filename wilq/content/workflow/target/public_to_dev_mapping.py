from __future__ import annotations

from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.connectors.wordpress.authoring import WordPressAuthoringDevContentProfile
from wilq.content.workflow.contracts.models import ContentDecisionTargetMappingStatus

ContentPublicToDevMappingBasis = Literal[
    "exact_dev_url_match",
    "confirmed_inventory_relation",
    "observed_only",
    "not_observed",
]
ContentPublicToDevMappingEvidenceBasis = Literal[
    "exact_dev_url_match",
    "confirmed_inventory_relation",
]


class ContentPublicToDevMappingEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    public_url: str = Field(min_length=1)
    dev_url: str = Field(min_length=1)
    dev_post_id: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    basis: ContentPublicToDevMappingEvidenceBasis

    @model_validator(mode="after")
    def require_named_evidence(self) -> ContentPublicToDevMappingEvidence:
        if any(not evidence_id.strip() for evidence_id in self.evidence_ids):
            raise ValueError("Public-to-dev relation evidence IDs cannot be blank.")
        return self


class ContentPublicToDevMapping(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mapping_status: ContentDecisionTargetMappingStatus
    public_url: str
    dev_url: str | None = None
    dev_post_id: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    basis: ContentPublicToDevMappingBasis
    blocker: str | None = None
    reason: str = Field(min_length=1)
    next_step: str | None = None

    @model_validator(mode="after")
    def require_evidence_bound_exact_mapping(self) -> ContentPublicToDevMapping:
        if self.mapping_status == "exact":
            if self.dev_url is None or self.dev_post_id is None or not self.evidence_ids:
                raise ValueError("Exact public-to-dev mapping requires a target and evidence.")
            if self.basis not in {"exact_dev_url_match", "confirmed_inventory_relation"}:
                raise ValueError("Exact public-to-dev mapping requires an evidence basis.")
            if self.blocker is not None or self.next_step is not None:
                raise ValueError("Exact public-to-dev mapping cannot expose a blocker.")
        elif self.evidence_ids:
            raise ValueError("Non-exact public-to-dev mapping cannot expose relation evidence.")
        elif self.blocker is None or self.next_step is None:
            raise ValueError("Non-exact public-to-dev mapping requires a blocker and next step.")
        elif self.mapping_status == "unverified" and self.basis != "observed_only":
            raise ValueError("Unverified public-to-dev mapping requires an observed basis.")
        elif self.mapping_status == "missing" and (
            self.basis != "not_observed" or self.dev_url is not None or self.dev_post_id is not None
        ):
            raise ValueError("Missing public-to-dev mapping cannot expose a target.")
        return self


def build_content_public_to_dev_mapping(
    public_url: str,
    *,
    dev_content: WordPressAuthoringDevContentProfile,
    relation_evidence: ContentPublicToDevMappingEvidence | None = None,
) -> ContentPublicToDevMapping:
    observed_items = dev_content.items if dev_content.status == "available" else []
    if not public_url.strip():
        return ContentPublicToDevMapping(
            mapping_status="missing",
            public_url=public_url,
            basis="not_observed",
            blocker="public_url_missing",
            reason="Brakuje publicznego adresu strony do zbudowania relacji z dev.",
            next_step="Wskaż dokładny publiczny adres pilota przed mapowaniem targetu dev.",
        )
    if relation_evidence is not None and relation_evidence.public_url == public_url:
        target = next(
            (
                item
                for item in observed_items
                if item.link == relation_evidence.dev_url
                and item.post_id == relation_evidence.dev_post_id
            ),
            None,
        )
        if target is not None:
            return ContentPublicToDevMapping(
                mapping_status="exact",
                public_url=public_url,
                dev_url=target.link,
                dev_post_id=target.post_id,
                evidence_ids=list(dict.fromkeys(relation_evidence.evidence_ids)),
                basis=relation_evidence.basis,
                reason=("Dowód relacji wiąże dokładny publiczny adres z odczytanym obiektem dev."),
            )
    observed_candidates = [
        item
        for item in observed_items
        if (urlparse(item.link).path or "/") == (urlparse(public_url).path or "/")
    ]
    if len(observed_candidates) == 1:
        candidate = observed_candidates[0]
        return ContentPublicToDevMapping(
            mapping_status="unverified",
            public_url=public_url,
            dev_url=candidate.link,
            dev_post_id=candidate.post_id,
            basis="observed_only",
            blocker="public_to_dev_relation_unverified",
            reason=(
                "Profil WordPress pokazuje obiekt dev o tej samej ścieżce, ale nie "
                "dowodzi relacji z tą publiczną stroną."
            ),
            next_step=(
                "OWNER powinien potwierdzić dokładny publiczny adres, adres dev i post ID "
                "dla tego pilota."
            ),
        )
    if len(observed_candidates) > 1:
        return ContentPublicToDevMapping(
            mapping_status="unverified",
            public_url=public_url,
            basis="observed_only",
            blocker="public_to_dev_candidates_ambiguous",
            reason="Profil WordPress pokazuje kilka kandydatów dev o tej samej ścieżce.",
            next_step="OWNER powinien wskazać dokładny obiekt dev dla tej publicznej strony.",
        )
    return ContentPublicToDevMapping(
        mapping_status="missing",
        public_url=public_url,
        basis="not_observed",
        blocker="public_to_dev_mapping_missing",
        reason="Brakuje potwierdzonej relacji publicznej strony z obiektem dev.",
        next_step="Potwierdź dokładny adres i identyfikator obiektu dev dla tej strony.",
    )


__all__ = [
    "ContentPublicToDevMapping",
    "ContentPublicToDevMappingEvidence",
    "build_content_public_to_dev_mapping",
]
