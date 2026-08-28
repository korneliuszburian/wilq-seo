from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any, cast

from wilq.content.workflow.keep_eligibility_validation import (
    _EXPECTED_CONNECTORS,
    _SOURCE_KEYS,
    KeepEligibilityError,
    KeepEligibilityInput,
    SourceProvenance,
    _ContextData,
    _JournalData,
    _validate_input,
)

OUTPUT_SCHEMA_VERSION = "content_keep_eligibility_v1"

__all__ = [
    "KeepEligibilityError",
    "KeepEligibilityInput",
    "SourceProvenance",
    "build_keep_eligibility_projection",
]


def build_keep_eligibility_projection(source: KeepEligibilityInput) -> dict[str, Any]:
    """Project one deterministic, read-only decision row for every canonical keep path."""

    validated = _validate_input(source)
    rows = [
        _project_row(
            path=path,
            authoring=validated.authoring[path],
            journal=validated.journal.rows[path],
            ledger=validated.ledger[path],
            catalog=validated.context.catalog_rows[path],
            journal_data=validated.journal,
            context=validated.context,
            provenance=source.provenance,
        )
        for path in sorted(validated.keep_paths)
    ]
    summary = _projection_summary(
        rows,
        source.provenance,
        source.expected_counts,
        source.expected_primary_blocker_counts,
    )
    return {
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "as_of": validated.context.capture_completed_at,
        "read_only": True,
        "safety": {
            "generation_performed": False,
            "target_context_capture_performed": False,
            "vendor_read_performed": False,
            "vendor_write": False,
        },
        "summary": summary,
        "rows": rows,
    }


def _project_row(
    *,
    path: str,
    authoring: Mapping[str, Any],
    journal: Mapping[str, Any],
    ledger: Mapping[str, Any],
    catalog: Mapping[str, Any],
    journal_data: _JournalData,
    context: _ContextData,
    provenance: Mapping[str, SourceProvenance],
) -> dict[str, Any]:
    identity = _work_identity(journal, catalog)
    existing = {
        "verified_keep_draft": path in journal_data.verified_draft_paths,
        "applied_external_write_attempted_bound_action": path in journal_data.applied_action_paths,
    }
    existing["present"] = any(existing.values())
    service = _service_binding(path, journal, context)
    revision = _revision_facts(journal)
    target = _target_context_facts(journal.get("target_mapping_status"))
    connectors = _connector_context(journal, context.connector_evidence)
    resolved_id = identity["resolved_work_item_id"]
    ledger_work_ids = list(cast(list[str], ledger["work_item_ids"]))
    source_pack_bound = resolved_id is not None and resolved_id in ledger_work_ids
    blockers = _hard_blockers(
        existing=bool(existing["present"]),
        identity_status=str(identity["status"]),
        source_pack_bound=source_pack_bound,
        service_status=str(service["status"]),
        revision=revision,
        target=target,
        connectors=connectors,
    )
    eligible = not blockers
    return {
        "path": path,
        "public_url": ledger["public_url"],
        "final_disposition": "keep",
        "canonical_lineage": {
            "ledger_source_ref": provenance["canonical_ledger"].source_ref,
            "lineage_status": ledger["lineage_status"],
            "evidence": [{"evidence_id": value} for value in ledger["evidence_ids"]],
            "source_pack_id": ledger["source_pack_id"],
            "source_pack_verification_ref": journal_data.source_pack_verification_ref,
            "source_pack_work_item_ids": ledger_work_ids,
            "source_pack_work_item_binding_verified": source_pack_bound,
            "path_join_is_work_item_id_proof": False,
        },
        "authoring_target": {
            "rest_object_observed": True,
            "object_id": authoring["object_id"],
            "endpoint": authoring["endpoint"],
            "authoring_mode": authoring["authoring_mode"],
            "raw_values_retained": False,
        },
        "work_item_identity": identity,
        "existing_generation_identity": existing,
        "service_binding": service,
        "revision": revision,
        "target_context": target,
        "connector_context": connectors,
        "keyword_planner": {
            "status": journal["keyword_planner_status"],
            "factual_signal_only": True,
            "hard_eligibility_gate": False,
        },
        "hard_blockers": blockers,
        "primary_blocker": blockers[0] if blockers else None,
        "planning_eligible": eligible,
        "new_generation_allowed": eligible,
        "publish_allowed": False,
        "write_authorized": False,
        "robot_ready": False,
    }


def _work_identity(
    journal: Mapping[str, Any],
    catalog: Mapping[str, Any],
) -> dict[str, Any]:
    retained = journal.get("planning_probe_work_item_id")
    current = catalog.get("current_work_item_id")
    exact_equal = retained is not None and current is not None and retained == current
    if exact_equal:
        status, resolved = "exact_id", current
    elif retained is not None and current is not None:
        status, resolved = "fork", None
    elif current is not None:
        status, resolved = "retained_missing", None
    else:
        status, resolved = "missing", None
    return {
        "retained_journal_work_item_id": retained,
        "current_catalog_work_item_id": current,
        "exact_ids_equal": exact_equal,
        "status": status,
        "resolved_work_item_id": resolved,
        "reconciliation_evidence_id": None,
        "join_basis": "exact_normalized_path",
    }


def _service_binding(
    path: str, journal: Mapping[str, Any], context: _ContextData
) -> dict[str, Any]:
    matches = context.bindings_by_path.get(path, ())
    card: Mapping[str, Any] | None = None
    status = "missing"
    if len(matches) > 1:
        status = "ambiguous"
    elif len(matches) == 1:
        card = context.service_cards[str(matches[0]["service_card_id"])]
        evidence = _validated_string_values(card.get("evidence_ids"))
        connectors = _validated_string_values(card.get("source_connectors"))
        freshness = card.get("freshness")
        normalized_freshness = freshness.strip().casefold() if isinstance(freshness, str) else ""
        provenance_ok = bool(evidence and connectors and normalized_freshness) and not (
            normalized_freshness.startswith(("stale", "rejected"))
        )
        if not provenance_ok:
            status = "provenance_unverified"
        elif card.get("lifecycle_status") != "approved_current":
            status = "lifecycle_unapproved"
        else:
            status = "verified"
    return {
        "status": status,
        "match_basis": "current_code_exact_public_url_only",
        "service_card_id": None if card is None else card["card_id"],
        "lifecycle_status": None if card is None else card["lifecycle_status"],
        "freshness": None if card is None else card["freshness"],
        "evidence_ids": [] if card is None else _validated_string_values(card.get("evidence_ids")),
        "source_connectors": (
            [] if card is None else _validated_string_values(card.get("source_connectors"))
        ),
        "journal_planning_service_card_id": journal.get("planning_service_card_id"),
        "journal_id_predates_exact_binding_commit": True,
        "journal_id_used_as_binding_proof": False,
    }


def _revision_facts(journal: Mapping[str, Any]) -> dict[str, Any]:
    revision_id = journal.get("current_revision_id")
    status = journal.get("current_revision_status")
    return {
        "revision_id": revision_id,
        "current_revision_digest": journal.get("current_revision_digest"),
        "status": status,
        "complete": revision_id is not None,
        "approved": status == "approved",
    }


def _target_context_facts(
    historical_target_status: Any,
) -> dict[str, Any]:
    return {
        "typed_context_present": False,
        "validation_status": "absent",
        "historical_journal_target_status": historical_target_status,
        "historical_status_used_as_current_context": False,
    }


def _connector_context(
    journal: Mapping[str, Any], evidence_index: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    evidence = cast(Mapping[str, Any], journal["connector_evidence"])
    resolved: list[str] = []
    valid = True
    for key, expected_connector in _EXPECTED_CONNECTORS.items():
        evidence_id = str(evidence[key])
        item = evidence_index.get(evidence_id)
        if (
            item is None
            or item.get("connector") != expected_connector
            or item.get("freshness_state") != "fresh"
        ):
            valid = False
        else:
            resolved.append(evidence_id)
    return {
        "evidence_ids": sorted(str(value) for value in evidence.values()),
        "all_resolved_fresh": valid and len(resolved) == len(_EXPECTED_CONNECTORS),
        "repeated_batch_context_only": True,
        "page_performance_membership_verified": False,
    }


def _hard_blockers(
    *,
    existing: bool,
    identity_status: str,
    source_pack_bound: bool,
    service_status: str,
    revision: Mapping[str, Any],
    target: Mapping[str, Any],
    connectors: Mapping[str, Any],
) -> list[str]:
    conditions = (
        (existing, "existing_verified_draft_or_applied_action"),
        (identity_status == "fork", "work_item_identity_fork"),
        (identity_status == "retained_missing", "retained_work_item_missing"),
        (identity_status == "missing", "work_item_identity_missing"),
        (not source_pack_bound, "source_pack_work_item_binding_unverified"),
        (service_status != "verified", f"service_binding_{service_status}"),
        (not revision["complete"], "current_revision_missing"),
        (revision["complete"] and not revision["approved"], "current_revision_not_approved"),
        (target["validation_status"] == "absent", "typed_target_context_absent"),
        (target["validation_status"] == "invalid", "typed_target_context_invalid"),
        (not connectors["all_resolved_fresh"], "connector_evidence_unresolved_or_stale"),
    )
    return [code for applies, code in conditions if applies]


def _projection_summary(
    rows: Sequence[Mapping[str, Any]],
    provenance: Mapping[str, SourceProvenance],
    expected_counts: Sequence[tuple[str, int]],
    expected_primary_blockers: Sequence[tuple[str, int]],
) -> dict[str, Any]:
    identities = [row["work_item_identity"] for row in rows]
    counts = {
        "keep_count": len(rows),
        "exact_authoring_target_count": len(rows),
        "retained_work_item_count": sum(
            item["retained_journal_work_item_id"] is not None for item in identities
        ),
        "current_work_item_count": sum(
            item["current_catalog_work_item_id"] is not None for item in identities
        ),
        "joined_work_item_count": sum(
            item["retained_journal_work_item_id"] is not None
            and item["current_catalog_work_item_id"] is not None
            for item in identities
        ),
        "exact_work_item_id_equal_count": sum(item["exact_ids_equal"] for item in identities),
        "reconciled_work_item_count": sum(item["status"] == "reconciled" for item in identities),
        "current_revision_count": sum(row["revision"]["complete"] for row in rows),
        "exact_service_binding_count": sum(
            row["service_binding"]["status"] == "verified" for row in rows
        ),
        "source_pack_work_item_binding_count": sum(
            row["canonical_lineage"]["source_pack_work_item_binding_verified"] for row in rows
        ),
        "existing_generation_identity_count": sum(
            row["existing_generation_identity"]["present"] for row in rows
        ),
        "typed_target_context_count": sum(
            row["target_context"]["typed_context_present"] for row in rows
        ),
        "eligible_count": sum(row["planning_eligible"] for row in rows),
    }
    blocker_counts = dict(
        sorted(
            Counter(
                str(row["primary_blocker"]) for row in rows if row["primary_blocker"] is not None
            ).items()
        )
    )
    for field, expected in expected_counts:
        _require_equal(f"projection {field}", counts.get(field), expected)
    _require_equal(
        "projection primary blocker partition",
        blocker_counts,
        dict(expected_primary_blockers),
    )
    return {
        **counts,
        "primary_blocker_counts": blocker_counts,
        "source_refs": {key: provenance[key].source_ref for key in _SOURCE_KEYS},
        "source_sha256": {key: provenance[key].sha256 for key in _SOURCE_KEYS},
    }


def _is_trimmed_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()


def _validated_string_values(value: Any) -> list[str]:
    if not isinstance(value, list) or any(not _is_trimmed_text(item) for item in value):
        return []
    if len(value) != len(set(value)):
        return []
    return value


def _require_equal(context: str, observed: Any, expected: Any) -> None:
    if observed != expected:
        raise KeepEligibilityError(f"{context} does not match the required contract.")
