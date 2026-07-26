from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256

from pydantic import BaseModel, ConfigDict, Field

from wilq.content.canonical.landing_identity import LandingPageCandidate, match_landing_page
from wilq.content.workflow.revisions import ContentDraftRevision
from wilq.schemas import MetricFact


class ContentPublicDeployment(BaseModel):
    """A human-confirmed, connector-observed public deployment of one revision.

    This is deliberately not a WordPress delivery record. It only records that
    WILQ observed a published public object and that an operator associated the
    observation with one exact approved revision.
    """

    model_config = ConfigDict(extra="forbid")

    deployment_id: str = Field(min_length=1)
    work_item_id: str = Field(min_length=1)
    revision_id: str = Field(min_length=1)
    revision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    public_url: str = Field(min_length=1)
    wordpress_post_id: str = Field(min_length=1)
    publication_evidence_id: str = Field(min_length=1)
    publication_source_connector: str = Field(min_length=1)
    observed_at: datetime
    confirmed_by: str = Field(min_length=1, max_length=200)
    confirmed_at: datetime


class ContentPublicDeploymentConfirmationCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    wordpress_post_id: str = Field(min_length=1)
    publication_evidence_id: str = Field(min_length=1)
    confirmed_by: str = Field(min_length=1, max_length=200)


def confirm_public_deployment(
    *,
    revision: ContentDraftRevision,
    command: ContentPublicDeploymentConfirmationCommand,
    publication_facts: list[MetricFact],
    now: datetime,
) -> ContentPublicDeployment:
    """Create a record only from an exact public WordPress observation."""

    if command.expected_revision_digest != revision.content_digest:
        raise ValueError("Potwierdzenie wskazuje inną wersję dokumentu.")
    fact = _publication_fact(
        revision=revision,
        wordpress_post_id=command.wordpress_post_id,
        publication_evidence_id=command.publication_evidence_id,
        facts=publication_facts,
    )
    if fact is None:
        raise ValueError(
            "Nie znaleziono potwierdzonego odczytu opublikowanego obiektu WordPress "
            "dla tej rewizji i publicznego adresu."
        )
    observed_at = _required_collected_at(fact)
    confirmed_at = now.replace(tzinfo=UTC) if now.tzinfo is None else now
    return ContentPublicDeployment(
        deployment_id=_deployment_id(
            work_item_id=revision.work_item_id,
            revision_id=revision.revision_id,
            evidence_id=fact.evidence_id,
        ),
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revision_digest=revision.content_digest,
        public_url=revision.final_canonical_url,
        wordpress_post_id=command.wordpress_post_id,
        publication_evidence_id=fact.evidence_id,
        publication_source_connector=fact.source_connector,
        observed_at=observed_at,
        confirmed_by=command.confirmed_by,
        confirmed_at=confirmed_at,
    )


def _publication_fact(
    *,
    revision: ContentDraftRevision,
    wordpress_post_id: str,
    publication_evidence_id: str,
    facts: list[MetricFact],
) -> MetricFact | None:
    for fact in facts:
        if (
            fact.evidence_id == publication_evidence_id
            and fact.source_connector == "wordpress_ekologus"
            and fact.name == "content_object_seen"
            and fact.dimensions.get("object_id") == wordpress_post_id
            and fact.dimensions.get("status") == "publish"
            and fact.collected_at is not None
            and match_landing_page(
                revision.final_canonical_url,
                LandingPageCandidate(
                    candidate_id="wordpress_publication_observation",
                    url=str(fact.dimensions.get("content_url", "")),
                ),
            ).matched
        ):
            return fact
    return None


def _required_collected_at(fact: MetricFact) -> datetime:
    if fact.collected_at is None:
        raise ValueError("Odczyt publikacji nie ma czasu obserwacji.")
    return (
        fact.collected_at.replace(tzinfo=UTC)
        if fact.collected_at.tzinfo is None
        else fact.collected_at
    )


def _deployment_id(*, work_item_id: str, revision_id: str, evidence_id: str) -> str:
    identity = f"{work_item_id}:{revision_id}:{evidence_id}".encode()
    return f"content_public_deployment_{sha256(identity).hexdigest()[:24]}"
