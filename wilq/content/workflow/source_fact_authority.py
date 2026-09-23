"""Public interface for exact, ActionObject-owned source-fact authority."""

from typing import Any

from wilq.content.workflow._source_fact_authority_contracts import (
    SOURCE_FACT_AUTHORITY_ACTION_TYPE,
    SOURCE_FACT_AUTHORITY_MUTATION_ADAPTER,
    SOURCE_FACT_AUTHORITY_PREVIEW_CONTRACT,
    SOURCE_FACT_AUTHORITY_PROPOSAL_SCHEMA,
    SOURCE_FACT_AUTHORITY_RECEIPT_SCHEMA,
    SOURCE_FACT_AUTHORITY_RECORDED_EVENT,
    ContentSourceFactAuthorityApplyResult,
    ContentSourceFactAuthorityBlocker,
    ContentSourceFactAuthorityCandidate,
    ContentSourceFactAuthorityCandidateProjection,
    ContentSourceFactAuthorityPreviewCommand,
    ContentSourceFactAuthorityPreviewResponse,
    ContentSourceFactAuthorityProposal,
    ContentSourceFactAuthorityReadProjection,
    ContentSourceFactAuthorityReceipt,
    ContentSourceFactAuthorityRegistryReceipt,
    ContentSourceFactAuthorityServiceBinding,
    ContentSourceFactAuthoritySnapshot,
    ContentSourceFactProvenance,
    authority_evidence_ids_digest,
    authority_source_fact_digest,
    authority_source_fact_evidence_digest,
    authority_source_fact_ids_digest,
    authority_source_fact_provenance,
    authority_source_fact_provenance_digest,
    authority_source_fact_reference_digest,
    parse_source_fact_authority_snapshot_json,
    source_fact_authority_action_id,
    source_fact_authority_action_payload_digest,
    source_fact_authority_proposal_digest,
    source_fact_authority_receipt_digest,
    source_fact_authority_snapshot_digest,
)
from wilq.content.workflow._source_fact_authority_runtime import (
    build_content_source_fact_authority_candidate_projection,
    build_source_fact_authority_action,
    build_source_fact_authority_snapshot,
    load_content_source_fact_authority_action,
    prepare_content_source_fact_authority_preview,
    read_content_source_fact_authority,
    source_fact_authority_action_for_proposal,
    validate_source_fact_authority_action_payload,
)
from wilq.content.workflow._source_fact_authority_runtime import (
    execute_content_source_fact_authority as _execute_content_source_fact_authority_v1,
)
from wilq.schemas import ActionObject, AuditEvent


def execute_content_source_fact_authority(
    action: ActionObject,
    *,
    store: Any,
    audit_events: list[AuditEvent],
) -> tuple[dict[str, Any] | None, list[str]]:
    """Dispatch the shared local source-fact adapter to its typed authority version."""
    if action.payload.get("action_type") == "content_source_fact_authority_v2":
        from wilq.content.workflow.source_fact_authority_v2 import (
            execute_source_fact_authority_v2,
        )

        return execute_source_fact_authority_v2(
            action,
            store=store,
            audit_events=audit_events,
        )
    return _execute_content_source_fact_authority_v1(
        action,
        store=store,
        audit_events=audit_events,
    )


__all__ = [
    "SOURCE_FACT_AUTHORITY_ACTION_TYPE",
    "SOURCE_FACT_AUTHORITY_MUTATION_ADAPTER",
    "SOURCE_FACT_AUTHORITY_PREVIEW_CONTRACT",
    "SOURCE_FACT_AUTHORITY_PROPOSAL_SCHEMA",
    "SOURCE_FACT_AUTHORITY_RECEIPT_SCHEMA",
    "SOURCE_FACT_AUTHORITY_RECORDED_EVENT",
    "ContentSourceFactAuthorityApplyResult",
    "ContentSourceFactAuthorityBlocker",
    "ContentSourceFactAuthorityCandidate",
    "ContentSourceFactAuthorityCandidateProjection",
    "ContentSourceFactAuthorityPreviewCommand",
    "ContentSourceFactAuthorityPreviewResponse",
    "ContentSourceFactAuthorityProposal",
    "ContentSourceFactAuthorityReadProjection",
    "ContentSourceFactAuthorityReceipt",
    "ContentSourceFactAuthorityRegistryReceipt",
    "ContentSourceFactAuthorityServiceBinding",
    "ContentSourceFactAuthoritySnapshot",
    "ContentSourceFactProvenance",
    "authority_evidence_ids_digest",
    "authority_source_fact_digest",
    "authority_source_fact_evidence_digest",
    "authority_source_fact_ids_digest",
    "authority_source_fact_provenance",
    "authority_source_fact_provenance_digest",
    "authority_source_fact_reference_digest",
    "build_source_fact_authority_action",
    "build_content_source_fact_authority_candidate_projection",
    "build_source_fact_authority_snapshot",
    "execute_content_source_fact_authority",
    "load_content_source_fact_authority_action",
    "prepare_content_source_fact_authority_preview",
    "read_content_source_fact_authority",
    "source_fact_authority_action_for_proposal",
    "source_fact_authority_action_id",
    "source_fact_authority_action_payload_digest",
    "source_fact_authority_proposal_digest",
    "source_fact_authority_receipt_digest",
    "source_fact_authority_snapshot_digest",
    "parse_source_fact_authority_snapshot_json",
    "validate_source_fact_authority_action_payload",
]
