from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from wilq.content.claims.ledger import (
    ContentClaimLedger,
    ContentClaimLedgerBlocker,
    claim_ledger_blockers,
)
from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.drafts.structured_generation import StructuredDraftOutput
from wilq.content.quality import review_evidence
from wilq.content.quality.reading_quality import weak_cta
from wilq.content.workflow.contracts.models import ContentWorkItem
from wilq.content.workflow.documents.revisions import ContentDraftRevision

if TYPE_CHECKING:
    from wilq.content.quality.review import (
        ContentQualityFinding,
        ContentQualityFindingCode,
        ContentQualitySeverity,
    )


class FindingFactory(Protocol):
    def __call__(
        self,
        code: ContentQualityFindingCode,
        severity: ContentQualitySeverity,
        label: str,
        reason: str,
        next_step: str,
        *,
        affected_section: str | None = None,
        evidence_ids: list[str] | None = None,
        source_connectors: list[str] | None = None,
    ) -> ContentQualityFinding: ...


def structured_output_findings(
    *,
    item: ContentWorkItem,
    draft_package: ContentDraftPackage | None,
    structured_output: StructuredDraftOutput | None,
    revision: ContentDraftRevision | None,
    finding: FindingFactory,
) -> list[ContentQualityFinding]:
    if structured_output is None:
        if revision is not None and revision.schema_version == "wilq_content_draft_revision_v2":
            return []
        return [
            finding(
                "missing_structured_output",
                "blocker",
                "Brakuje ustrukturyzowanego szkicu",
                "Ocena jakości przed sprawdzeniem człowieka wymaga szkicu z runtime WILQ.",
                "Wygeneruj szkic przez WILQ Structured Outputs po przejściu bramek.",
                evidence_ids=item.evidence_ids,
                source_connectors=item.source_connectors,
            )
        ]
    return [
        *_structured_evidence_findings(item, structured_output, finding),
        *_unknown_evidence_findings(item, draft_package, structured_output, finding),
        *_forbidden_claim_acknowledgement_findings(
            item, draft_package, structured_output, finding
        ),
        *_structured_usefulness_findings(item, structured_output, finding),
    ]


def claim_findings(
    *,
    item: ContentWorkItem,
    claim_ledger: ContentClaimLedger | None,
    structured_output: StructuredDraftOutput | None,
    revision: ContentDraftRevision | None,
    finding: FindingFactory,
) -> list[ContentQualityFinding]:
    if claim_ledger is None:
        return [
            finding(
                "missing_claim_ledger",
                "blocker",
                "Brakuje sprawdzenia twierdzeń",
                "Szkic nie może przejść jakości bez listy dozwolonych i zablokowanych twierdzeń.",
                "Zbuduj claim ledger przed oceną jakości.",
                evidence_ids=item.evidence_ids,
                source_connectors=item.source_connectors,
            )
        ]
    ledger_blockers = _active_ledger_blockers(claim_ledger, revision)
    findings = _ledger_blocker_findings(item, claim_ledger, ledger_blockers, finding)
    if structured_output is None:
        return findings
    findings.extend(
        _structured_claim_usage_findings(
            item, claim_ledger, structured_output, ledger_blockers, finding
        )
    )
    findings.extend(
        _claim_evidence_findings(item, claim_ledger, structured_output, finding)
    )
    return findings


def _structured_evidence_findings(
    item: ContentWorkItem,
    structured_output: StructuredDraftOutput,
    finding: FindingFactory,
) -> list[ContentQualityFinding]:
    findings: list[ContentQualityFinding] = []
    if structured_output.language != "pl-PL":
        findings.append(
            finding(
                "non_polish_language",
                "blocker",
                "Szkic nie jest po polsku",
                "Wilku pracuje po polsku, a szkic musi być gotowy do polskiego review.",
                "Wygeneruj szkic ponownie w języku polskim.",
                evidence_ids=item.evidence_ids,
                source_connectors=item.source_connectors,
            )
        )
    if not structured_output.source_facts_used:
        findings.append(
            finding(
                "section_missing_evidence",
                "blocker",
                "Szkic nie wskazuje użytych dowodów",
                "Nie wolno przekazać szkicu, którego źródła nie są jawne.",
                "Wygeneruj szkic ponownie z mapą dowodów.",
                source_connectors=item.source_connectors,
            )
        )
    for section in structured_output.sections:
        if section.evidence_ids:
            continue
        findings.append(
            finding(
                "section_missing_evidence",
                "blocker",
                "Sekcja szkicu nie ma dowodów",
                "Każda sekcja szkicu musi wskazywać użyte dowody.",
                "Uzupełnij dowody dla sekcji albo usuń sekcję.",
                affected_section=section.heading,
                source_connectors=item.source_connectors,
            )
        )
    return findings


def _unknown_evidence_findings(
    item: ContentWorkItem,
    draft_package: ContentDraftPackage | None,
    structured_output: StructuredDraftOutput,
    finding: FindingFactory,
) -> list[ContentQualityFinding]:
    unknown_evidence = review_evidence.structured_output_evidence_ids(
        structured_output
    ).difference(review_evidence.allowed_evidence_ids(item, draft_package))
    if not unknown_evidence:
        return []
    return [
        finding(
            "unknown_evidence_reference",
            "blocker",
            "Szkic wskazuje obcy dowód",
            "Szkic może korzystać tylko z dowodów przekazanych przez WILQ gates.",
            "Usuń obce dowody: " + ", ".join(sorted(unknown_evidence)),
            evidence_ids=sorted(unknown_evidence),
            source_connectors=item.source_connectors,
        )
    ]


def _forbidden_claim_acknowledgement_findings(
    item: ContentWorkItem,
    draft_package: ContentDraftPackage | None,
    structured_output: StructuredDraftOutput,
    finding: FindingFactory,
) -> list[ContentQualityFinding]:
    if draft_package is None:
        return []
    missing_claims = sorted(
        set(draft_package.claims_removed_or_blocked).difference(
            structured_output.forbidden_claims_avoided
        )
    )
    if not missing_claims:
        return []
    return [
        finding(
            "missing_forbidden_claim_acknowledgement",
            "blocker",
            "Szkic nie potwierdza uniknięcia zakazanych claimów",
            "Ocena jakości wymaga jawnego potwierdzenia, że claimy usunięte "
            "z kontraktu nie trafiły do szkicu.",
            "Uzupełnij listę unikniętych claimów: " + "; ".join(missing_claims),
            evidence_ids=item.evidence_ids,
            source_connectors=item.source_connectors,
        )
    ]


def _structured_usefulness_findings(
    item: ContentWorkItem,
    structured_output: StructuredDraftOutput,
    finding: FindingFactory,
) -> list[ContentQualityFinding]:
    findings: list[ContentQualityFinding] = []
    if weak_cta(structured_output.cta):
        findings.append(
            finding(
                "weak_cta",
                "needs_changes",
                "CTA jest za słabe albo puste",
                "Treść ma prowadzić do bezpiecznego następnego kroku dla klienta.",
                "Dopisz konkretne CTA bez obietnicy wyniku.",
                evidence_ids=item.evidence_ids,
                source_connectors=item.source_connectors,
            )
        )
    if not structured_output.internal_links:
        findings.append(
            finding(
                "missing_internal_links",
                "needs_changes",
                "Brakuje linkowania wewnętrznego",
                "Szkic powinien wskazać bezpieczne linki wewnętrzne do dalszej ścieżki.",
                "Dodaj linki wewnętrzne z briefu albo oznacz brak jako decyzję człowieka.",
                evidence_ids=item.evidence_ids,
                source_connectors=item.source_connectors,
            )
        )
    return findings


def _active_ledger_blockers(
    claim_ledger: ContentClaimLedger,
    revision: ContentDraftRevision | None,
) -> list[ContentClaimLedgerBlocker]:
    blockers = claim_ledger_blockers(claim_ledger)
    if revision is None or revision.schema_version != "wilq_content_draft_revision_v2":
        return blockers
    used_claim_ids = {
        claim_id for section in revision.sections for claim_id in section.claim_ids
    }
    return [blocker for blocker in blockers if blocker.claim_id in used_claim_ids]


def _ledger_blocker_findings(
    item: ContentWorkItem,
    claim_ledger: ContentClaimLedger,
    ledger_blockers: list[ContentClaimLedgerBlocker],
    finding: FindingFactory,
) -> list[ContentQualityFinding]:
    if not ledger_blockers:
        return []
    return [
        finding(
            "claim_ledger_blocks_quality",
            "blocker",
            "Sprawdzenie twierdzeń blokuje szkic",
            "Ryzykowne albo niezweryfikowane twierdzenia muszą zostać usunięte.",
            "Rozwiąż claim ledger przed oceną jakości.",
            evidence_ids=review_evidence.unique(
                entry.evidence_ids for entry in claim_ledger.entries
            ),
            source_connectors=item.source_connectors,
        )
    ]


def _structured_claim_usage_findings(
    item: ContentWorkItem,
    claim_ledger: ContentClaimLedger,
    structured_output: StructuredDraftOutput,
    ledger_blockers: list[ContentClaimLedgerBlocker],
    finding: FindingFactory,
) -> list[ContentQualityFinding]:
    blocked_claim_texts = {
        entry.claim_text
        for blocker in ledger_blockers
        for entry in claim_ledger.entries
        if entry.id == blocker.claim_id
    }
    used_claims = {
        claim
        for section in structured_output.sections
        for claim in section.claims_used
        if claim
    }
    ledger_claim_texts = {entry.claim_text for entry in claim_ledger.entries}
    unsupported_claims = sorted(used_claims.difference(ledger_claim_texts))
    leaked_claims = sorted(used_claims.intersection(blocked_claim_texts))
    required_claims = sorted(
        entry.claim_text
        for entry in claim_ledger.entries
        if entry.required
        and entry.status in {"allowed_with_evidence", "allowed_general"}
        and entry.claim_text not in used_claims
    )
    findings: list[ContentQualityFinding] = []
    if unsupported_claims:
        findings.append(
            finding(
                "unsupported_claim_used",
                "blocker",
                "Szkic używa twierdzenia spoza rejestru",
                "Każde twierdzenie użyte przez model musi istnieć w Claim Ledger.",
                "Usuń albo dodaj do Claim Ledger po review: "
                + "; ".join(unsupported_claims),
                source_connectors=item.source_connectors,
            )
        )
    if leaked_claims:
        findings.append(
            finding(
                "forbidden_claim_used",
                "blocker",
                "Szkic używa zablokowanego twierdzenia",
                "Zablokowane claimy nie mogą pojawić się w treści.",
                "Usuń zablokowane twierdzenia: " + "; ".join(leaked_claims),
                source_connectors=item.source_connectors,
            )
        )
    if required_claims:
        findings.append(
            finding(
                "required_claim_missing",
                "blocker",
                "Szkic pomija wymagany claim",
                "Claim Ledger oznacza te twierdzenia jako wymagane do pokrycia w szkicu.",
                "Dodaj wymagane twierdzenia do właściwej sekcji albo zmień Claim Ledger: "
                + "; ".join(required_claims),
                source_connectors=item.source_connectors,
            )
        )
    return findings


def _claim_evidence_findings(
    item: ContentWorkItem,
    claim_ledger: ContentClaimLedger,
    structured_output: StructuredDraftOutput,
    finding: FindingFactory,
) -> list[ContentQualityFinding]:
    evidence_by_claim = {
        entry.claim_text: set(entry.evidence_ids)
        for entry in claim_ledger.entries
        if entry.status == "allowed_with_evidence" and entry.evidence_ids
    }
    findings: list[ContentQualityFinding] = []
    for section in structured_output.sections:
        section_evidence = set(section.evidence_ids)
        for claim in section.claims_used:
            required_evidence = evidence_by_claim.get(claim)
            if not required_evidence or required_evidence.issubset(section_evidence):
                continue
            findings.append(
                finding(
                    "claim_missing_required_evidence",
                    "blocker",
                    "Twierdzenie nie ma wymaganych dowodów w sekcji",
                    "Sekcja używa claimu z Claim Ledger, ale nie wskazuje wszystkich "
                    "dowodów wymaganych dla tego twierdzenia.",
                    "Dodaj wymagane dowody do sekcji albo usuń claim: " + claim,
                    affected_section=section.heading,
                    evidence_ids=sorted(required_evidence.difference(section_evidence)),
                    source_connectors=item.source_connectors,
                )
            )
    return findings
