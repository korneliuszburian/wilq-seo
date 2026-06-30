from __future__ import annotations

from typing import TypedDict


class ContentInventoryGateStatus(TypedDict):
    inventory_gate_status: str
    canonical_gate_status: str
    duplicate_gate_status: str
    content_gate_summary: str


def content_inventory_gate_status(
    *,
    decision_type: str,
    wordpress_match: str,
) -> ContentInventoryGateStatus:
    if decision_type == "refresh_or_merge" and wordpress_match == "found":
        return {
            "inventory_gate_status": "confirmed_current_inventory",
            "canonical_gate_status": "public_canonical_confirmed",
            "duplicate_gate_status": "existing_public_content_requires_refresh_or_merge",
            "content_gate_summary": (
                "Spis treści potwierdza istniejący URL. WILQ traktuje to jako "
                "odświeżenie albo scalenie, nie nowy artykuł; nowa treść pozostaje zablokowana "
                "przed kontrolą duplikacji."
            ),
        }
    if decision_type == "merge_create_after_inventory_check":
        return {
            "inventory_gate_status": "missing_inventory_match",
            "canonical_gate_status": "blocked_until_content_url_review",
            "duplicate_gate_status": "manual_merge_or_create_review",
            "content_gate_summary": (
                "GSC pokazuje klaster zapytań bez potwierdzonego inventory. "
                "Najpierw potrzebna kontrola URL i duplikatów; dopiero potem "
                "scalenie albo nowa treść."
            ),
        }
    if decision_type == "inventory_check_before_create":
        return {
            "inventory_gate_status": "missing_inventory_match",
            "canonical_gate_status": "blocked_until_inventory_review",
            "duplicate_gate_status": "create_blocked_until_duplicate_check",
            "content_gate_summary": (
                "GSC pokazuje popyt, ale WordPress nie potwierdza URL. "
                "Plan nowej treści jest zablokowany do czasu kontroli spisu, adresu kanonicznego "
                "i duplikatów."
            ),
        }
    return {
        "inventory_gate_status": "not_applicable",
        "canonical_gate_status": "not_applicable",
        "duplicate_gate_status": "not_applicable",
        "content_gate_summary": (
            "Ta decyzja nie jest bezpośrednim planem treści; wymaga osobnego "
            "sprawdzenia przed użyciem w planie treści."
        ),
    }
