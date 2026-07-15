from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

from wilq.content.drafts.structured_generation import (
    StructuredDraftGenerationContract,
    StructuredDraftOutput,
)

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


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.sub(r"[^\w%]+", " ", normalized).split())


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value.strip()))


__all__ = ["GeneratedClaimSafetyIssue", "generated_claim_safety_issues"]
