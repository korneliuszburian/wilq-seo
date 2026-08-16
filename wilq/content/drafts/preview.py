from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from wilq.content.drafts.generated_claim_safety import generated_claim_safety_issues
from wilq.content.drafts.structured_generation import (
    StructuredDraftGenerationContract,
    StructuredDraftOutput,
)
from wilq.content.operator_copy import build_blocker

StructuredDraftPreviewBlockerCode = Literal[
    "missing_output",
    "missing_contract",
    "claims_need_review",
    "missing_source_facts",
    "section_missing_evidence",
    "unknown_evidence_reference",
    "unknown_claim_reference",
    "known_blocked_claim_text_present",
    "undeclared_high_risk_claim_language",
    "claim_missing_required_evidence",
    "required_claim_missing",
    "missing_forbidden_claim_acknowledgement",
]


class StructuredDraftPreviewBlocker(BaseModel):
    code: StructuredDraftPreviewBlockerCode
    label: str
    reason: str
    next_step: str


def structured_draft_preview_blockers(
    *,
    output: StructuredDraftOutput | None,
    contract: StructuredDraftGenerationContract | None,
) -> list[StructuredDraftPreviewBlocker]:
    blockers: list[StructuredDraftPreviewBlocker] = []
    if output is None:
        blockers.append(
            build_blocker(
                StructuredDraftPreviewBlocker,
                code="missing_output",
                label="Brakuje szkicu",
                reason="Podgląd wymaga ustrukturyzowanego szkicu z runtime WILQ.",
                next_step="Najpierw wygeneruj albo wczytaj ustrukturyzowany szkic.",
            )
        )
    if contract is None:
        blockers.append(
            build_blocker(
                StructuredDraftPreviewBlocker,
                code="missing_contract",
                label="Brakuje kontraktu szkicu",
                reason="Nie można sprawdzić szkicu bez kontraktu, z którego powstał.",
                next_step="Użyj kontraktu generowania powiązanego z tym szkicem.",
            )
        )
    if output is None or contract is None:
        return blockers

    if output.claims_needing_review:
        blockers.append(
            build_blocker(
                StructuredDraftPreviewBlocker,
                code="claims_need_review",
                label="Szkic ma twierdzenia do sprawdzenia",
                reason="WILQ nie pokaże szkicu jako gotowego do przekazania, gdy są "
                "twierdzenia wymagające decyzji człowieka.",
                next_step="Usuń albo zatwierdź wskazane twierdzenia przed kolejnym krokiem.",
            )
        )
    if not output.source_facts_used:
        blockers.append(
            build_blocker(
                StructuredDraftPreviewBlocker,
                code="missing_source_facts",
                label="Szkic nie wskazuje użytych dowodów",
                reason="Każdy szkic musi pokazać, z których dowodów korzysta.",
                next_step="Wygeneruj szkic ponownie z mapą dowodów.",
            )
        )

    allowed_evidence_ids = _contract_evidence_ids(contract)
    referenced_evidence_ids = _output_evidence_ids(output)
    missing_section_evidence = any(not section.evidence_ids for section in output.sections)
    if missing_section_evidence:
        blockers.append(
            build_blocker(
                StructuredDraftPreviewBlocker,
                code="section_missing_evidence",
                label="Sekcja nie ma dowodów",
                reason="Każda sekcja szkicu musi zachować powiązanie z dowodami.",
                next_step="Uzupełnij mapę dowodów dla każdej sekcji.",
            )
        )

    unknown_ids = sorted(referenced_evidence_ids.difference(allowed_evidence_ids))
    if unknown_ids:
        blockers.append(
            build_blocker(
                StructuredDraftPreviewBlocker,
                code="unknown_evidence_reference",
                label="Szkic wskazuje obcy dowód",
                reason="Szkic może używać tylko dowodów z kontraktu WILQ.",
                next_step="Usuń obce dowody ze szkicu: " + ", ".join(unknown_ids),
            )
        )

    blockers.extend(_claim_contract_blockers(output, contract))
    return blockers


def _contract_evidence_ids(contract: StructuredDraftGenerationContract) -> set[str]:
    values = {fact.evidence_id for fact in contract.model_input.source_facts}
    for section in contract.model_input.sections:
        values.update(section.evidence_ids)
    return {value for value in values if value}


def _output_evidence_ids(output: StructuredDraftOutput) -> set[str]:
    values = set(output.source_facts_used)
    for section in output.sections:
        values.update(section.evidence_ids)
    return {value for value in values if value}


def _output_claims(output: StructuredDraftOutput) -> set[str]:
    values: set[str] = set()
    for section in output.sections:
        values.update(section.claims_used)
    return {value for value in values if value}


def _claim_contract_blockers(
    output: StructuredDraftOutput,
    contract: StructuredDraftGenerationContract,
) -> list[StructuredDraftPreviewBlocker]:
    blockers: list[StructuredDraftPreviewBlocker] = []
    used_claims = _output_claims(output)
    unknown_claims = sorted(used_claims.difference(contract.model_input.claims_allowed))
    if unknown_claims:
        blockers.append(
            build_blocker(
                StructuredDraftPreviewBlocker,
                code="unknown_claim_reference",
                label="Szkic używa claimu spoza kontraktu",
                reason="Podgląd może pokazać tylko twierdzenia dopuszczone przez kontrakt WILQ.",
                next_step="Usuń obce twierdzenia ze szkicu: " + "; ".join(unknown_claims),
            )
        )
    blockers.extend(_generated_claim_blockers(output, contract))
    missing_required_claims = sorted(
        marker.claim_text
        for marker in contract.model_input.claim_markers
        if marker.required and marker.claim_text not in used_claims
    )
    if missing_required_claims:
        blockers.append(
            build_blocker(
                StructuredDraftPreviewBlocker,
                code="required_claim_missing",
                label="Szkic pomija wymagany claim",
                reason="Kontrakt WILQ oznaczył claim jako wymagany do pokrycia w szkicu.",
                next_step="Dodaj wymagany claim do odpowiedniej sekcji albo zmień Claim Ledger: "
                + "; ".join(missing_required_claims),
            )
        )
    missing_forbidden_claims = sorted(
        set(contract.model_input.claims_removed_or_blocked).difference(
            output.forbidden_claims_avoided
        )
    )
    if missing_forbidden_claims:
        blockers.append(
            build_blocker(
                StructuredDraftPreviewBlocker,
                code="missing_forbidden_claim_acknowledgement",
                label="Szkic nie potwierdza uniknięcia zakazanych claimów",
                reason="Podgląd wymaga jawnego potwierdzenia, że claimy usunięte z kontraktu "
                "nie trafiły do szkicu.",
                next_step="Uzupełnij listę unikniętych claimów: "
                + "; ".join(missing_forbidden_claims),
            )
        )
    blockers.extend(_claim_marker_evidence_blockers(output, contract))
    return blockers


def _generated_claim_blockers(
    output: StructuredDraftOutput,
    contract: StructuredDraftGenerationContract,
) -> list[StructuredDraftPreviewBlocker]:
    issues = generated_claim_safety_issues(output, contract)
    if not issues:
        return []
    issue = issues[0]
    labels = {
        "known_blocked_claim_text_present": "Zablokowany claim trafił do tekstu",
        "undeclared_high_risk_claim_language": (
            "Tekst zawiera niezadeklarowaną obietnicę albo claim prawny"
        ),
    }
    return [
        build_blocker(
            StructuredDraftPreviewBlocker,
            code=issue.code,
            label=labels[issue.code],
            reason="Treść sekcji nie zgadza się z deklarowanym, dozwolonym lineage claimów.",
            next_step=(
                f'Popraw sekcję "{issue.heading}" i wygeneruj ją ponownie; '
                "WILQ nie zapisze tego tekstu bez semantycznego review."
            ),
        )
    ]


def _claim_marker_evidence_blockers(
    output: StructuredDraftOutput,
    contract: StructuredDraftGenerationContract,
) -> list[StructuredDraftPreviewBlocker]:
    marker_by_claim = {
        marker.claim_text: marker
        for marker in contract.model_input.claim_markers
        if marker.claim_text and marker.evidence_ids
    }
    if not marker_by_claim:
        return []

    blockers: list[StructuredDraftPreviewBlocker] = []
    for section in output.sections:
        section_evidence_ids = set(section.evidence_ids)
        for claim_text in section.claims_used:
            marker = marker_by_claim.get(claim_text)
            if marker is None:
                continue
            missing = sorted(set(marker.evidence_ids).difference(section_evidence_ids))
            if not missing:
                continue
            blockers.append(
                build_blocker(
                    StructuredDraftPreviewBlocker,
                    code="claim_missing_required_evidence",
                    label="Claim nie ma wymaganego dowodu w sekcji",
                    reason=(
                        "Szkic używa claimu z Claim Ledger, ale sekcja nie wskazuje "
                        "dowodu przypisanego do tego claimu."
                    ),
                    next_step=(
                        f'Uzupełnij dowody dla claimu "{claim_text}": ' + ", ".join(missing)
                    ),
                )
            )
    return blockers
