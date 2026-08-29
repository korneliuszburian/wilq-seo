from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast

from . import _contract as contract
from ._models import (
    Action,
    AdjudicationDecision,
    AdjudicationExpectations,
    Confidence,
    JudgeLineage,
)
from ._policy import INPUT_REFERENCE


def validate_decisions(
    packet: Sequence[Mapping[str, Any]],
    ledger_rows: Mapping[str, Mapping[str, Any]],
    *,
    input_receipt_sha256: str,
    judge_lineage: JudgeLineage,
    expectations: AdjudicationExpectations,
) -> dict[str, AdjudicationDecision]:
    if len(packet) != expectations.decision_rows:
        raise contract.AdjudicationError("Decision packet row count does not match the contract.")
    decisions: dict[str, AdjudicationDecision] = {}
    for index, raw in enumerate(packet):
        decision = _validated_decision(
            raw,
            index=index,
            ledger_rows=ledger_rows,
            judge_lineage=judge_lineage,
            input_receipt_sha256=input_receipt_sha256,
        )
        if decision.path in decisions:
            raise contract.AdjudicationError(f"Duplicate decision path: {decision.path}")
        decisions[decision.path] = decision
    expected_paths = {
        path for path, row in ledger_rows.items() if row["final_disposition"] == "noindex"
    }
    if set(decisions) != expected_paths:
        raise contract.AdjudicationError(
            "Decision packet does not cover the exact noindex path set."
        )
    return decisions


def _validated_decision(
    raw: Mapping[str, Any],
    *,
    index: int,
    ledger_rows: Mapping[str, Mapping[str, Any]],
    judge_lineage: JudgeLineage,
    input_receipt_sha256: str,
) -> AdjudicationDecision:
    row = contract.object_value(raw, f"decision row {index}")
    if set(row) != contract.PACKET_KEYS:
        raise contract.AdjudicationError(
            f"Decision row {index} has unsupported or operational fields."
        )
    url = contract.string_value(row.get("url"), f"decision row {index}.url")
    path = contract.dev_path(url, f"decision row {index}.url")
    ledger_row = ledger_rows.get(path)
    if ledger_row is None:
        raise contract.AdjudicationError(
            f"Decision path is missing from the canonical ledger: {path}"
        )
    if url != ledger_row["url"]:
        raise contract.AdjudicationError(
            f"Decision URL is not the exact canonical ledger URL: {path}"
        )
    if row.get("current_disposition") != "noindex" or ledger_row["final_disposition"] != "noindex":
        raise contract.AdjudicationError(f"Decision path is not operationally noindex: {path}")
    action, target = _validated_action(row, path)
    confidence = contract.string_value(row.get("confidence"), f"decision row {path}.confidence")
    if confidence not in contract.CONFIDENCE_VALUES:
        raise contract.AdjudicationError(f"Unsupported confidence for {path}: {confidence}")
    evidence_ids = sorted(
        contract.string_list(row.get("evidence_ids"), f"decision row {path}.evidence_ids")
    )
    if len(evidence_ids) != len(set(evidence_ids)):
        raise contract.AdjudicationError(f"Duplicate evidence ID for {path}.")
    required = contract.required_evidence_ids(ledger_row, path)
    if not evidence_ids or not required.issubset(evidence_ids):
        raise contract.AdjudicationError(f"Required evidence is missing for {path}.")
    basis = contract.string_value(row.get("decision_basis"), f"decision row {path}.decision_basis")
    blockers = sorted(contract.string_list(row.get("blockers"), f"decision row {path}.blockers"))
    if len(blockers) != len(set(blockers)) or ((action == "blocked") != bool(blockers)):
        raise contract.AdjudicationError(f"Blocked action and blocker state disagree for {path}.")
    row_lineage = judge_lineage.rows_by_url.get(url)
    if row_lineage is None:
        raise contract.AdjudicationError(f"Judge row lineage is missing for {path}.")
    normalized = {
        "url": url,
        "current_disposition": "noindex",
        "proposed_disposition": action,
        "target_url": target,
        "confidence": confidence,
        "evidence_ids": evidence_ids,
        "decision_basis": basis,
        "blockers": blockers,
    }
    return AdjudicationDecision(
        path=path,
        source_url=url,
        source_public_url=contract.string_value(
            ledger_row.get("public_url"), f"ledger public URL for {path}"
        ),
        recommended_action=cast(Action, action),
        recommended_target_url=target,
        status="blocked" if action == "blocked" else "resolved",
        confidence=cast(Confidence, confidence),
        decision_basis_pl=basis,
        evidence_ids=tuple(evidence_ids),
        blockers=tuple(blockers),
        decision_receipt_sha256=contract.digest_json(normalized),
        input_receipt_sha256=input_receipt_sha256,
        judge_receipt_set_digest=judge_lineage.receipt_set_digest,
        caveat_set_digest=judge_lineage.caveat_set_digest,
        technical_row_digest=row_lineage.technical_row_digest,
        strategy_row_digest=row_lineage.strategy_row_digest,
        tie_breaker_row_digest=row_lineage.tie_breaker_row_digest,
        selected_authority=row_lineage.selected_authority,
        confidence_authority=row_lineage.confidence_authority,
        input_reference=INPUT_REFERENCE,
    )


def _validated_action(row: Mapping[str, Any], path: str) -> tuple[str, str | None]:
    action = contract.string_value(row.get("proposed_disposition"), f"decision row {path}.action")
    if action == "remove":
        raise contract.AdjudicationError(f"Remove is forbidden in re-adjudication: {path}")
    if action not in contract.SUPPORTED_ACTIONS:
        raise contract.AdjudicationError(f"Unsupported recommended action for {path}: {action}")
    target = row.get("target_url")
    if action == "redirect":
        target = contract.string_value(target, f"decision row {path}.target_url")
        contract.public_path(target, f"decision row {path}.target_url")
        return action, target
    if target is not None:
        raise contract.AdjudicationError(f"Only redirect may carry a target URL: {path}")
    return action, None
