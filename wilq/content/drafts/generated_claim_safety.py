from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftBlocker,
    ContentInitialDraftModelOutput,
)
from wilq.content.drafts.initial_full_draft_scope import draftable_planning_sections
from wilq.content.drafts.structured_generation import (
    StructuredDraftGenerationContract,
    StructuredDraftOutput,
    StructuredDraftOutputSection,
)
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.workflow.decisions.planning import ContentPlanningProposal

GeneratedClaimSafetyIssueCode = Literal[
    "known_blocked_claim_text_present",
    "undeclared_high_risk_claim_language",
]


@dataclass(frozen=True, slots=True)
class GeneratedClaimSafetyIssue:
    code: GeneratedClaimSafetyIssueCode
    heading: str
    claim_text: str | None = None


_HIGH_RISK_PATTERNS = (
    re.compile(r"(?<!nie )\bgwarant\w*\b"),
    re.compile(r"\bstuprocent\w*\b"),
    re.compile(r"\b100\s*%\b"),
    re.compile(r"\bpełn\w*\s+zgodnoś\w*\b"),
    re.compile(r"\bzgodnoś\w*(?:\s+\w+){0,3}\s+praw\w*\b"),
    re.compile(r"\bbez\s+ryzyk\w*\b"),
    re.compile(
        r"\b(?:zwiększ|popraw|podnies|zapewni|przynies)\w*"
        r"(?:\s+\w+){0,8}\s+"
        r"(?:lead|sprzedaż|przych|pozycj|widocznoś|konwersj|ruch)\w*\b"
    ),
    re.compile(
        r"\b(?:wzrost|zwiększen|popraw)\w*(?:\s+\w+){0,8}\s+"
        r"(?:lead|sprzedaż|przych|pozycj|widocznoś|konwersj|ruch)\w*\b"
    ),
)


def claim_safety_output(
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
    generation_contract: StructuredDraftGenerationContract,
) -> StructuredDraftOutput:
    claim_text_by_id = {item.id: item.claim_text for item in planning_input.claim_ledger}
    sections: list[StructuredDraftOutputSection] = []
    draftable_sections = draftable_planning_sections(proposal.sections)
    global_claim_ids = [claim_id for item in draftable_sections for claim_id in item.claim_ids]
    sections.append(
        StructuredDraftOutputSection(
            heading="Page assets",
            body_markdown="\n".join(
                output.page_assets.model_dump(mode="json", exclude_none=True).values()
            ),
            evidence_ids=proposal.evidence_ids,
            claims_used=claim_texts(global_claim_ids, claim_text_by_id),
        )
    )
    for plan, generated in zip(draftable_sections, output.sections, strict=True):
        sections.append(
            StructuredDraftOutputSection(
                heading=generated.heading,
                body_markdown=generated.body_markdown,
                evidence_ids=plan.evidence_ids,
                claims_used=claim_texts(plan.claim_ids, claim_text_by_id),
            )
        )
    sections.extend(asset_safety_sections(proposal, output, claim_text_by_id))
    return StructuredDraftOutput(
        draft_kind="full_draft",
        language="pl-PL",
        title=output.page_assets.wordpress_title,
        meta_title=output.page_assets.meta_title,
        meta_description=output.page_assets.meta_description,
        h1=output.page_assets.h1,
        sections=sections,
        faq=[item.answer_markdown for item in output.faq],
        cta="\n".join(item.body_markdown for item in output.cta_blocks),
        internal_links=[item.anchor_text for item in output.internal_links],
        source_facts_used=planning_input.evidence_ids,
        claims_needing_review=[],
        forbidden_claims_avoided=generation_contract.model_input.claims_removed_or_blocked,
        human_review_checklist=generation_contract.model_input.human_review_questions,
        publish_ready=False,
    )


def asset_safety_sections(
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
    claim_text_by_id: dict[str, str],
) -> list[StructuredDraftOutputSection]:
    sections: list[StructuredDraftOutputSection] = []
    for index, (faq_plan, faq_output) in enumerate(zip(proposal.faq, output.faq, strict=True)):
        sections.append(
            StructuredDraftOutputSection(
                heading=f"FAQ {index + 1}: {faq_output.question}",
                body_markdown=faq_output.answer_markdown,
                evidence_ids=faq_plan.evidence_ids,
                claims_used=claim_texts(faq_plan.claim_ids, claim_text_by_id),
            )
        )
    for index, (cta_plan, cta_output) in enumerate(
        zip(proposal.cta_blocks, output.cta_blocks, strict=True)
    ):
        sections.append(
            StructuredDraftOutputSection(
                heading=f"CTA {index + 1}",
                body_markdown=cta_output.body_markdown,
                evidence_ids=cta_plan.evidence_ids,
                claims_used=claim_texts(cta_plan.claim_ids, claim_text_by_id),
            )
        )
    for index, (link_plan, link_output) in enumerate(
        zip(proposal.internal_links, output.internal_links, strict=True)
    ):
        sections.append(
            StructuredDraftOutputSection(
                heading=f"Link {index + 1}",
                body_markdown=link_output.anchor_text,
                evidence_ids=link_plan.evidence_ids,
                claims_used=claim_texts(link_plan.claim_ids, claim_text_by_id),
            )
        )
    return sections


def claim_texts(claim_ids: list[str], claim_text_by_id: dict[str, str]) -> list[str]:
    return [claim_text_by_id[item] for item in claim_ids if item in claim_text_by_id]


def generated_claim_safety_issues(
    output: StructuredDraftOutput,
    contract: StructuredDraftGenerationContract,
) -> list[GeneratedClaimSafetyIssue]:
    """Catch typed claim mismatches and narrow, high-risk generated language.

    This is deliberately not a semantic verifier. It protects exact Claim Ledger
    boundaries and a small class of promise/compliance language; human semantic
    review remains mandatory for every generated proposal.
    """

    blocked_claims = _unique(
        [
            *contract.model_input.claims_removed_or_blocked,
            *(
                marker.claim_text
                for marker in contract.model_input.removed_or_blocked_claim_markers
            ),
        ]
    )
    issues: list[GeneratedClaimSafetyIssue] = []
    for section in output.sections:
        normalized_body = _normalize(section.body_markdown)
        declared_claims = _unique(section.claims_used)
        for claim in blocked_claims:
            if _normalize(claim) not in normalized_body:
                continue
            issues.append(
                GeneratedClaimSafetyIssue(
                    code="known_blocked_claim_text_present",
                    heading=section.heading,
                    claim_text=claim,
                )
            )
        undeclared_body = normalized_body
        for claim in declared_claims:
            normalized_claim = _normalize(claim)
            if normalized_claim:
                undeclared_body = undeclared_body.replace(normalized_claim, " ")
        if any(pattern.search(undeclared_body) for pattern in _HIGH_RISK_PATTERNS):
            issues.append(
                GeneratedClaimSafetyIssue(
                    code="undeclared_high_risk_claim_language",
                    heading=section.heading,
                )
            )
    return issues


def generated_claim_blocker(
    issues: list[GeneratedClaimSafetyIssue],
) -> ContentInitialDraftBlocker:
    """Describe the exact planned section without exposing generated prose."""

    headings = list(dict.fromkeys(item.heading.strip() for item in issues if item.heading.strip()))
    section_detail = f" Sekcje planu: {', '.join(headings[:3])}." if headings else ""
    return ContentInitialDraftBlocker(
        code="generated_claim_blocked",
        label="Tekst zawiera niedozwoloną obietnicę",
        reason="Deterministyczna bramka wykryła blocked claim albo ryzykowny język."
        + section_detail,
        next_step="Usuń niedozwolone twierdzenie ze wskazanej sekcji i wygeneruj nową próbę.",
        source_codes=list(dict.fromkeys(item.code for item in issues)),
    )


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.sub(r"[^\w%]+", " ", normalized).split())


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value.strip()))


__all__ = [
    "GeneratedClaimSafetyIssue",
    "asset_safety_sections",
    "claim_safety_output",
    "claim_texts",
    "generated_claim_blocker",
    "generated_claim_safety_issues",
]
