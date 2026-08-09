from __future__ import annotations

from typing import Literal, NamedTuple

from pydantic import BaseModel, ConfigDict, Field

from wilq.content.briefs.sales import ContentSalesBrief
from wilq.content.claims.ledger import ContentClaimLedger
from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.drafts.structured_generation import StructuredDraftOutput
from wilq.content.inventory.records import ContentInventoryDuplicateRisk
from wilq.content.quality import review_evidence, review_findings
from wilq.content.quality.reading_quality import revision_readability_issues, weak_cta
from wilq.content.workflow.contracts.models import ContentWorkItem
from wilq.content.workflow.documents.revisions import ContentDraftRevision

ContentQualityVerdict = Literal[
    "blocked",
    "needs_changes",
    "reviewable",
    "ready_for_human_review",
]
ContentQualitySeverity = Literal["blocker", "needs_changes", "info"]
ContentQualityDimensionStatus = Literal["pass", "needs_changes", "blocked"]
ContentQualityFindingCode = Literal[
    "missing_draft_package",
    "draft_package_mismatch",
    "draft_package_marked_publish_ready",
    "missing_structured_output",
    "section_missing_evidence",
    "unknown_evidence_reference",
    "missing_claim_ledger",
    "claim_ledger_blocks_quality",
    "unsupported_claim_used",
    "forbidden_claim_used",
    "claim_missing_required_evidence",
    "required_claim_missing",
    "missing_forbidden_claim_acknowledgement",
    "duplicate_risk_not_clear",
    "missing_measurement_window",
    "measurement_window_pending_publication",
    "sales_brief_signal_review_required",
    "sales_brief_signal_thin",
    "thin_section",
    "wall_of_text",
    "weak_cta",
    "missing_service_fit",
    "missing_search_intent",
    "missing_buyer_problem",
    "missing_internal_links",
    "non_polish_language",
]


class ContentQualityDimension(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ContentQualityDimensionStatus
    label: str
    reason: str


class ContentQualityFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ContentQualityFindingCode
    severity: ContentQualitySeverity
    label: str
    reason: str
    next_step: str
    affected_section: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)


class ContentRevisionInstruction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    affected_section: str | None = None
    change: str
    reason: str
    required_evidence_ids: list[str] = Field(default_factory=list)
    forbidden_claims_to_avoid: list[str] = Field(default_factory=list)
    human_review_checklist_additions: list[str] = Field(default_factory=list)


class ContentQualityReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_id: str
    work_item_id: str
    draft_package_id: str | None = None
    revision_digest: str | None = None
    verdict: ContentQualityVerdict
    evidence_coverage: ContentQualityDimension
    claim_safety: ContentQualityDimension
    duplicate_risk: ContentQualityDimension
    usefulness: ContentQualityDimension
    service_fit: ContentQualityDimension
    search_intent_fit: ContentQualityDimension
    buyer_problem_fit: ContentQualityDimension
    cta_quality: ContentQualityDimension
    factual_precision: ContentQualityDimension
    polish_language_quality: ContentQualityDimension
    internal_link_fit: ContentQualityDimension
    measurement_readiness: ContentQualityDimension
    blockers: list[ContentQualityFinding] = Field(default_factory=list)
    findings: list[ContentQualityFinding] = Field(default_factory=list)
    revision_instructions: list[ContentRevisionInstruction] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    safe_next_step: str


class _ContentQualityDimensions(NamedTuple):
    evidence_coverage: ContentQualityDimension
    claim_safety: ContentQualityDimension
    duplicate_risk: ContentQualityDimension
    usefulness: ContentQualityDimension
    service_fit: ContentQualityDimension
    search_intent_fit: ContentQualityDimension
    buyer_problem_fit: ContentQualityDimension
    cta_quality: ContentQualityDimension
    factual_precision: ContentQualityDimension
    polish_language_quality: ContentQualityDimension
    internal_link_fit: ContentQualityDimension
    measurement_readiness: ContentQualityDimension


def build_content_quality_review(
    *,
    item: ContentWorkItem,
    draft_package: ContentDraftPackage | None,
    structured_output: StructuredDraftOutput | None,
    revision: ContentDraftRevision | None = None,
    claim_ledger: ContentClaimLedger | None,
    sales_brief: ContentSalesBrief | None = None,
    duplicate_risk: ContentInventoryDuplicateRisk = "clear",
) -> ContentQualityReview:
    findings = [
        *_draft_package_findings(
            item=item,
            draft_package=draft_package,
            revision=revision,
        ),
        *_structured_output_findings(
            item=item,
            draft_package=draft_package,
            structured_output=structured_output,
            revision=revision,
        ),
        *_claim_findings(
            item=item,
            claim_ledger=claim_ledger,
            structured_output=structured_output,
            revision=revision,
        ),
        *_duplicate_findings(
            item=item,
            duplicate_risk=duplicate_risk,
        ),
        *_brief_fit_findings(sales_brief=sales_brief),
        *_measurement_findings(item=item, revision=revision),
        *_revision_readability_findings(item=item, revision=revision),
    ]
    blockers = [finding for finding in findings if finding.severity == "blocker"]
    needs_changes = [finding for finding in findings if finding.severity == "needs_changes"]
    verdict: ContentQualityVerdict
    if blockers:
        verdict = "blocked"
    elif needs_changes:
        verdict = "needs_changes"
    elif structured_output is None:
        verdict = "reviewable"
    else:
        verdict = "ready_for_human_review"

    evidence_ids = review_evidence.review_evidence_ids(
        item, draft_package, structured_output, claim_ledger
    )
    dimensions = _quality_dimensions(findings)
    return ContentQualityReview(
        review_id=(
            f"quality_review_{item.id}"
            if revision is None
            else f"quality_review_{item.id}_{revision.content_digest[:12]}"
        ),
        work_item_id=item.id,
        draft_package_id=None if draft_package is None else draft_package.id,
        revision_digest=None if revision is None else revision.content_digest,
        verdict=verdict,
        evidence_coverage=dimensions.evidence_coverage,
        claim_safety=dimensions.claim_safety,
        duplicate_risk=dimensions.duplicate_risk,
        usefulness=dimensions.usefulness,
        service_fit=dimensions.service_fit,
        search_intent_fit=dimensions.search_intent_fit,
        buyer_problem_fit=dimensions.buyer_problem_fit,
        cta_quality=dimensions.cta_quality,
        factual_precision=dimensions.factual_precision,
        polish_language_quality=dimensions.polish_language_quality,
        internal_link_fit=dimensions.internal_link_fit,
        measurement_readiness=dimensions.measurement_readiness,
        blockers=blockers,
        findings=findings,
        revision_instructions=_revision_instructions(findings),
        evidence_ids=evidence_ids,
        source_connectors=item.source_connectors,
        safe_next_step=_safe_next_step(verdict, blockers, needs_changes),
    )


def _quality_dimensions(
    findings: list[ContentQualityFinding],
) -> _ContentQualityDimensions:
    return _ContentQualityDimensions(
        evidence_coverage=_dimension(
            "Pokrycie dowodami",
            findings,
            blocked_codes={
                "missing_structured_output",
                "section_missing_evidence",
                "unknown_evidence_reference",
                "sales_brief_signal_thin",
            },
            needs_change_codes={"sales_brief_signal_review_required"},
        ),
        claim_safety=_dimension(
            "Bezpieczeństwo twierdzeń",
            findings,
            blocked_codes={
                "missing_claim_ledger",
                "claim_ledger_blocks_quality",
                "unsupported_claim_used",
                "forbidden_claim_used",
                "claim_missing_required_evidence",
                "required_claim_missing",
                "missing_forbidden_claim_acknowledgement",
            },
        ),
        duplicate_risk=_dimension(
            "Ryzyko duplikacji",
            findings,
            blocked_codes={"duplicate_risk_not_clear"},
        ),
        usefulness=_dimension(
            "Użyteczność dla czytelnika",
            findings,
            blocked_codes={"sales_brief_signal_thin"},
            needs_change_codes={
                "sales_brief_signal_review_required",
                "thin_section",
                "wall_of_text",
                "weak_cta",
                "missing_buyer_problem",
                "missing_service_fit",
            },
        ),
        service_fit=_dimension(
            "Dopasowanie do usługi",
            findings,
            needs_change_codes={"missing_service_fit"},
        ),
        search_intent_fit=_dimension(
            "Dopasowanie do intencji",
            findings,
            needs_change_codes={"missing_search_intent"},
        ),
        buyer_problem_fit=_dimension(
            "Problem kupującego",
            findings,
            needs_change_codes={"missing_buyer_problem"},
        ),
        cta_quality=_dimension(
            "Jakość CTA",
            findings,
            needs_change_codes={"weak_cta"},
        ),
        factual_precision=_dimension(
            "Precyzja faktów",
            findings,
            blocked_codes={"unknown_evidence_reference"},
        ),
        polish_language_quality=_dimension(
            "Język polski",
            findings,
            blocked_codes={"non_polish_language"},
        ),
        internal_link_fit=_dimension(
            "Linkowanie wewnętrzne",
            findings,
            needs_change_codes={"missing_internal_links"},
        ),
        measurement_readiness=_dimension(
            "Gotowość pomiaru",
            findings,
            blocked_codes={"missing_measurement_window"},
        ),
    )


def _draft_package_findings(
    *,
    item: ContentWorkItem,
    draft_package: ContentDraftPackage | None,
    revision: ContentDraftRevision | None,
) -> list[ContentQualityFinding]:
    if draft_package is None:
        # Full-document v2 revisions are the durable source of truth for the
        # current pipeline. They already carry section/evidence/claim lineage;
        # requiring the legacy draft-package projection here would make a
        # successfully persisted full document impossible to review.
        if revision is not None and revision.schema_version == "wilq_content_draft_revision_v2":
            return []
        return [
            _finding(
                "missing_draft_package",
                "blocker",
                "Brakuje paczki szkicu",
                "Ocena jakości wymaga paczki szkicu z mapą sekcji i dowodów.",
                "Najpierw przygotuj paczkę szkicu z WILQ gates.",
                source_connectors=item.source_connectors,
            )
        ]
    findings: list[ContentQualityFinding] = []
    if draft_package.work_item_id != item.id:
        findings.append(
            _finding(
                "draft_package_mismatch",
                "blocker",
                "Paczka szkicu dotyczy innego tematu",
                "Nie wolno oceniać szkicu przypisanego do innego work itemu.",
                "Użyj paczki szkicu dla aktualnego tematu.",
                source_connectors=item.source_connectors,
            )
        )
    if draft_package.publish_ready:
        findings.append(
            _finding(
                "draft_package_marked_publish_ready",
                "blocker",
                "Szkic nie może być oznaczony jako gotowy do publikacji",
                "WILQ wymaga oceny jakości i decyzji człowieka przed publikacyjnym językiem.",
                "Zmień szkic na tryb do sprawdzenia i wróć do review.",
                source_connectors=item.source_connectors,
            )
        )
    for section in draft_package.sections:
        if section.evidence_ids:
            continue
        findings.append(
            _finding(
                "section_missing_evidence",
                "blocker",
                "Sekcja nie ma dowodów",
                "Każda sekcja musi wskazywać dowody, z których korzysta.",
                "Przypisz dowody do sekcji albo usuń sekcję ze szkicu.",
                affected_section=section.heading,
                source_connectors=item.source_connectors,
            )
        )
    return findings


def _structured_output_findings(
    *,
    item: ContentWorkItem,
    draft_package: ContentDraftPackage | None,
    structured_output: StructuredDraftOutput | None,
    revision: ContentDraftRevision | None = None,
) -> list[ContentQualityFinding]:
    return review_findings.structured_output_findings(
        item=item,
        draft_package=draft_package,
        structured_output=structured_output,
        revision=revision,
        finding=_finding,
    )


def _claim_findings(
    *,
    item: ContentWorkItem,
    claim_ledger: ContentClaimLedger | None,
    structured_output: StructuredDraftOutput | None,
    revision: ContentDraftRevision | None = None,
) -> list[ContentQualityFinding]:
    return review_findings.claim_findings(
        item=item,
        claim_ledger=claim_ledger,
        structured_output=structured_output,
        revision=revision,
        finding=_finding,
    )


def _duplicate_findings(
    *,
    item: ContentWorkItem,
    duplicate_risk: ContentInventoryDuplicateRisk,
) -> list[ContentQualityFinding]:
    if duplicate_risk == "clear" and item.duplicate_status == "checked":
        return []
    return [
        _finding(
            "duplicate_risk_not_clear",
            "blocker",
            "Nie zamknięto ryzyka duplikacji",
            "Szkic bez sprawdzenia duplikacji może kanibalizować istniejące treści.",
            "Najpierw zamknij duplicate/canonical gate dla tego tematu.",
            evidence_ids=item.evidence_ids,
            source_connectors=item.source_connectors,
        )
    ]


def _brief_fit_findings(
    *,
    sales_brief: ContentSalesBrief | None,
) -> list[ContentQualityFinding]:
    if sales_brief is None:
        return [
            _finding(
                "missing_service_fit",
                "needs_changes",
                "Brakuje dopasowania do usługi",
                "Bez briefu WILQ nie wie, jak temat pomaga klientowi Ekologus.",
                "Podłącz brief sprzedażowy przed oceną jakości.",
            ),
            _finding(
                "missing_search_intent",
                "needs_changes",
                "Brakuje intencji wyszukiwania",
                "Treść musi odpowiadać na konkretną intencję, nie tylko na frazę.",
                "Uzupełnij intencję w briefie.",
            ),
            _finding(
                "missing_buyer_problem",
                "needs_changes",
                "Brakuje problemu kupującego",
                "Treść musi rozwiązywać realny problem osoby po stronie klienta.",
                "Uzupełnij problem kupującego w briefie.",
            ),
        ]
    findings: list[ContentQualityFinding] = []
    if sales_brief.signal_quality.status == "thin":
        findings.append(
            _finding(
                "sales_brief_signal_thin",
                "blocker",
                "Brief ma zbyt cienki sygnał",
                sales_brief.signal_quality.reason,
                sales_brief.signal_quality.safe_next_step,
                evidence_ids=sales_brief.evidence_ids,
                source_connectors=sales_brief.source_connectors,
            )
        )
    elif sales_brief.signal_quality.status == "review_required":
        findings.append(
            _finding(
                "sales_brief_signal_review_required",
                "needs_changes",
                "Brief wymaga review źródeł",
                sales_brief.signal_quality.reason,
                sales_brief.signal_quality.safe_next_step,
                evidence_ids=sales_brief.evidence_ids,
                source_connectors=sales_brief.source_connectors,
            )
        )
    if not sales_brief.service_fit.strip():
        findings.append(
            _finding(
                "missing_service_fit",
                "needs_changes",
                "Brakuje dopasowania do usługi",
                "Treść musi wskazywać, jak temat pasuje do pracy Ekologus.",
                "Uzupełnij service fit bez obietnicy efektu.",
                evidence_ids=sales_brief.evidence_ids,
                source_connectors=sales_brief.source_connectors,
            )
        )
    if not sales_brief.search_intent.strip():
        findings.append(
            _finding(
                "missing_search_intent",
                "needs_changes",
                "Brakuje intencji wyszukiwania",
                "Szkic musi odpowiadać na intencję użytkownika, nie tylko zawierać temat.",
                "Uzupełnij search intent w briefie.",
                evidence_ids=sales_brief.evidence_ids,
                source_connectors=sales_brief.source_connectors,
            )
        )
    if not sales_brief.buyer_problem.strip():
        findings.append(
            _finding(
                "missing_buyer_problem",
                "needs_changes",
                "Brakuje problemu kupującego",
                "Treść musi pomóc osobie, która ma realny problem biznesowy.",
                "Uzupełnij buyer problem w briefie.",
                evidence_ids=sales_brief.evidence_ids,
                source_connectors=sales_brief.source_connectors,
            )
        )
    return findings


def _measurement_findings(
    *, item: ContentWorkItem, revision: ContentDraftRevision | None
) -> list[ContentQualityFinding]:
    if item.measurement_window_status != "missing" and item.measurement_window_id:
        return []
    if revision is not None and item.wordpress_handoff_status in {
        "missing",
        "blocked",
        "prepared",
    }:
        return [
            _finding(
                "measurement_window_pending_publication",
                "info",
                "Pomiar zostanie otwarty po publikacji",
                (
                    "Measurement window wiąże się z exact publikacją i nie może "
                    "powstać przed WordPress draft handoffem."
                ),
                "Po zatwierdzeniu i publikacji utwórz publication-bound measurement window.",
                evidence_ids=item.evidence_ids,
                source_connectors=item.source_connectors,
            )
        ]
    return [
        _finding(
            "missing_measurement_window",
            "blocker",
            "Brakuje planu pomiaru",
            "Nie trzeba czekać na metryki, ale trzeba od razu wiedzieć, co będzie mierzone.",
            "Utwórz measurement window przed sprawdzeniem człowieka.",
            evidence_ids=item.evidence_ids,
            source_connectors=item.source_connectors,
        )
    ]


def _revision_readability_findings(
    *, item: ContentWorkItem, revision: ContentDraftRevision | None
) -> list[ContentQualityFinding]:
    if revision is None or revision.schema_version != "wilq_content_draft_revision_v2":
        return []
    return [
        _finding(
            issue.code,
            "needs_changes",
            issue.label,
            issue.reason,
            issue.next_step,
            affected_section=issue.affected_section,
            source_connectors=item.source_connectors,
        )
        for issue in revision_readability_issues(revision.sections)
    ]


def _dimension(
    label: str,
    findings: list[ContentQualityFinding],
    *,
    blocked_codes: set[ContentQualityFindingCode] | None = None,
    needs_change_codes: set[ContentQualityFindingCode] | None = None,
) -> ContentQualityDimension:
    blocked_codes = blocked_codes or set()
    needs_change_codes = needs_change_codes or set()
    if any(finding.code in blocked_codes for finding in findings):
        return ContentQualityDimension(
            status="blocked",
            label=label,
            reason="Ten obszar blokuje przejście szkicu do człowieka.",
        )
    if any(finding.code in needs_change_codes for finding in findings):
        return ContentQualityDimension(
            status="needs_changes",
            label=label,
            reason="Ten obszar wymaga poprawki przed wygodnym review.",
        )
    return ContentQualityDimension(
        status="pass",
        label=label,
        reason="Ten obszar spełnia aktualne bramki WILQ.",
    )


def _revision_instructions(
    findings: list[ContentQualityFinding],
) -> list[ContentRevisionInstruction]:
    instructions: list[ContentRevisionInstruction] = []
    for index, finding in enumerate(
        [item for item in findings if item.severity in {"blocker", "needs_changes"}],
        start=1,
    ):
        instructions.append(
            ContentRevisionInstruction(
                id=f"content_revision_{index}",
                affected_section=finding.affected_section,
                change=finding.next_step,
                reason=finding.reason,
                required_evidence_ids=finding.evidence_ids,
                forbidden_claims_to_avoid=(
                    [finding.reason] if finding.code == "forbidden_claim_used" else []
                ),
                human_review_checklist_additions=[finding.label],
            )
        )
    return instructions


def _safe_next_step(
    verdict: ContentQualityVerdict,
    blockers: list[ContentQualityFinding],
    needs_changes: list[ContentQualityFinding],
) -> str:
    if blockers:
        return blockers[0].next_step
    if needs_changes:
        return needs_changes[0].next_step
    if verdict == "ready_for_human_review":
        return "Przekaż szkic do sprawdzenia człowieka, bez publikacji i bez WordPress write."
    return "Uzupełnij szkic i uruchom ocenę jakości ponownie."


def _finding(
    code: ContentQualityFindingCode,
    severity: ContentQualitySeverity,
    label: str,
    reason: str,
    next_step: str,
    *,
    affected_section: str | None = None,
    evidence_ids: list[str] | None = None,
    source_connectors: list[str] | None = None,
) -> ContentQualityFinding:
    return ContentQualityFinding(
        code=code,
        severity=severity,
        label=label,
        reason=reason,
        next_step=next_step,
        affected_section=affected_section,
        evidence_ids=evidence_ids or [],
        source_connectors=source_connectors or [],
    )


def _weak_cta(cta: str) -> bool:
    return weak_cta(cta)
