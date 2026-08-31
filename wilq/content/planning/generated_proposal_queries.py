PROPOSAL_INPUT_SELECTS = {
    "content_planning_proposals": """
        SELECT payload_json, proposal_version, work_item_id, service_card_id,
               content_kind, subject_key, planning_input_digest
        FROM content_planning_proposals
        WHERE work_item_id = ? AND content_kind = ? AND subject_key = ?
          AND planning_input_digest = ?
    """,
    "content_planning_proposal_repairs": """
        SELECT payload_json, proposal_version, work_item_id, service_card_id,
               content_kind, subject_key, planning_input_digest
        FROM content_planning_proposal_repairs
        WHERE work_item_id = ? AND content_kind = ? AND subject_key = ?
          AND planning_input_digest = ?
    """,
}
PROPOSAL_LATEST_SELECTS = {
    "content_planning_proposals": (
        "SELECT payload_json, proposal_version, work_item_id, service_card_id, "
        "content_kind, subject_key, planning_input_digest "
        "FROM content_planning_proposals WHERE "
    ),
    "content_planning_proposal_repairs": (
        "SELECT payload_json, proposal_version, work_item_id, service_card_id, "
        "content_kind, subject_key, planning_input_digest "
        "FROM content_planning_proposal_repairs WHERE "
    ),
}
PROPOSAL_PLANNING_DIGEST_SELECTS = {
    "content_planning_proposals": """
        SELECT payload_json, proposal_version, work_item_id, service_card_id,
               content_kind, subject_key, planning_input_digest
        FROM content_planning_proposals
        WHERE work_item_id = ?
          AND json_extract(payload_json, '$.planning_digest') = ?
    """,
    "content_planning_proposal_repairs": """
        SELECT payload_json, proposal_version, work_item_id, service_card_id,
               content_kind, subject_key, planning_input_digest
        FROM content_planning_proposal_repairs
        WHERE work_item_id = ?
          AND json_extract(payload_json, '$.planning_digest') = ?
    """,
}

__all__ = [
    "PROPOSAL_INPUT_SELECTS",
    "PROPOSAL_LATEST_SELECTS",
    "PROPOSAL_PLANNING_DIGEST_SELECTS",
]
