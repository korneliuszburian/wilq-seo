from __future__ import annotations

from collections.abc import (
    Iterable,
    Mapping,
)
from typing import Any

from .shared import (
    CONTENT_CONTRACT_LABELS,
    CONTENT_URL_REVIEW_CONTRACT,
    _string_list,
)

__all__ = [
    "content_url_review_contract",
    "_content_contract_label",
    "_content_contract_labels",
    "content_contract_label",
    "content_contract_labels",
    "_prefixed_labels",
    "_reviewed_candidate_ids",
    "_reviewed_candidate_ids_from_details",
    "_reviewed_candidate_url_reviews",
    "_reviewed_candidate_url_reviews_from_details",
    "_reviewed_candidate_draft_readiness_from_details",
    "_review_summary_token",
    "_draft_readiness_review_contract",
    "_content_gate_status_summary",
    "_draft_readiness_review_contract_summary",
    "_draft_readiness_review_summary",
    "_content_gate_status_for_brief",
    "_content_gate_status_payload",
]



def content_url_review_contract() -> dict[str, Any]:
    allowed_outcomes = [
        "confirm_existing_public_url",
        "confirm_final_canonical_url",
        "request_duplicate_or_canonical_review",
        "block_until_public_inventory_known",
        "mark_preview_design_context_not_required",
    ]
    required_fields = [
        "source_public_url",
        "final_canonical_url",
        "intended_final_url",
        "review_outcome",
        "reviewed_by",
        "notes",
    ]
    blocked_outputs = [
        "wordpress_draft_write",
        "wordpress_publish",
        "non_public_url_as_final_canonical",
        "new_content_without_inventory_check",
        "duplicate_free_claim",
        "obietnica wzrostu pozycji albo leadów",
    ]
    return {
        "contract": CONTENT_URL_REVIEW_CONTRACT,
        "scope": "review_only",
        "canonical_home": "ekologus.pl",
        "preview_url_policy": "optional_only_when_explicitly_configured",
        "allowed_outcomes": allowed_outcomes,
        "allowed_outcome_labels": _content_contract_labels(allowed_outcomes),
        "required_fields": required_fields,
        "required_field_labels": _content_contract_labels(required_fields),
        "blocked_outputs": blocked_outputs,
        "blocked_output_labels": _content_contract_labels(blocked_outputs),
    }


def _content_contract_label(value: str | None) -> str:
    if not value:
        return "warunek treści do sprawdzenia"
    return CONTENT_CONTRACT_LABELS.get(value, "warunek treści do sprawdzenia")


def _content_contract_labels(values: Iterable[str]) -> list[str]:
    return [_content_contract_label(value) for value in values if value]


def content_contract_label(value: str) -> str:
    return _content_contract_label(value)


def content_contract_labels(values: Iterable[str]) -> list[str]:
    return _content_contract_labels(values)


def _prefixed_labels(prefix: str, values: Iterable[str]) -> list[str]:
    return [f"{prefix}: {label}" for label in _content_contract_labels(values)]


def _reviewed_candidate_ids(review_event_summaries: Iterable[str]) -> set[str]:
    candidate_ids: set[str] = set()
    for summary in review_event_summaries:
        if "candidate:" not in summary:
            continue
        for fragment in summary.split("candidate:")[1:]:
            candidate_id = fragment.split(",", 1)[0].split(".", 1)[0].strip()
            if candidate_id:
                candidate_ids.add(candidate_id)
    return candidate_ids


def _reviewed_candidate_ids_from_details(
    review_event_details: Iterable[Mapping[str, Any]],
) -> set[str]:
    candidate_ids: set[str] = set()
    for details in review_event_details:
        for review_key in (
            "content_url_review",
            "content_draft_readiness_review",
        ):
            review = details.get(review_key)
            if not isinstance(review, Mapping):
                continue
            candidate_id = review.get("candidate")
            if isinstance(candidate_id, str) and candidate_id:
                candidate_ids.add(candidate_id)
    return candidate_ids


def _reviewed_candidate_url_reviews(
    review_event_summaries: Iterable[str],
) -> dict[str, dict[str, str]]:
    url_reviews: dict[str, dict[str, str]] = {}
    for summary in review_event_summaries:
        candidate_id = _review_summary_token(summary, "candidate")
        if not candidate_id:
            continue
        outcome = _review_summary_token(summary, "url_review_outcome")
        reviewed_url = _review_summary_token(summary, "reviewed_url")
        notes = _review_summary_token(summary, "review_notes")
        if outcome or reviewed_url or notes:
            url_reviews[candidate_id] = {
                "url_review_outcome": outcome,
                "reviewed_url": reviewed_url,
                "review_notes": notes,
            }
    return url_reviews


def _reviewed_candidate_url_reviews_from_details(
    review_event_details: Iterable[Mapping[str, Any]],
) -> dict[str, dict[str, str]]:
    url_reviews: dict[str, dict[str, str]] = {}
    for details in review_event_details:
        url_review = details.get("content_url_review")
        if not isinstance(url_review, Mapping):
            continue
        candidate_id = url_review.get("candidate")
        if not isinstance(candidate_id, str) or not candidate_id:
            continue
        url_reviews[candidate_id] = {
            "url_review_outcome": str(url_review.get("url_review_outcome") or ""),
            "reviewed_url": str(url_review.get("reviewed_url") or ""),
            "review_notes": str(url_review.get("review_notes") or ""),
        }
    return url_reviews


def _reviewed_candidate_draft_readiness_from_details(
    review_event_details: Iterable[Mapping[str, Any]],
) -> dict[str, dict[str, str]]:
    draft_reviews: dict[str, dict[str, str]] = {}
    for details in review_event_details:
        review = details.get("content_draft_readiness_review")
        if not isinstance(review, Mapping):
            continue
        candidate_id = review.get("candidate")
        if not isinstance(candidate_id, str) or not candidate_id:
            continue
        draft_reviews[candidate_id] = {
            "draft_readiness_outcome": str(review.get("draft_readiness_outcome") or ""),
            "canonical_review_outcome": str(review.get("canonical_review_outcome") or ""),
            "duplicate_review_outcome": str(review.get("duplicate_review_outcome") or ""),
            "legal_factual_review_outcome": str(review.get("legal_factual_review_outcome") or ""),
            "human_review_outcome": str(review.get("human_review_outcome") or ""),
            "draft_readiness_notes": str(review.get("draft_readiness_notes") or ""),
        }
    return draft_reviews


def _review_summary_token(summary: str, key: str) -> str:
    marker = f"{key}:"
    if marker not in summary:
        return ""
    fragment = summary.split(marker, 1)[1]
    return fragment.split(",", 1)[0].split(".", 1)[0].strip()


def _draft_readiness_review_contract() -> dict[str, Any]:
    return {
        "contract_version": "content_draft_readiness_review_v1",
        "scope": "review_only",
        "allowed_outcomes": [
            "approve_outline_for_editorial_review",
            "needs_canonical_fix",
            "needs_duplicate_resolution",
            "needs_legal_review",
            "reject_until_source_evidence",
        ],
        "required_fields": [
            "candidate_id",
            "canonical_review_outcome",
            "duplicate_review_outcome",
            "legal_factual_review_outcome",
            "human_review_outcome",
            "reviewed_by",
            "notes",
        ],
        "blocked_outputs": [
            "wordpress_draft_write",
            "wordpress_publish",
            "publish_ready_claim",
            "duplicate_free_claim_without_review",
            "legal_compliance_guarantee",
            "obietnica wzrostu pozycji albo leadów",
        ],
    }


def _content_gate_status_summary(
    *,
    inventory_gate_status: str | None,
    canonical_gate_status: str | None,
    duplicate_gate_status: str | None,
    content_gate_summary: str | None,
) -> list[str]:
    values = [
        f"spis treści: {_content_contract_label(inventory_gate_status)}"
        if inventory_gate_status
        else "",
        f"URL kanoniczny: {_content_contract_label(canonical_gate_status)}"
        if canonical_gate_status
        else "",
        f"duplikaty: {_content_contract_label(duplicate_gate_status)}"
        if duplicate_gate_status
        else "",
        content_gate_summary or "",
    ]
    return [value for value in values if value.strip()]


def _draft_readiness_review_contract_summary(contract: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    scope = contract.get("scope")
    if isinstance(scope, str) and scope:
        values.append(f"zakres: {_content_contract_label(scope)}")
    values.extend(_prefixed_labels("wynik", _string_list(contract.get("allowed_outcomes"))[:3]))
    required_fields = [
        value for value in _string_list(contract.get("required_fields")) if value != "candidate_id"
    ]
    values.extend(_prefixed_labels("wymaga", required_fields[:4]))
    values.extend(_prefixed_labels("blokuje", _string_list(contract.get("blocked_outputs"))[:4]))
    return values


def _draft_readiness_review_summary(review: Mapping[str, Any]) -> list[str]:
    values = [
        ("szkic", review.get("draft_readiness_outcome")),
        ("kanoniczny URL", review.get("canonical_review_outcome")),
        ("duplikaty", review.get("duplicate_review_outcome")),
        ("legal/fakty", review.get("legal_factual_review_outcome")),
        ("człowiek", review.get("human_review_outcome")),
    ]
    return [
        f"{prefix}: {_content_contract_label(value)}"
        for prefix, value in values
        if isinstance(value, str) and value
    ]


def _content_gate_status_for_brief(
    *,
    source_type: str,
    mode: str,
    wordpress_match: bool,
) -> dict[str, str]:
    if source_type == "gsc_query_page" and mode == "refresh" and wordpress_match:
        return _content_gate_status_payload(
            inventory_gate_status="confirmed_current_inventory",
            canonical_gate_status="public_canonical_confirmed",
            duplicate_gate_status="existing_public_content_requires_refresh_or_merge",
            content_gate_summary=(
                "Spis treści potwierdza istniejący URL. WILQ traktuje to jako "
                "odświeżenie albo scalenie, nie nowy artykuł; nowa treść pozostaje "
                "zablokowana przed kontrolą duplikacji."
            ),
        )
    if source_type == "gsc_query_page":
        return _content_gate_status_payload(
            inventory_gate_status="missing_inventory_match",
            canonical_gate_status="blocked_until_inventory_review",
            duplicate_gate_status="create_blocked_until_duplicate_check",
            content_gate_summary=(
                "GSC pokazuje popyt, ale WordPress nie potwierdza URL. Plan nowej treści "
                "jest zablokowany do czasu kontroli spisu, adresu kanonicznego i duplikatów."
            ),
        )
    return _content_gate_status_payload(
        inventory_gate_status="not_applicable",
        canonical_gate_status="blocked_until_relevance_review",
        duplicate_gate_status="manual_merge_or_create_review",
        content_gate_summary=(
            "To jest propozycja z Ahrefs do sprawdzenia, nie decyzja create. Najpierw "
            "potwierdź popyt GSC, inventory WordPress i duplikaty."
        ),
    )


def _content_gate_status_payload(
    *,
    inventory_gate_status: str,
    canonical_gate_status: str,
    duplicate_gate_status: str,
    content_gate_summary: str,
) -> dict[str, str]:
    return {
        "inventory_gate_status": inventory_gate_status,
        "inventory_gate_status_label": _content_contract_label(inventory_gate_status),
        "canonical_gate_status": canonical_gate_status,
        "canonical_gate_status_label": _content_contract_label(canonical_gate_status),
        "duplicate_gate_status": duplicate_gate_status,
        "duplicate_gate_status_label": _content_contract_label(duplicate_gate_status),
        "content_gate_summary": content_gate_summary,
    }
