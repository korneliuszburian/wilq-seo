from __future__ import annotations

from scripts.context_pack_language_guard import (
    FORBIDDEN_VALUE_TERMS,
    _context_pack_structure_errors,
    _walk_string_values,
)


def test_context_pack_guard_tracks_action_and_url_jargon() -> None:
    required_terms = {
        "ActionObject",
        "Dry-run",
        "dry-run",
        "No evidence ID",
        "must not invent metrics",
        "ID dowodu",
        "source_public_url",
        "final_canonical_url",
        "intended_final_url",
        "preview_url",
        "target site",
        "mapping-review",
        "blockers",
    }

    assert required_terms.issubset(set(FORBIDDEN_VALUE_TERMS))


def test_context_pack_guard_scans_nested_string_values() -> None:
    payload = {
        "context": {
            "decision": [
                {"visible": "ActionObject payload should never reach skill context"}
            ]
        }
    }

    hits = [
        (path, term)
        for path, value in _walk_string_values(payload)
        for term in FORBIDDEN_VALUE_TERMS
        if term in value
    ]

    assert ("$.context.decision[0].visible", "ActionObject") in hits
    assert ("$.context.decision[0].visible", "payload") in hits


def test_context_pack_guard_blocks_top_level_action_payload_key() -> None:
    payload = {
        "active_action_objects": [
            {"id": "act_bad", "payload": {"preview": []}},
            {"id": "act_good", "action_plan": {"preview": []}},
        ],
        "technical_detail": {"payload": {"allowed_outside_skill_actions": True}},
    }

    assert _context_pack_structure_errors(payload) == [
        (
            "$.active_action_objects[0].payload",
            "action_payload_key",
            "Use action_plan in skill context packs; keep payload on action detail endpoints.",
        )
    ]


def test_context_pack_guard_blocks_raw_contract_and_review_gate_keys() -> None:
    payload = {
        "active_action_objects": [
            {
                "id": "act_bad",
                "action_plan": {
                    "allowed_contracts": ["localo_rankings"],
                    "available_read_contracts": ["demand_gen_campaign_rows"],
                    "operator_review_gates": ["human_review"],
                },
            }
        ]
    }

    assert _context_pack_structure_errors(payload) == [
        (
            "$.active_action_objects[0].action_plan.allowed_contracts",
            "technical_action_plan_key",
            "Use marketer-readable compact action plan keys instead of allowed_contracts.",
        ),
        (
            "$.active_action_objects[0].action_plan.available_read_contracts",
            "technical_action_plan_key",
            "Use marketer-readable compact action plan keys instead of available_read_contracts.",
        ),
        (
            "$.active_action_objects[0].action_plan.operator_review_gates",
            "technical_action_plan_key",
            "Use marketer-readable compact action plan keys instead of operator_review_gates.",
        ),
    ]


def test_context_pack_guard_blocks_raw_content_status_keys() -> None:
    payload = {
        "active_action_objects": [
            {
                "id": "act_bad",
                "action_plan": {
                    "content_plan_items": [
                        {
                            "source_type": "gsc_query_page",
                            "publication_readiness_status": "blocked_until_review",
                            "publication_blockers": ["canonical_review"],
                            "forbidden_claims": ["ranking_guarantee"],
                        }
                    ]
                },
            }
        ]
    }

    assert _context_pack_structure_errors(payload) == [
        (
            "$.active_action_objects[0].action_plan.content_plan_items[0].source_type",
            "technical_action_plan_key",
            "Use marketer-readable compact action plan keys instead of source_type.",
        ),
        (
            "$.active_action_objects[0].action_plan.content_plan_items[0].publication_readiness_status",
            "technical_action_plan_key",
            (
                "Use marketer-readable compact action plan keys instead of "
                "publication_readiness_status."
            ),
        ),
        (
            "$.active_action_objects[0].action_plan.content_plan_items[0].publication_blockers",
            "technical_action_plan_key",
            "Use marketer-readable compact action plan keys instead of publication_blockers.",
        ),
        (
            "$.active_action_objects[0].action_plan.content_plan_items[0].forbidden_claims",
            "technical_action_plan_key",
            "Use marketer-readable compact action plan keys instead of forbidden_claims.",
        ),
    ]


def test_context_pack_guard_blocks_required_mapping_key() -> None:
    payload = {
        "expert_capabilities": [
            {"id": "cap_bad", "required_mapping": []},
            {"id": "cap_good", "required_inputs": []},
        ],
    }

    assert _context_pack_structure_errors(payload) == [
        (
            "$.expert_capabilities[0].required_mapping",
            "required_mapping_key",
            "Use required_inputs in compact skill context packs.",
        )
    ]
