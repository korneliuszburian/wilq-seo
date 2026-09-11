"""Deterministic pre-judge checks for one immutable content revision.

This gate is deliberately a pure, read-only projection. It composes the
existing quality/claim checks with exact source-fact privacy and a small set of
anti-slop heading checks. Hard blockers stop the model lane; needs-changes
findings remain advisory and preclude approval.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.briefs.sales import ContentSalesBrief
from wilq.content.claims.ledger import ContentClaimLedger, claim_ledger_blockers
from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.inventory.records import ContentInventoryDuplicateRisk
from wilq.content.knowledge.source_facts import (
    ContentSourceFact,
    ekologus_source_facts,
)
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.proposal_quality import HEADING_EXAGGERATION_PATTERN
from wilq.content.quality.review import ContentQualityReview, build_content_quality_review
from wilq.content.workflow.contracts.models import ContentWorkItem
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.documents.revisions import ContentDraftRevision

ContentDeterministicRevisionGateStatus = Literal["passed", "needs_changes", "blocked"]
ContentDeterministicRevisionGateSeverity = Literal["blocker", "needs_changes", "info"]

class ContentDeterministicRevisionGateFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=120)
    severity: ContentDeterministicRevisionGateSeverity
    label: str = Field(min_length=1, max_length=240)
    reason: str = Field(min_length=1, max_length=1200)
    next_step: str = Field(min_length=1, max_length=600)
    affected_target: str | None = Field(default=None, max_length=240)
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)


class ContentDeterministicRevisionGate(BaseModel):
    """Exact-revision result consumed before semantic or judge review."""

    model_config = ConfigDict(extra="forbid")

    contract: Literal["wilq_deterministic_revision_gate_v1"] = (
        "wilq_deterministic_revision_gate_v1"
    )
    status: ContentDeterministicRevisionGateStatus
    work_item_id: str = Field(min_length=1)
    revision_id: str = Field(min_length=1)
    revision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    quality_review_verdict: str = Field(min_length=1)
    quality_finding_codes: list[str] = Field(default_factory=list)
    findings: list[ContentDeterministicRevisionGateFinding] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    byline: str | None = None
    byline_review: Literal["lab_test"] = "lab_test"
    safe_next_step: str = Field(min_length=1, max_length=600)

    @model_validator(mode="after")
    def require_derived_status(self) -> ContentDeterministicRevisionGate:
        failures = [item for item in self.findings if item.severity != "info"]
        blockers = [item for item in failures if item.severity == "blocker"]
        expected: ContentDeterministicRevisionGateStatus = (
            "blocked" if blockers else "needs_changes" if failures else "passed"
        )
        if self.status != expected:
            raise ValueError("Deterministic gate status must be derived from findings.")
        if self.byline is not None and not self.byline.strip():
            raise ValueError("Deterministic gate byline cannot be blank.")
        return self


def build_content_deterministic_revision_gate(
    *,
    item: ContentWorkItem,
    revision: ContentDraftRevision,
    draft_package: ContentDraftPackage | None,
    claim_ledger: ContentClaimLedger | None,
    sales_brief: ContentSalesBrief | None,
    duplicate_risk: ContentInventoryDuplicateRisk,
    planning_input: ContentPlanningInput | None = None,
    planning_proposal: ContentPlanningProposal | None = None,
    source_facts: Iterable[ContentSourceFact] | None = None,
) -> ContentDeterministicRevisionGate:
    findings: list[ContentDeterministicRevisionGateFinding] = []
    if revision.work_item_id != item.id:
        findings.append(
            _finding(
                code="revision_work_item_mismatch",
                severity="blocker",
                label="Rewizja dotyczy innego tematu",
                reason="Deterministyczny gate wymaga zgodności work_item_id rewizji i wejścia.",
                next_step="Otwórz exact workspace i użyj rewizji przypisanej do tego tematu.",
            )
        )

    quality_review = build_content_quality_review(
        item=item,
        draft_package=draft_package,
        structured_output=None,
        revision=revision,
        claim_ledger=claim_ledger,
        sales_brief=sales_brief,
        duplicate_risk=duplicate_risk,
    )
    findings.extend(_quality_findings(quality_review))
    findings.extend(
        _source_lineage_findings(
            revision=revision,
            source_facts=ekologus_source_facts() if source_facts is None else source_facts,
        )
    )
    findings.extend(_heading_findings(revision=revision, claim_ledger=claim_ledger))

    findings.extend(
        _planning_lineage_findings(
            revision=revision,
            planning_input=planning_input,
            planning_proposal=planning_proposal,
        )
    )

    all_evidence_ids = list(
        dict.fromkeys(
            [
                *quality_review.evidence_ids,
                *(
                    evidence_id
                    for finding in findings
                    for evidence_id in finding.evidence_ids
                ),
            ]
        )
    )
    all_connectors = list(
        dict.fromkeys(
            [
                *quality_review.source_connectors,
                *(
                    connector
                    for finding in findings
                    for connector in finding.source_connectors
                ),
            ]
        )
    )
    failures = [finding for finding in findings if finding.severity != "info"]
    blockers = [finding for finding in failures if finding.severity == "blocker"]
    status: ContentDeterministicRevisionGateStatus = (
        "blocked" if blockers else "needs_changes" if failures else "passed"
    )
    return ContentDeterministicRevisionGate(
        status=status,
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revision_digest=revision.content_digest,
        quality_review_verdict=quality_review.verdict,
        quality_finding_codes=list(dict.fromkeys(item.code for item in quality_review.findings)),
        findings=findings,
        evidence_ids=all_evidence_ids,
        source_connectors=all_connectors,
        byline=None if revision.page_assets is None else revision.page_assets.byline,
        safe_next_step=_safe_next_step(status, failures),
    )


def deterministic_gate_for_snapshot(
    *,
    snapshot: object,
    revision: ContentDraftRevision,
    planning_input: ContentPlanningInput,
    planning_proposal: ContentPlanningProposal,
) -> ContentDeterministicRevisionGate | None:
    """Build the gate only for a complete API snapshot, never a test stub."""

    if not all(
        hasattr(snapshot, attribute)
        for attribute in ("preflight", "draft_package", "sales_brief", "claim_ledger")
    ):
        return None
    snapshot_view = cast(Any, snapshot)
    item = snapshot_view.preflight.item
    return build_content_deterministic_revision_gate(
        item=item,
        revision=revision,
        draft_package=snapshot_view.draft_package.draft_package_result.draft_package,
        claim_ledger=snapshot_view.claim_ledger,
        sales_brief=snapshot_view.sales_brief.sales_brief_result.brief,
        duplicate_risk=_duplicate_risk_for_item(item),
        planning_input=planning_input,
        planning_proposal=planning_proposal,
    )


def _quality_findings(
    review: ContentQualityReview,
) -> list[ContentDeterministicRevisionGateFinding]:
    return [
        _finding(
            code=finding.code,
            severity=finding.severity,
            label=finding.label,
            reason=finding.reason,
            next_step=finding.next_step,
            affected_target=finding.affected_section,
            evidence_ids=finding.evidence_ids,
            source_connectors=finding.source_connectors,
        )
        for finding in review.findings
    ]


def _planning_lineage_findings(
    *,
    revision: ContentDraftRevision,
    planning_input: ContentPlanningInput | None,
    planning_proposal: ContentPlanningProposal | None,
) -> list[ContentDeterministicRevisionGateFinding]:
    if planning_input is None or planning_proposal is None:
        return []
    findings: list[ContentDeterministicRevisionGateFinding] = []
    if planning_input.work_item_id != revision.work_item_id:
        findings.append(
            _finding(
                code="planning_work_item_mismatch",
                severity="blocker",
                label="Plan dotyczy innego work itemu",
                reason="Exact revision nie może być oceniana względem obcego planu.",
                next_step="Zbuduj planning input dla bieżącej rewizji.",
            )
        )
    if planning_proposal.planning_input_digest != revision.planning_input_digest:
        findings.append(
            _finding(
                code="planning_input_digest_mismatch",
                severity="blocker",
                label="Plan nie jest związany z rewizją",
                reason="Deterministyczny gate wymaga exact planning_input_digest.",
                next_step="Odśwież plan i zrebasuj rewizję na aktualnym digest.",
            )
        )
    return findings


def _source_lineage_findings(
    *,
    revision: ContentDraftRevision,
    source_facts: Iterable[ContentSourceFact],
) -> list[ContentDeterministicRevisionGateFinding]:
    facts_by_id = {fact.source_id: fact for fact in source_facts}
    if not revision.source_provenance:
        return [
            _finding(
                code="missing_source_provenance",
                severity="blocker",
                label="Brakuje jawnej proweniencji źródeł",
                reason="Exact revision musi wskazywać zatwierdzone source facts i ich evidence.",
                next_step="Dodaj source provenance z zatwierdzonych, rozwiązywalnych źródeł.",
            )
        ]
    findings: list[ContentDeterministicRevisionGateFinding] = []
    for provenance in revision.source_provenance:
        fact = facts_by_id.get(provenance.source_fact_id)
        if fact is None:
            findings.append(
                _finding(
                    code="unknown_source_fact",
                    severity="blocker",
                    label="Rewizja wskazuje nieznany source fact",
                    reason="Source fact nie istnieje w aktualnym, zatwierdzonym katalogu WILQ.",
                    next_step="Użyj source fact z aktualnego katalogu i zachowaj jego evidence.",
                    evidence_ids=provenance.evidence_ids,
                )
            )
            continue
        if fact.review_status != "approved":
            findings.append(
                _finding(
                    code="source_fact_not_approved",
                    severity="blocker",
                    label="Źródło nie ma decyzji approved",
                    reason=(
                        "Do exact revision można podłączyć tylko aktualne, "
                        "zatwierdzone source facts."
                    ),
                    next_step="Zakończ source review albo usuń źródło z rewizji.",
                    evidence_ids=provenance.evidence_ids,
                    source_connectors=fact.source_connectors,
                )
            )
        if fact.privacy_class == "private_local":
            findings.append(
                _finding(
                    code="source_fact_privacy_blocked",
                    severity="blocker",
                    label="Źródło prywatne nie może wejść do rewizji",
                    reason="Prywatny materiał lokalny nie jest bezpieczną lineage do treści.",
                    next_step="Użyj commit_safe albo zatwierdzonego redacted_only projection.",
                    evidence_ids=provenance.evidence_ids,
                    source_connectors=fact.source_connectors,
                )
            )
        if not set(provenance.evidence_ids).issubset(set(fact.evidence_ids)):
            findings.append(
                _finding(
                    code="source_evidence_mismatch",
                    severity="blocker",
                    label="Evidence nie pasuje do source fact",
                    reason="Proweniencja rewizji musi wskazywać evidence należące do tego faktu.",
                    next_step="Zapisz exact evidence_ids z zatwierdzonego source fact.",
                    evidence_ids=provenance.evidence_ids,
                    source_connectors=fact.source_connectors,
                )
            )
        if fact.source_type == "uat_feedback" and fact.privacy_class != "redacted_only":
            findings.append(
                _finding(
                    code="source_consent_not_proven",
                    severity="blocker",
                    label="Feedback nie ma bezpiecznej zgody na reuse",
                    reason=(
                        "UAT feedback może być użyty dopiero jako zatwierdzony "
                        "redacted_only materiał."
                    ),
                    next_step="Zredaguj feedback i zapisz decyzję source review przed reuse.",
                    evidence_ids=provenance.evidence_ids,
                    source_connectors=fact.source_connectors,
                )
            )
    return findings


def _duplicate_risk_for_item(item: object) -> ContentInventoryDuplicateRisk:
    status = getattr(item, "duplicate_status", "missing")
    if status == "checked":
        return "clear"
    if status in {"risk_found", "blocked"}:
        return "high"
    return "unknown"


def _heading_findings(
    *,
    revision: ContentDraftRevision,
    claim_ledger: ContentClaimLedger | None,
) -> list[ContentDeterministicRevisionGateFinding]:
    headings: list[tuple[str, str, frozenset[str]]] = [("title", revision.title, frozenset())]
    if revision.page_assets is not None:
        headings.extend(
            (
                ("page_assets.wordpress_title", revision.page_assets.wordpress_title, frozenset()),
                ("page_assets.meta_title", revision.page_assets.meta_title, frozenset()),
                ("page_assets.h1", revision.page_assets.h1, frozenset()),
            )
        )
    headings.extend(
        (
            f"section:{section.section_id or section.heading}",
            section.heading,
            frozenset(section.claim_ids),
        )
        for section in revision.sections
    )
    headings.extend(
        (f"faq:{faq.faq_id}", faq.question, frozenset(faq.claim_ids))
        for faq in revision.faq
    )
    findings: list[ContentDeterministicRevisionGateFinding] = []
    ledger_entries = () if claim_ledger is None else tuple(claim_ledger.entries)
    blocked_claim_ids = (
        set()
        if claim_ledger is None
        else {item.claim_id for item in claim_ledger_blockers(claim_ledger)}
    )
    for target, heading, claim_ids in headings:
        for match in HEADING_EXAGGERATION_PATTERN.finditer(heading):
            term = match.group(0).casefold()
            supported = any(
                entry.status == "allowed_with_evidence"
                and entry.id in claim_ids
                and entry.id not in blocked_claim_ids
                and entry.evidence_ids
                and term in entry.claim_text.casefold()
                for entry in ledger_entries
            )
            if supported:
                continue
            findings.append(
                _finding(
                    code="unsupported_superlative_heading",
                    severity="blocker",
                    label="Nagłówek zawiera nieudowodnione twierdzenie",
                    reason=(
                        f"Nagłówek „{heading.strip()}” używa sformułowania „{match.group(0)}” "
                        "bez claimu allowed_with_evidence z dowodem."
                    ),
                    next_step=(
                        "Zastąp superlatyw konkretną informacją albo podepnij exact "
                        "claim i evidence."
                    ),
                    affected_target=target,
                )
            )
    return findings


def _finding(
    *,
    code: str,
    severity: ContentDeterministicRevisionGateSeverity,
    label: str,
    reason: str,
    next_step: str,
    affected_target: str | None = None,
    evidence_ids: Iterable[str] = (),
    source_connectors: Iterable[str] = (),
) -> ContentDeterministicRevisionGateFinding:
    return ContentDeterministicRevisionGateFinding(
        code=code,
        severity=severity,
        label=_clip(label, 240),
        reason=_clip(reason, 1200),
        next_step=_clip(next_step, 600),
        affected_target=None if affected_target is None else _clip(affected_target, 240),
        evidence_ids=list(dict.fromkeys(str(item) for item in evidence_ids if str(item).strip())),
        source_connectors=list(
            dict.fromkeys(str(item) for item in source_connectors if str(item).strip())
        ),
    )


def _safe_next_step(
    status: ContentDeterministicRevisionGateStatus,
    failures: list[ContentDeterministicRevisionGateFinding],
) -> str:
    if failures:
        return failures[0].next_step
    if status == "passed":
        return (
            "Uruchom niezależny review dla tej samej exact rewizji; gate nie "
            "zatwierdza publikacji."
        )
    return "Popraw exact rewizję i uruchom gate ponownie."


def _clip(value: str, limit: int) -> str:
    normalized = str(value).strip()
    return normalized if len(normalized) <= limit else normalized[: limit - 1].rstrip() + "…"


__all__ = [
    "ContentDeterministicRevisionGate",
    "ContentDeterministicRevisionGateFinding",
    "ContentDeterministicRevisionGateSeverity",
    "ContentDeterministicRevisionGateStatus",
    "build_content_deterministic_revision_gate",
    "deterministic_gate_for_snapshot",
]
