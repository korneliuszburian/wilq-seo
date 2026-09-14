from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Literal, cast

from wilq.content.workflow.decisions.production import (
    ContentProductionAcceptancePolicy,
    ContentProductionBlockedHistoricalProtectionPolicy,
    ContentProductionClassificationCounts,
    ContentProductionEvidenceDefectPolicy,
    ContentProductionProtectedBindingPolicy,
    ContentProductionSourceReceiptPolicy,
    canonical_json_digest,
)

JsonObject = dict[str, object]
PATHS = ("/bdo-test", "/zablokowane")
REVISION_ID = "content_revision_test"
REVISION_DIGEST = "9" * 64
ACTION_ID = "act_content_dev_draft_test"


@dataclass(frozen=True)
class SyntheticInputs:
    packet: JsonObject
    judge: JsonObject
    packet_bytes: bytes
    judge_bytes: bytes
    policy: ContentProductionAcceptancePolicy


def json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()


def build_inputs() -> SyntheticInputs:
    rows = [_row(PATHS[0], "reuse", 1), _row(PATHS[1], "blocked", 2)]
    blocked = rows[1]
    cast(JsonObject, blocked["evidence"])["lineage_defects"] = [
        {
            "evidence_id": "ev_legacy_invalid",
            "source": "ledger",
            "owner": "owner_test",
            "reason_pl": "Niepełny identyfikator.",
            "next_step_pl": "Napraw lineage.",
            "status": "invalid_unusable",
            "usable_as_decision_proof": False,
        }
    ]
    blocked["typed_blockers"] = [
        {
            "code": "invalid_legacy_evidence_id",
            "owner": "owner_test",
            "next_step_pl": "Napraw lineage przed pracą.",
            "sources": ["ledger"],
            "blocks_initial_generation": True,
        }
    ]
    sources = {
        "matched_classification": _source("matched.json", "a" * 64),
        "unmatched_classification": _source("unmatched.json", "b" * 64),
    }
    packet: JsonObject = {
        "schema_version": "wilq_content_production_classification_v1",
        "base_revision": "1" * 40,
        "generated_at": "2026-08-30T10:00:00Z",
        "row_digest_algorithm": (
            "sha256(canonical_json(source_packet_receipts); UTF-8, sorted keys, compact separators)"
        ),
        "decision_set_digest_algorithm": (
            "sha256(canonical_json(rows); UTF-8, sorted keys, compact separators)"
        ),
        "decision_set_digest": "0" * 64,
        "source_file_receipts": sources,
        "rows": rows,
        "counts": _counts(),
        "wilq_diagnostic_freshness": {
            "state": "fresh",
            "checked_at": "2026-08-30T09:59:00Z",
            "requires_refresh": False,
            "connector_covered_windows": {"gsc": {}, "wordpress": {}},
        },
    }
    return resign(packet)


def build_blocked_historical_protection_inputs() -> SyntheticInputs:
    baseline = build_inputs()
    packet = copy.deepcopy(baseline.packet)
    rows = cast(list[object], packet["rows"])
    blocked = cast(JsonObject, rows[0])
    blocked["decision"] = "blocked"
    blocked["typed_blockers"] = [
        {
            "code": "current_historical_revision_drift",
            "owner": "content_owner_test",
            "next_step_pl": "Wykonaj nową weryfikację rewizji.",
            "sources": ["wordpress_readback"],
            "blocks_initial_generation": True,
        }
    ]
    identity = cast(JsonObject, blocked["work_item_identity"])
    identity["retained_work_item_id"] = None
    blocked["revision"] = {
        "revision_id": None,
        "digest": None,
        "approved": False,
        "complete": False,
    }
    blocked["retained_revision_binding"] = None
    blocked["draft_and_action_state"] = {
        "verified_current_action_bindings": [],
        "verified_current_draft_bindings": [],
    }
    blocked["blocked_historical_protection"] = {
        "historical_revision_id": "content_revision_historical_blocked",
        "historical_revision_digest": "7" * 64,
        "current_verification_outcome": "drifted",
        "current_verification_evidence_id": "ev_current_historical_readback",
        "current_verification_connector": "wordpress",
        "current_verification_checked_at": "2026-08-30T10:02:00Z",
        "must_not_regenerate": True,
    }
    packet["counts"] = {
        **_counts(),
        "reuse": 0,
        "blocked": 2,
        "verified_current_actions": 0,
        "verified_current_drafts": 0,
    }
    policy = baseline.policy.model_copy(
        update={
            "protected_binding": None,
            "blocked_historical_protection": ContentProductionBlockedHistoricalProtectionPolicy(
                canonical_path=PATHS[0],
                historical_revision_id="content_revision_historical_blocked",
                historical_revision_digest="7" * 64,
                current_verification_outcome="drifted",
                current_verification_evidence_id="ev_current_historical_readback",
                current_verification_connector="wordpress",
                current_verification_checked_at="2026-08-30T10:02:00Z",
            ),
            "expected_counts": ContentProductionClassificationCounts(**packet["counts"]),
            "expected_approved_revisions": 0,
        }
    )
    return resign(packet, policy=policy, sync_policy_decision=True)


def build_clean_current_all_blocked_inputs() -> SyntheticInputs:
    baseline = build_blocked_historical_protection_inputs()
    packet = copy.deepcopy(baseline.packet)
    clean = cast(JsonObject, cast(list[object], packet["rows"])[1])
    cast(JsonObject, clean["evidence"])["lineage_defects"] = []
    clean["typed_blockers"] = [
        {
            "code": "current_source_evidence_gap",
            "owner": "content_owner_test",
            "next_step_pl": "Uzupełnij bieżące źródło dowodowe.",
            "sources": ["ledger"],
            "blocks_initial_generation": True,
        }
    ]
    policy = baseline.policy.model_copy(update={"invalid_evidence": None})
    return resign(packet, policy=policy, sync_policy_decision=True)


def build_missing_source_binding_inputs() -> SyntheticInputs:
    baseline = build_inputs()
    packet = copy.deepcopy(baseline.packet)
    missing = cast(JsonObject, cast(list[object], packet["rows"])[1])
    identity = cast(JsonObject, missing["work_item_identity"])
    identity["current_inventory_work_item_id"] = None
    evidence = cast(JsonObject, missing["evidence"])
    evidence.pop("source_pack_id", None)
    missing["source_packet_receipts"] = {
        "binding_state": "missing",
        "missing_sources": ["authoring_inventory_row", "source_pack_binding"],
        "content_status_row_sha256": "c" * 64,
        "wordpress_catalog_scope_sha256": "d" * 64,
        "catalog_lookup_outcome": "exact_path_absent",
    }
    return resign(packet, policy=baseline.policy, sync_policy_decision=True)


def build_present_source_binding_inputs() -> SyntheticInputs:
    baseline = build_missing_source_binding_inputs()
    packet = copy.deepcopy(baseline.packet)
    present = cast(JsonObject, cast(list[object], packet["rows"])[1])
    present["source_packet_receipts"] = {
        "binding_state": "missing",
        "missing_sources": ["delivery_identity_binding", "source_pack_binding"],
        "content_status_row_sha256": "c" * 64,
        "wordpress_catalog_scope_sha256": "d" * 64,
        "catalog_lookup_outcome": "exact_path_present",
    }
    return resign(packet, policy=baseline.policy, sync_policy_decision=True)


def resign(
    packet: JsonObject,
    *,
    policy: ContentProductionAcceptancePolicy | None = None,
    sync_policy_decision: bool = False,
    repair_row_receipts: bool = True,
) -> SyntheticInputs:
    packet = copy.deepcopy(packet)
    rows = cast(list[object], packet["rows"])
    if repair_row_receipts:
        for value in rows:
            row = cast(JsonObject, value)
            row["source_packet_row_digest"] = canonical_json_digest(row["source_packet_receipts"])
    decision_digest = canonical_json_digest(rows)
    packet["decision_set_digest"] = decision_digest
    packet_bytes = json_bytes(packet)
    packet_sha = sha256(packet_bytes).hexdigest()
    judge = _judge(packet_sha, decision_digest, cast(JsonObject, rows[0]))
    judge_bytes = json_bytes(judge)
    updates = {
        "packet_sha256": packet_sha,
        "judge_sha256": sha256(judge_bytes).hexdigest(),
    }
    if sync_policy_decision:
        updates["decision_set_digest"] = decision_digest
    policy = (
        _policy(updates, decision_digest) if policy is None else policy.model_copy(update=updates)
    )
    return SyntheticInputs(packet, judge, packet_bytes, judge_bytes, policy)


def resign_raw(inputs: SyntheticInputs, packet_bytes: bytes) -> SyntheticInputs:
    judge = copy.deepcopy(inputs.judge)
    judge["reviewed_packet_sha256"] = sha256(packet_bytes).hexdigest()
    judge_bytes = json_bytes(judge)
    policy = inputs.policy.model_copy(
        update={
            "packet_sha256": sha256(packet_bytes).hexdigest(),
            "judge_sha256": sha256(judge_bytes).hexdigest(),
        }
    )
    return SyntheticInputs(inputs.packet, judge, packet_bytes, judge_bytes, policy)


def resign_judge(inputs: SyntheticInputs, judge: JsonObject) -> SyntheticInputs:
    judge = copy.deepcopy(judge)
    judge_bytes = json_bytes(judge)
    policy = inputs.policy.model_copy(update={"judge_sha256": sha256(judge_bytes).hexdigest()})
    return SyntheticInputs(
        inputs.packet,
        judge,
        inputs.packet_bytes,
        judge_bytes,
        policy,
    )


def _row(path: str, decision: Literal["reuse", "blocked"], index: int) -> JsonObject:
    reuse = decision == "reuse"
    source = "matched" if reuse else "unmatched"
    url = f"https://www.ekologus.pl{path}/"
    return {
        "path": path,
        "public_url": url,
        "decision": decision,
        "generation_allowed": False,
        "rationale_pl": f"Zażółć gęślą {index}.",
        "next_step_pl": "Sprawdź bezpieczny krok.",
        "typed_blockers": [],
        "work_item_identity": {
            "current_inventory_work_item_id": f"work_current_{index}",
            "retained_work_item_id": "work_retained" if reuse else None,
        },
        "revision": {
            "revision_id": REVISION_ID if reuse else None,
            "digest": REVISION_DIGEST if reuse else None,
            "approved": reuse,
            "complete": reuse,
        },
        "retained_revision_binding": _binding() if reuse else None,
        "draft_and_action_state": (
            _verified_state(url)
            if reuse
            else {
                "verified_current_action_bindings": [],
                "verified_current_draft_bindings": [],
            }
        ),
        "evidence": {
            "evidence_ids": [f"ev_{index}"],
            "source_connectors": ["gsc"],
            "canonical_ledger_evidence_ids": [f"lineage_{index}"],
            "lineage_defects": [],
            "source_pack_id": f"pack_{index}",
        },
        "source_packet_receipts": _row_receipt(index, source),
        "source_packet_row_digest": "0" * 64,
    }


def _binding() -> JsonObject:
    return {
        "binding_basis": "exact_normalized_path_with_retained_revision_state",
        "current_inventory_work_item_id": "work_current_1",
        "retained_work_item_id": "work_retained",
        "retained_revision_id": REVISION_ID,
        "retained_revision_digest": REVISION_DIGEST,
        "identity_reconciliation_status": "fork",
        "verified_draft_action_ids": [ACTION_ID],
        "verified_draft_post_ids": ["1991"],
        "must_not_regenerate": True,
    }


def _verified_state(url: str) -> JsonObject:
    action = {
        "action_id": ACTION_ID,
        "mutation_audit_id": "audit_test",
        "action_type": "content_dev_draft_create",
        "status": "applied",
        "bound_work_item_id": "work_retained",
        "bound_revision_id": REVISION_ID,
        "bound_content_digest": REVISION_DIGEST,
        "bound_final_canonical_url": url,
        "adapter_reached": True,
        "external_write_attempted": True,
    }
    draft = {
        "action_id": ACTION_ID,
        "apply_audit_id": "audit_test",
        "post_id": "1991",
        "revision_id": REVISION_ID,
        "revision_digest": REVISION_DIGEST,
        "readback_content_digest": "8" * 64,
        "state_class": "dev_draft_verified",
        "wordpress_draft_status": "draft",
        "readback_status": "verified",
    }
    return {
        "verified_current_action_bindings": [action],
        "verified_current_draft_bindings": [draft],
    }


def _row_receipt(index: int, source: str) -> JsonObject:
    return {
        "authoring_inventory_row_sha256": f"{index}" * 64,
        "canonical_ledger_row_sha256": f"{index}" * 64,
        "keep_eligibility_row_sha256": f"{index}" * 64,
        "state_journal_url_row_sha256": f"{index}" * 64,
        "classification_source": source,
        "classification_artifact_reference": f"{source}.json",
        "classification_file_sha256": "a" * 64 if source == "matched" else "b" * 64,
        "classification_row_sha256": f"{index}" * 64,
        "classification_raw_artifact_retained": False,
        "classification_retention_status": "external_ephemeral_receipt_only",
        "source_pack_id": f"pack_{index}",
        "bound_mutation_audit_row_sha256": [],
        "draft_row_sha256": [],
    }


def _source(reference: str, digest: str) -> JsonObject:
    return {
        "artifact_reference": reference,
        "sha256": digest,
        "raw_artifact_retained": False,
        "retention_status": "external_ephemeral_receipt_only",
    }


def _counts() -> JsonObject:
    return {
        "rows": 2,
        "reuse": 1,
        "refresh": 0,
        "write": 0,
        "blocked": 1,
        "generation_allowed": 0,
        "verified_current_actions": 1,
        "verified_current_drafts": 1,
    }


def _policy(
    hashes: dict[str, str],
    decision_digest: str,
) -> ContentProductionAcceptancePolicy:
    sources = {
        "matched_classification": _source("matched.json", "a" * 64),
        "unmatched_classification": _source("unmatched.json", "b" * 64),
    }
    source_policies = tuple(
        ContentProductionSourceReceiptPolicy(
            name=name,
            reference=cast(str, item["artifact_reference"]),
            sha256=cast(str, item["sha256"]),
            raw_artifact_retained=False,
            retention_status="external_ephemeral_receipt_only",
        )
        for name, item in sources.items()
    )
    return ContentProductionAcceptancePolicy(
        policy_id="synthetic_v1",
        packet_schema_version="wilq_content_production_classification_v1",
        judge_schema_version="synthetic_judge_v1",
        judge_reviewer_role="independent_judge",
        judge_protected_binding_check_name="protected",
        decision_set_digest=decision_digest,
        base_revision="1" * 40,
        canonical_paths=PATHS,
        expected_counts=ContentProductionClassificationCounts(**_counts()),
        expected_approved_revisions=1,
        freshness_connector_ids=("gsc", "wordpress"),
        source_receipts=source_policies,
        protected_binding=ContentProductionProtectedBindingPolicy(
            canonical_path=PATHS[0],
            current_work_item_id="work_current_1",
            retained_work_item_id="work_retained",
            revision_id=REVISION_ID,
            revision_digest=REVISION_DIGEST,
            action_ids=(ACTION_ID,),
            draft_post_ids=("1991",),
            identity_status="fork",
            judge_identity_status="fork_explicitly_unresolved",
        ),
        invalid_evidence=ContentProductionEvidenceDefectPolicy(
            evidence_id="ev_legacy_invalid",
            blocker_code="invalid_legacy_evidence_id",
            occurrence_count=1,
        ),
        public_origin="https://www.ekologus.pl",
        primary_evidence_http_status=200,
        primary_evidence_metrics_asserted=False,
        **hashes,
    )


def _judge(packet_sha: str, decision_digest: str, protected: JsonObject) -> JsonObject:
    historical_protection = protected.get("blocked_historical_protection")
    if historical_protection is not None:
        history = cast(JsonObject, historical_protection)
        protected_check = {
            "decision": "blocked",
            "historical_revision_id": history["historical_revision_id"],
            "historical_revision_digest": history["historical_revision_digest"],
            "current_verification_outcome": history["current_verification_outcome"],
            "current_verification_evidence_id": history["current_verification_evidence_id"],
            "current_verification_connector": history["current_verification_connector"],
            "current_verification_checked_at": history["current_verification_checked_at"],
            "exact_historical_revision_identity": True,
            "current_reuse_allowed": False,
            "must_not_regenerate": True,
        }
    else:
        binding = cast(JsonObject, protected["retained_revision_binding"])
        action_ids = cast(list[object], binding["verified_draft_action_ids"])
        draft_post_ids = cast(list[object], binding["verified_draft_post_ids"])
        protected_check = {
            "decision": "reuse",
            "revision_id": binding["retained_revision_id"],
            "revision_digest": binding["retained_revision_digest"],
            "action_id": action_ids[0],
            "draft_post_id": draft_post_ids[0],
            "exact_revision_action_draft_binding": True,
            "current_retained_work_item_status": "fork_explicitly_unresolved",
            "must_not_regenerate": True,
        }
    return {
        "schema_version": "synthetic_judge_v1",
        "reviewer_role": "independent_judge",
        "verdict": "accept",
        "reviewed_packet_sha256": packet_sha,
        "reviewed_decision_set_digest": decision_digest,
        "generated_at": "2026-08-30T10:01:00Z",
        "checks": {
            "packet_sha256_exact": True,
            "decision_set_digest_recomputed": True,
            "source_file_receipts_exact": True,
            "source_row_receipts_exact": True,
            "absolute_temp_path_count": 0,
            "raw_vendor_payload_count": 0,
            "protected": protected_check,
        },
    }
