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

V3_PLAN_GENERATION_LINKAGE_SELECT = """
    SELECT job.work_item_id AS job_work_item_id,
           job.service_card_id AS job_service_card_id,
           job.content_kind AS job_content_kind,
           job.subject_key AS job_subject_key,
           job.planning_input_digest AS job_planning_input_digest,
           job.status AS job_status,
           job.payload_json AS job_payload_json,
           frozen.work_item_id AS frozen_work_item_id,
           frozen.service_card_id AS frozen_service_card_id,
           frozen.content_kind AS frozen_content_kind,
           frozen.subject_key AS frozen_subject_key,
           frozen.planning_input_digest AS frozen_planning_input_digest,
           frozen.input_json AS frozen_input_json,
           run.id AS persisted_run_id,
           run.payload_json AS persisted_run_payload_json
    FROM content_planning_generation_jobs AS job
    LEFT JOIN codex_runs AS run ON run.id = ?
    LEFT JOIN content_planning_input_snapshots AS frozen
      ON frozen.work_item_id = job.work_item_id
     AND frozen.planning_input_digest = job.planning_input_digest
    WHERE job.work_item_id = ?
      AND job.content_kind = ?
      AND job.subject_key = ?
      AND job.planning_input_digest = ?
    LIMIT 1
"""

__all__ = [
    "PROPOSAL_INPUT_SELECTS",
    "PROPOSAL_LATEST_SELECTS",
    "PROPOSAL_PLANNING_DIGEST_SELECTS",
    "V3_PLAN_GENERATION_LINKAGE_SELECT",
]
