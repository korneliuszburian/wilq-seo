from __future__ import annotations

import pytest

from wilq.content.planning.generated_proposal_contracts import ContentPlanningModelOutput


def test_planning_model_output_enforces_compactness_caps_at_validation_boundary() -> None:
    base = {
        "language": "pl-PL",
        "service_card_id": "ekologus_service_bdo_reporting",
        "target_reader": "przedsiębiorca",
        "buyer_problem": "Nie wie, co sprawdzić.",
        "buyer_trigger": "Przed przygotowaniem obowiązków.",
        "search_intent": "informational",
        "angle": "Praktyczny przewodnik",
        "value_proposition": "Porządkuje pierwszy krok.",
        "sections": [
            {
                "heading": "Sekcja 1",
                "purpose": "Odpowiedzieć.",
                "reader_question": "Co sprawdzić?",
                "inventory_disposition": "create",
                "evidence_ids": ["ev_planning"],
            }
        ],
        "measurement_plan": {
            "observation_rule": "Porównaj ten sam okres po zmianie.",
            "success_claim_rule": "Nie twierdź o efekcie bez porównania.",
        },
        "publish_ready": False,
    }
    over_limit = {
        "sections": 12,
        "faq": 8,
        "cta_blocks": 4,
        "conditional_hypotheses": 4,
    }

    for field, limit in over_limit.items():
        payload = dict(base)
        if field == "sections":
            payload[field] = [
                {
                    "heading": f"Sekcja {index}",
                    "purpose": "Odpowiedzieć.",
                    "reader_question": "Co sprawdzić?",
                    "inventory_disposition": "create",
                    "evidence_ids": ["ev_planning"],
                }
                for index in range(limit + 1)
            ]
        elif field == "faq":
            payload[field] = [
                {
                    "question": f"Pytanie {index}?",
                    "purpose": "Wyjaśnić.",
                    "evidence_ids": ["ev_planning"],
                }
                for index in range(limit + 1)
            ]
        elif field == "cta_blocks":
            payload[field] = [
                {
                    "placement": "after_lead",
                    "purpose": "Skierować do kontaktu.",
                    "copy_direction": "Opisz sytuację.",
                    "evidence_ids": ["ev_planning"],
                }
                for _ in range(limit + 1)
            ]
        else:
            payload[field] = [
                {
                    "channel": "social",
                    "hypothesis": "Sprawdzić ponowne użycie.",
                    "evidence_ids": ["ev_planning"],
                    "review_required": True,
                }
                for _ in range(limit + 1)
            ]

        with pytest.raises(ValueError, match=field):
            ContentPlanningModelOutput.model_validate(payload)


def test_planning_model_output_rejects_placement_after_removed_section() -> None:
    payload = {
        "language": "pl-PL",
        "service_card_id": "ekologus_service_bdo_reporting",
        "target_reader": "przedsiębiorca",
        "buyer_problem": "Nie wie, co sprawdzić.",
        "buyer_trigger": "Przed przygotowaniem obowiązków.",
        "search_intent": "informational",
        "angle": "Praktyczny przewodnik",
        "value_proposition": "Porządkuje pierwszy krok.",
        "page_assets": {
            "title": "Tytuł",
            "h1": "Nagłówek",
            "lead": "Lead.",
            "meta_title": "Meta title",
            "meta_description": "Meta description.",
        },
        "sections": [
            {
                "heading": "Sekcja do usunięcia",
                "purpose": "Oznaczyć element do osobnego review.",
                "reader_question": "Czy ta sekcja zostaje?",
                "inventory_disposition": "remove_review_required",
                "evidence_ids": ["ev_planning"],
            },
            {
                "heading": "Sekcja zachowana",
                "purpose": "Odpowiedzieć.",
                "reader_question": "Co sprawdzić?",
                "inventory_disposition": "preserve",
                "evidence_ids": ["ev_planning"],
            },
        ],
        "cta_blocks": [
            {
                "placement": "Sekcja do usunięcia",
                "purpose": "Skierować do kontaktu.",
                "copy_direction": "Opisz sytuację.",
                "evidence_ids": ["ev_planning"],
            }
        ],
        "measurement_plan": {
            "observation_rule": "Porównaj ten sam okres po zmianie.",
            "success_claim_rule": "Nie twierdź o efekcie bez porównania.",
        },
        "publish_ready": False,
    }

    with pytest.raises(ValueError, match="remove_review_required"):
        ContentPlanningModelOutput.model_validate(payload)
