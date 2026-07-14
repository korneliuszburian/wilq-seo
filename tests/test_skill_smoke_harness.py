from __future__ import annotations

from scripts.skill_smoke_harness import (
    skill_eval_action_state_errors,
    smoke_action_contract,
)


def test_smoke_action_contract_ignores_adjacent_brief_actions() -> None:
    exposed, validated = smoke_action_contract(
        {
            "diagnostics_action_ids": [],
            "action_validations": {},
            "brief_items": [{"action_ids": ["act_prepare_content_refresh_queue"]}],
        }
    )

    assert exposed == set()
    assert validated == set()


def test_smoke_action_contract_requires_explicit_validation_proof() -> None:
    exposed, validated = smoke_action_contract(
        {
            "selected_action_ids": ["act_prepare_content_refresh_queue"],
            "selected_validated_action_ids": ["act_prepare_content_refresh_queue"],
            "action_validations": [
                {
                    "action_id": "act_review_ga4_tracking_quality",
                    "valid": True,
                    "status": "valid",
                },
                {
                    "action_id": "act_review_merchant_feed_issues",
                    "valid": False,
                    "status": "invalid",
                },
            ],
        }
    )

    assert exposed == {
        "act_prepare_content_refresh_queue",
        "act_review_ga4_tracking_quality",
        "act_review_merchant_feed_issues",
    }
    assert validated == {
        "act_prepare_content_refresh_queue",
        "act_review_ga4_tracking_quality",
    }


def test_smoke_action_contract_requires_canonical_valid_status() -> None:
    exposed, validated = smoke_action_contract(
        {
            "action_validations": [
                {
                    "action_id": "act_review_ga4_tracking_quality",
                    "valid": True,
                    "status": "invalid",
                }
            ]
        }
    )

    assert exposed == {"act_review_ga4_tracking_quality"}
    assert validated == set()


def test_skill_eval_blocks_unproved_action_handoffs_unless_fail_closed() -> None:
    pending_errors = skill_eval_action_state_errors(
        [
            {
                "action_id": "act_prepare_content_refresh_queue",
                "validation_state": "pending_validation",
            }
        ],
        smoke_action_ids=set(),
        smoke_validated_action_ids=set(),
    )
    missing_errors = skill_eval_action_state_errors(
        [
            {
                "action_id": "act_prepare_content_refresh_queue",
                "validation_state": "missing",
            }
        ],
        smoke_action_ids=set(),
        smoke_validated_action_ids=set(),
    )

    assert pending_errors == [
        "action candidate 1 uses unproved action_id outside blocked/missing state: "
        "act_prepare_content_refresh_queue"
    ]
    assert missing_errors == []


def test_skill_eval_rejects_malformed_validated_action_without_smoke_proof() -> None:
    errors = skill_eval_action_state_errors(
        [
            {
                "action_id": "hallucinated_action",
                "validation_state": "validated",
            }
        ],
        smoke_action_ids=set(),
        smoke_validated_action_ids=set(),
    )

    assert errors == [
        "action candidate 1 uses unproved action_id outside blocked/missing state: "
        "hallucinated_action",
        "action_id claims validation without deterministic smoke proof: hallucinated_action",
    ]
