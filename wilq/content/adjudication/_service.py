from __future__ import annotations

import hashlib
from collections import Counter
from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any, cast

from . import _contract as contract
from ._authorities import validate_authorities
from ._contract import (
    CONFIDENCE_VALUES,
    JOURNAL_RESUMPTION_KEYS,
    JOURNAL_RESUMPTION_SCHEMA_VERSION,
    LEDGER_ADJUDICATION_KEYS,
    LEDGER_ADJUDICATION_SCHEMA_VERSION,
    OPERATIONAL_SUMMARY_SCHEMA_VERSION,
    SOURCE_SCHEMA_VERSION,
    SUPPORTED_ACTIONS,
    AdjudicationError,
    assert_only_adjudication_changes,
    decision_set_digest,
    operational_ledger_summary,
    render_journal,
    render_ledger,
)
from ._decisions import validate_decisions
from ._judges import (
    caveat_set_digest,
    judge_receipt_set_digest,
    validate_judge_artifacts,
    validate_retained_caveats,
    validate_retained_judge_receipts,
)
from ._models import (
    Action,
    AdjudicationDecision,
    AdjudicationExpectations,
    AdjudicationProvenance,
    Confidence,
    ConfidenceAuthority,
    EvidenceCaveat,
    JudgeLineage,
    JudgeReceipt,
    NoindexAdjudicationSources,
    ReconciliationResult,
    RetainedAuthorities,
    SelectedAuthority,
    Status,
)
from ._policy import (
    CANONICAL_DIGEST_ALGORITHM,
    FILE_RECEIPT_ALGORITHM,
    INPUT_REFERENCE,
    PRODUCTION_EXPECTATIONS,
)
from ._sources import (
    retained_digest_locations,
    validate_baseline_pins,
    validate_production_pins,
    validate_provenance,
    validate_source_bundle,
)

_complete_counts = contract.complete_counts
_dev_path = contract.dev_path
_digest_json = contract.digest_json
_object_list = contract.object_list
_object = contract.object_value
_parse_json = contract.parse_json
_parse_jsonl = contract.parse_jsonl
_public_path = contract.public_path
_required_evidence_ids = contract.required_evidence_ids
_sha256 = contract.sha256_value
_string_list = contract.string_list
_string = contract.string_value
_validate_input_reference = contract.validate_input_reference
_verified_digest = contract.verified_digest


def reconcile_noindex_adjudication(
    sources: NoindexAdjudicationSources,
    *,
    expectations: AdjudicationExpectations = PRODUCTION_EXPECTATIONS,
) -> ReconciliationResult:
    """Add a review-only adjudication layer without changing operational state."""

    input_receipt_sha256 = _verified_digest(
        sources.integrated_decision.content,
        sources.integrated_decision.expected_sha256,
        "decision packet",
    )
    validate_source_bundle(sources, expectations)
    _validate_input_reference(INPUT_REFERENCE)
    packet = _object_list(
        _parse_json(sources.integrated_decision.content, "decision packet"),
        "decision packet",
    )
    _verified_digest(sources.ledger.content, sources.ledger.expected_sha256, "canonical ledger")
    _verified_digest(sources.journal.content, sources.journal.expected_sha256, "state journal")
    ledger = _parse_jsonl(sources.ledger.content, "canonical ledger")
    journal = _object(_parse_json(sources.journal.content, "state journal"), "state journal")
    ledger_rows, journal_rows = validate_authorities(ledger, journal, expectations)
    judge_lineage = validate_judge_artifacts(
        sources.judge_artifacts,
        packet,
        integrated_packet_sha256=input_receipt_sha256,
        ledger_rows=ledger_rows,
    )
    decisions = validate_decisions(
        packet,
        ledger_rows,
        input_receipt_sha256=input_receipt_sha256,
        judge_lineage=judge_lineage,
        expectations=expectations,
    )
    _validate_decision_counts(decisions, expectations)
    _validate_redirect_targets(decisions, ledger_rows)
    updated_ledger, updated_journal, path_digests = _reconciled_rows(
        ledger,
        journal,
        decisions,
    )
    adjudication_set_digest = decision_set_digest(path_digests)
    ledger_bytes = render_ledger(updated_ledger)
    summary = _adjudication_summary(decisions, expectations)
    _update_journal_metadata(
        updated_journal,
        ledger=updated_ledger,
        ledger_bytes=ledger_bytes,
        input_reference=INPUT_REFERENCE,
        input_receipt_sha256=input_receipt_sha256,
        decision_set_digest=adjudication_set_digest,
        judge_lineage=judge_lineage,
        provenance=sources.provenance,
        summary=summary,
    )
    journal_bytes = render_journal(updated_journal)
    assert_only_adjudication_changes(ledger, journal, updated_ledger, updated_journal)
    _validate_retained_authorities(ledger_bytes, journal_bytes, expectations=expectations)
    return ReconciliationResult(
        ledger_bytes=ledger_bytes,
        journal_bytes=journal_bytes,
        input_receipt_sha256=input_receipt_sha256,
        decision_set_digest=adjudication_set_digest,
        caveat_set_digest=judge_lineage.caveat_set_digest,
    )


def _reconciled_rows(
    ledger: Sequence[Mapping[str, Any]],
    journal: Mapping[str, Any],
    decisions: Mapping[str, AdjudicationDecision],
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, str]]]:
    updated_ledger = [deepcopy(dict(row)) for row in ledger]
    updated_journal = deepcopy(dict(journal))
    updated_ledger_by_path = {_dev_path(row["url"], "ledger URL"): row for row in updated_ledger}
    updated_journal_by_path = {row["path"]: row for row in updated_journal["urls"]}
    path_digests: list[dict[str, str]] = []
    for path in sorted(decisions):
        adjudication = _ledger_adjudication(decisions[path])
        updated_ledger_by_path[path]["re_adjudication"] = adjudication
        updated_journal_by_path[path]["re_adjudication"] = _journal_resumption(adjudication)
        path_digests.append(
            {"path": path, "adjudication_digest": adjudication["adjudication_digest"]}
        )
    return updated_ledger, updated_journal, path_digests


def _update_journal_metadata(
    journal: dict[str, Any],
    *,
    ledger: Sequence[Mapping[str, Any]],
    ledger_bytes: bytes,
    input_reference: str,
    input_receipt_sha256: str,
    decision_set_digest: str,
    judge_lineage: JudgeLineage,
    provenance: AdjudicationProvenance,
    summary: Mapping[str, Any],
) -> None:
    journal_summary = _object(journal.get("summary"), "journal.summary")
    journal_summary["noindex_re_adjudication"] = dict(summary)
    journal["summary"] = journal_summary
    journal_sources = _object(journal.get("sources"), "journal.sources")
    canonical_source = _object(
        journal_sources.get("canonical_ledger"),
        "journal.sources.canonical_ledger",
    )
    canonical_source.update(_canonical_ledger_metadata(ledger, ledger_bytes))
    journal_sources["canonical_ledger"] = canonical_source
    journal_sources["noindex_re_adjudication"] = _source_metadata(
        input_reference=input_reference,
        input_receipt_sha256=input_receipt_sha256,
        decision_set_digest=decision_set_digest,
        judge_lineage=judge_lineage,
        provenance=provenance,
        summary=summary,
    )
    journal["sources"] = journal_sources


def _validate_retained_authorities(
    ledger_bytes: bytes,
    journal_bytes: bytes,
    *,
    expectations: AdjudicationExpectations,
) -> RetainedAuthorities:
    """Validate a retained pair without access to the ephemeral judge files."""

    ledger = _parse_jsonl(ledger_bytes, "canonical ledger")
    journal = _object(_parse_json(journal_bytes, "state journal"), "state journal")
    ledger_rows, journal_rows = validate_authorities(ledger, journal, expectations)
    (
        decisions,
        input_receipts,
        input_references,
        judge_receipt_sets,
        caveat_sets,
        path_digests,
    ) = _embedded_decisions(ledger_rows, journal_rows)
    if len(decisions) != expectations.decision_rows:
        raise AdjudicationError("Embedded re-adjudication row count does not match the contract.")
    if len(input_receipts) != 1 or len(input_references) != 1:
        raise AdjudicationError("Embedded adjudications do not share one exact input receipt.")
    if len(judge_receipt_sets) != 1:
        raise AdjudicationError("Embedded adjudications do not share one judge receipt set.")
    if len(caveat_sets) != 1:
        raise AdjudicationError("Embedded adjudications do not share one caveat set.")
    _validate_decision_counts(decisions, expectations)
    terminal_redirect_rows = _validate_redirect_targets(decisions, ledger_rows)
    summary = _adjudication_summary(decisions, expectations)
    if terminal_redirect_rows != summary["terminal_redirect_target_rows"]:
        raise AdjudicationError("Redirect target summary is not exact.")
    decision_digest = decision_set_digest(path_digests)
    caveat_digest = next(iter(caveat_sets))
    _validate_journal_metadata(
        journal,
        ledger=ledger,
        input_reference=next(iter(input_references)),
        input_receipt_sha256=next(iter(input_receipts)),
        decision_set_digest=decision_digest,
        expected_judge_receipt_set_digest=next(iter(judge_receipt_sets)),
        expected_caveat_set_digest=caveat_digest,
        summary=summary,
        expectations=expectations,
    )
    validate_baseline_pins(ledger, journal, expectations)
    return RetainedAuthorities(
        receipt_occurrences=retained_digest_locations(ledger, journal),
        decision_set_digest=decision_digest,
        caveat_set_digest=caveat_digest,
    )


def _embedded_decisions(
    ledger_rows: Mapping[str, Mapping[str, Any]],
    journal_rows: Mapping[str, Mapping[str, Any]],
) -> tuple[
    dict[str, AdjudicationDecision],
    set[str],
    set[str],
    set[str],
    set[str],
    list[dict[str, str]],
]:
    decisions: dict[str, AdjudicationDecision] = {}
    input_receipts: set[str] = set()
    input_references: set[str] = set()
    judge_receipt_sets: set[str] = set()
    caveat_sets: set[str] = set()
    path_digests: list[dict[str, str]] = []
    for path, row in ledger_rows.items():
        raw = row.get("re_adjudication")
        if raw is None:
            if row["final_disposition"] == "noindex":
                raise AdjudicationError(f"Missing re-adjudication for noindex path: {path}")
            continue
        if row["final_disposition"] != "noindex":
            raise AdjudicationError(f"Re-adjudication is attached to a non-noindex path: {path}")
        adjudication = _validated_embedded_adjudication(raw, row, path)
        decisions[path] = _decision_from_adjudication(path, row, adjudication)
        input_receipts.add(adjudication["input_receipt_sha256"])
        input_references.add(adjudication["input_reference"])
        judge_receipt_sets.add(adjudication["judge_receipt_set_digest"])
        caveat_sets.add(adjudication["caveat_set_digest"])
        path_digests.append(
            {"path": path, "adjudication_digest": adjudication["adjudication_digest"]}
        )

        resume = _object(
            journal_rows[path].get("re_adjudication"),
            f"journal re-adjudication for {path}",
        )
        if set(resume) != JOURNAL_RESUMPTION_KEYS:
            raise AdjudicationError(f"Journal re-adjudication has unsupported fields: {path}")
        if resume != _journal_resumption(adjudication):
            raise AdjudicationError(f"Ledger/journal adjudication mirror mismatch: {path}")
    for path, row in journal_rows.items():
        if path not in decisions and "re_adjudication" in row:
            raise AdjudicationError(f"Journal has an orphan re-adjudication: {path}")
    return (
        decisions,
        input_receipts,
        input_references,
        judge_receipt_sets,
        caveat_sets,
        path_digests,
    )


def _validate_journal_metadata(
    journal: Mapping[str, Any],
    *,
    ledger: Sequence[Mapping[str, Any]],
    input_reference: str,
    input_receipt_sha256: str,
    decision_set_digest: str,
    expected_judge_receipt_set_digest: str,
    expected_caveat_set_digest: str,
    summary: Mapping[str, Any],
    expectations: AdjudicationExpectations,
) -> None:
    source = _object(
        _object(journal.get("sources"), "journal.sources").get("noindex_re_adjudication"),
        "journal.sources.noindex_re_adjudication",
    )
    receipts = validate_retained_judge_receipts(source.get("judge_receipts"))
    observed_judge_digest = judge_receipt_set_digest(receipts)
    if observed_judge_digest != expected_judge_receipt_set_digest:
        raise AdjudicationError("Retained judge receipts are not bound to ledger adjudications.")
    caveats = validate_retained_caveats(source.get("caveats"))
    observed_caveat_digest = caveat_set_digest(caveats)
    if observed_caveat_digest != expected_caveat_set_digest:
        raise AdjudicationError("Retained caveats are not bound to ledger adjudications.")
    provenance = validate_provenance(source.get("provenance"))
    validate_production_pins(
        expectations,
        input_receipt_sha256=input_receipt_sha256,
        receipts=receipts,
        observed_judge_receipt_set_digest=observed_judge_digest,
        decision_set_digest=decision_set_digest,
        observed_caveat_set_digest=observed_caveat_digest,
        provenance=provenance,
    )
    if source != _source_metadata(
        input_reference=input_reference,
        input_receipt_sha256=input_receipt_sha256,
        decision_set_digest=decision_set_digest,
        receipts=receipts,
        judge_receipt_set_digest=observed_judge_digest,
        caveats=caveats,
        caveat_set_digest=observed_caveat_digest,
        provenance=provenance,
        summary=summary,
    ):
        raise AdjudicationError("Journal adjudication source metadata is not canonical.")
    journal_summary = _object(journal.get("summary"), "journal.summary")
    if journal_summary.get("noindex_re_adjudication") != summary:
        raise AdjudicationError("Journal adjudication summary is not canonical.")
    ledger_bytes = render_ledger(ledger)
    canonical_source = _object(
        _object(journal.get("sources"), "journal.sources").get("canonical_ledger"),
        "journal.sources.canonical_ledger",
    )
    expected_canonical_metadata = _canonical_ledger_metadata(ledger, ledger_bytes)
    for key, expected in expected_canonical_metadata.items():
        if canonical_source.get(key) != expected:
            raise AdjudicationError(f"Canonical ledger source metadata is stale: {key}")


def _source_metadata(
    *,
    input_reference: str,
    input_receipt_sha256: str,
    decision_set_digest: str,
    provenance: AdjudicationProvenance,
    summary: Mapping[str, Any],
    judge_lineage: JudgeLineage | None = None,
    receipts: Sequence[JudgeReceipt] | None = None,
    judge_receipt_set_digest: str | None = None,
    caveats: Sequence[EvidenceCaveat] | None = None,
    caveat_set_digest: str | None = None,
) -> dict[str, Any]:
    if judge_lineage is not None:
        receipts = judge_lineage.receipts
        judge_receipt_set_digest = judge_lineage.receipt_set_digest
        caveats = judge_lineage.caveats
        caveat_set_digest = judge_lineage.caveat_set_digest
    if (
        receipts is None
        or judge_receipt_set_digest is None
        or caveats is None
        or caveat_set_digest is None
    ):
        raise AdjudicationError("Adjudication source lineage is incomplete.")
    return {
        "schema_version": SOURCE_SCHEMA_VERSION,
        "input_reference": input_reference,
        "input_receipt_sha256": input_receipt_sha256,
        "input_receipt_algorithm": FILE_RECEIPT_ALGORITHM,
        "judge_receipts": [receipt.as_json() for receipt in receipts],
        "judge_receipt_set_digest": judge_receipt_set_digest,
        "judge_receipt_set_digest_algorithm": CANONICAL_DIGEST_ALGORITHM,
        "caveats": [caveat.as_json() for caveat in caveats],
        "caveat_set_digest": caveat_set_digest,
        "caveat_set_digest_algorithm": CANONICAL_DIGEST_ALGORITHM,
        "provenance": provenance.as_json(),
        "confidence_authority": {
            "tie_breaker_rows": "tie_breaker",
            "non_tie_rows": "integrator_decision_packet",
        },
        "decision_receipt_algorithm": CANONICAL_DIGEST_ALGORITHM,
        "adjudication_digest_algorithm": CANONICAL_DIGEST_ALGORITHM,
        "decision_set_digest": decision_set_digest,
        "decision_set_digest_algorithm": CANONICAL_DIGEST_ALGORITHM,
        "rows": summary["rows"],
        "resolved_rows": summary["resolved_rows"],
        "blocked_rows": summary["blocked_rows"],
        "recommended_action_counts": summary["recommended_action_counts"],
        "terminal_redirect_target_rows": summary["terminal_redirect_target_rows"],
        "read_only": True,
        "operational_promotion": False,
    }


def _canonical_ledger_metadata(
    ledger: Sequence[Mapping[str, Any]],
    ledger_bytes: bytes,
) -> dict[str, Any]:
    summary = operational_ledger_summary(ledger)
    return {
        "sha256": hashlib.sha256(ledger_bytes).hexdigest(),
        "summary_sha256": _digest_json(summary),
        "summary_schema_version": OPERATIONAL_SUMMARY_SCHEMA_VERSION,
        "summary_digest_algorithm": CANONICAL_DIGEST_ALGORITHM,
        "summary": summary,
    }


def _ledger_adjudication(decision: AdjudicationDecision) -> dict[str, Any]:
    payload = {
        "schema_version": LEDGER_ADJUDICATION_SCHEMA_VERSION,
        "input_reference": decision.input_reference,
        "recommended_action": decision.recommended_action,
        "recommended_target_url": decision.recommended_target_url,
        "status": decision.status,
        "confidence": decision.confidence,
        "confidence_authority": decision.confidence_authority,
        "selected_authority": decision.selected_authority,
        "decision_basis_pl": decision.decision_basis_pl,
        "evidence_ids": list(decision.evidence_ids),
        "blockers": list(decision.blockers),
        "decision_receipt_sha256": decision.decision_receipt_sha256,
        "input_receipt_sha256": decision.input_receipt_sha256,
        "judge_receipt_set_digest": decision.judge_receipt_set_digest,
        "caveat_set_digest": decision.caveat_set_digest,
        "technical_row_digest": decision.technical_row_digest,
        "strategy_row_digest": decision.strategy_row_digest,
        "tie_breaker_row_digest": decision.tie_breaker_row_digest,
        "operational_promotion": False,
    }
    payload["adjudication_digest"] = _digest_json(payload)
    return payload


def _journal_resumption(adjudication: Mapping[str, Any]) -> dict[str, Any]:
    blocked = adjudication["status"] == "blocked"
    return {
        "schema_version": JOURNAL_RESUMPTION_SCHEMA_VERSION,
        "input_reference": adjudication["input_reference"],
        "adjudication_digest": adjudication["adjudication_digest"],
        "caveat_set_digest": adjudication["caveat_set_digest"],
        "status": adjudication["status"],
        "recommended_action": adjudication["recommended_action"],
        "recommended_target_url": adjudication["recommended_target_url"],
        "operational_promotion": False,
        "next_gate": (
            "resolve_blockers_and_re_adjudicate"
            if blocked
            else "human_review_before_typed_operational_promotion"
        ),
        "blockers": list(adjudication["blockers"]),
    }


def _validated_embedded_adjudication(
    raw: Any,
    ledger_row: Mapping[str, Any],
    path: str,
) -> Mapping[str, Any]:
    value = _object(raw, f"ledger re-adjudication for {path}")
    if set(value) != LEDGER_ADJUDICATION_KEYS:
        raise AdjudicationError(f"Ledger re-adjudication has unsupported fields: {path}")
    if value.get("schema_version") != LEDGER_ADJUDICATION_SCHEMA_VERSION:
        raise AdjudicationError(f"Unsupported ledger re-adjudication schema: {path}")
    _validate_input_reference(value.get("input_reference"))
    action = _string(value.get("recommended_action"), f"re-adjudication action {path}")
    if action not in SUPPORTED_ACTIONS:
        raise AdjudicationError(f"Unsupported embedded recommended action: {path}")
    target = value.get("recommended_target_url")
    if action == "redirect":
        _public_path(_string(target, f"re-adjudication target {path}"), f"target {path}")
    elif target is not None:
        raise AdjudicationError(f"Non-redirect embedded action has a target: {path}")
    expected_status = "blocked" if action == "blocked" else "resolved"
    blockers = _string_list(value.get("blockers"), f"re-adjudication blockers {path}")
    if value.get("status") != expected_status or ((action == "blocked") != bool(blockers)):
        raise AdjudicationError(f"Embedded status/blocker state is invalid: {path}")
    if value.get("confidence") not in CONFIDENCE_VALUES:
        raise AdjudicationError(f"Embedded confidence is invalid: {path}")
    _string(value.get("decision_basis_pl"), f"re-adjudication decision basis {path}")
    evidence_ids = _string_list(value.get("evidence_ids"), f"re-adjudication evidence {path}")
    if evidence_ids != sorted(evidence_ids) or len(evidence_ids) != len(set(evidence_ids)):
        raise AdjudicationError(f"Embedded evidence IDs are not canonical: {path}")
    required_evidence = _required_evidence_ids(ledger_row, path)
    if not required_evidence.issubset(evidence_ids):
        raise AdjudicationError(f"Embedded required evidence is missing: {path}")
    if blockers != sorted(blockers) or len(blockers) != len(set(blockers)):
        raise AdjudicationError(f"Embedded blockers are not canonical: {path}")
    for key in (
        "decision_receipt_sha256",
        "input_receipt_sha256",
        "judge_receipt_set_digest",
        "caveat_set_digest",
        "technical_row_digest",
        "strategy_row_digest",
        "adjudication_digest",
    ):
        _sha256(value.get(key), f"re-adjudication {key} {path}")
    tie_digest = value.get("tie_breaker_row_digest")
    if tie_digest is not None:
        _sha256(tie_digest, f"re-adjudication tie_breaker_row_digest {path}")
    expected_authorities = (
        ("tie_breaker", "tie_breaker")
        if tie_digest is not None
        else ("strategy", "integrator_decision_packet")
    )
    if (
        value.get("selected_authority"),
        value.get("confidence_authority"),
    ) != expected_authorities:
        raise AdjudicationError(f"Embedded authority attribution is invalid: {path}")
    if value.get("operational_promotion") is not False:
        raise AdjudicationError(f"Operational promotion is forbidden: {path}")
    receipt_row = {
        "url": ledger_row["url"],
        "current_disposition": "noindex",
        "proposed_disposition": action,
        "target_url": target,
        "confidence": value["confidence"],
        "evidence_ids": evidence_ids,
        "decision_basis": value["decision_basis_pl"],
        "blockers": blockers,
    }
    if value["decision_receipt_sha256"] != _digest_json(receipt_row):
        raise AdjudicationError(f"Decision receipt hash mismatch: {path}")
    digest_payload = dict(value)
    digest = digest_payload.pop("adjudication_digest")
    if digest != _digest_json(digest_payload):
        raise AdjudicationError(f"Adjudication digest mismatch: {path}")
    return value


def _decision_from_adjudication(
    path: str,
    ledger_row: Mapping[str, Any],
    adjudication: Mapping[str, Any],
) -> AdjudicationDecision:
    return AdjudicationDecision(
        path=path,
        source_url=cast(str, ledger_row["url"]),
        source_public_url=cast(str, ledger_row["public_url"]),
        recommended_action=cast(Action, adjudication["recommended_action"]),
        recommended_target_url=cast(str | None, adjudication["recommended_target_url"]),
        status=cast(Status, adjudication["status"]),
        confidence=cast(Confidence, adjudication["confidence"]),
        decision_basis_pl=cast(str, adjudication["decision_basis_pl"]),
        evidence_ids=tuple(cast(list[str], adjudication["evidence_ids"])),
        blockers=tuple(cast(list[str], adjudication["blockers"])),
        decision_receipt_sha256=cast(str, adjudication["decision_receipt_sha256"]),
        input_receipt_sha256=cast(str, adjudication["input_receipt_sha256"]),
        judge_receipt_set_digest=cast(str, adjudication["judge_receipt_set_digest"]),
        caveat_set_digest=cast(str, adjudication["caveat_set_digest"]),
        technical_row_digest=cast(str, adjudication["technical_row_digest"]),
        strategy_row_digest=cast(str, adjudication["strategy_row_digest"]),
        tie_breaker_row_digest=cast(str | None, adjudication["tie_breaker_row_digest"]),
        selected_authority=cast(SelectedAuthority, adjudication["selected_authority"]),
        confidence_authority=cast(ConfidenceAuthority, adjudication["confidence_authority"]),
        input_reference=cast(str, adjudication["input_reference"]),
    )


def _validate_redirect_targets(
    decisions: Mapping[str, AdjudicationDecision],
    ledger_rows: Mapping[str, Mapping[str, Any]],
) -> int:
    by_public_url = {row["public_url"]: row for row in ledger_rows.values()}
    decisions_by_public_url = {
        decision.source_public_url: decision for decision in decisions.values()
    }
    redirect_edges = {
        decision.source_public_url: cast(str, decision.recommended_target_url)
        for decision in decisions.values()
        if decision.recommended_action == "redirect"
    }
    for source, target in redirect_edges.items():
        if source == target:
            raise AdjudicationError(f"Self redirect is forbidden: {source}")
    _reject_redirect_cycles(redirect_edges)
    for source, target in redirect_edges.items():
        target_row = by_public_url.get(target)
        if target_row is None:
            raise AdjudicationError(f"Redirect target is outside the 214-row ledger: {target}")
        target_decision = decisions_by_public_url.get(target)
        if target in redirect_edges or target_row["final_disposition"] == "redirect":
            raise AdjudicationError(f"Redirect chain is forbidden: {source} -> {target}")
        if target_decision is not None:
            terminal_keep = (
                target_decision.recommended_action == "keep"
                and target_decision.status == "resolved"
            )
        else:
            terminal_keep = target_row["final_disposition"] == "keep"
            if terminal_keep:
                terminal_keep = (
                    target_row.get("canonical_owner_url") == target
                    and target_row.get("lineage_status") == "canonical_target_verified"
                    and isinstance(target_row.get("production_readback_receipt_id"), str)
                    and bool(target_row["production_readback_receipt_id"])
                )
        if not terminal_keep:
            raise AdjudicationError(f"Redirect target is not a safe terminal keep: {target}")
    return len(redirect_edges)


def _reject_redirect_cycles(edges: Mapping[str, str]) -> None:
    for source in edges:
        seen: set[str] = set()
        current = source
        while current in edges:
            if current in seen:
                raise AdjudicationError(f"Redirect loop is forbidden: {source}")
            seen.add(current)
            current = edges[current]


def _validate_decision_counts(
    decisions: Mapping[str, AdjudicationDecision],
    expectations: AdjudicationExpectations,
) -> None:
    actions: Counter[str] = Counter(decision.recommended_action for decision in decisions.values())
    observed_actions = _complete_counts(actions, set(SUPPORTED_ACTIONS) | {"remove"})
    if observed_actions != expectations.recommendation_partition:
        raise AdjudicationError("Recommended action partition does not match the contract.")
    statuses = Counter(decision.status for decision in decisions.values())
    if statuses != Counter(resolved=expectations.resolved_rows, blocked=expectations.blocked_rows):
        raise AdjudicationError("Resolved/blocked partition does not match the contract.")


def _adjudication_summary(
    decisions: Mapping[str, AdjudicationDecision],
    expectations: AdjudicationExpectations,
) -> dict[str, Any]:
    return {
        "rows": len(decisions),
        "resolved_rows": sum(item.status == "resolved" for item in decisions.values()),
        "blocked_rows": sum(item.status == "blocked" for item in decisions.values()),
        "recommended_action_counts": expectations.recommendation_partition,
        "terminal_redirect_target_rows": sum(
            item.recommended_action == "redirect" for item in decisions.values()
        ),
        "operational_promotion_rows": 0,
    }
