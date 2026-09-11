from __future__ import annotations

import datetime as dt
from collections.abc import Mapping, Sequence
from typing import Any

from . import _contract as contract
from ._models import (
    AdjudicationExpectations,
    AdjudicationProvenance,
    JudgeReceipt,
    NoindexAdjudicationSources,
    RetainedReceiptOccurrence,
)

SOURCE_ROLES = (
    "integrated_decision",
    "technical",
    "strategy",
    "tie_breaker",
    "canonical_ledger",
    "state_journal",
)
LEDGER_DIGEST_KEYS = (
    "adjudication_digest",
    "caveat_set_digest",
    "decision_receipt_sha256",
    "input_receipt_sha256",
    "judge_receipt_set_digest",
    "strategy_row_digest",
    "technical_row_digest",
    "tie_breaker_row_digest",
)
JOURNAL_SOURCE_SHA256_KEYS = (
    "acf_current_observation",
    "action_binding_recovery",
    "candidate_quality_audit",
    "canonical_ledger",
    "current_revision_export",
    "dev_progress_overlay",
    "dev_readback_archive",
    "public_acf_inventory",
    "public_sitemap_inventory",
    "robot_manifest",
    "source_pack_verification",
)


def validate_source_bundle(
    sources: NoindexAdjudicationSources,
    expectations: AdjudicationExpectations,
) -> None:
    observed_roles = (
        sources.integrated_decision.role,
        sources.technical_judge.role,
        sources.strategy_judge.role,
        sources.tie_breaker_judge.role,
        sources.ledger.role,
        sources.journal.role,
    )
    if observed_roles != SOURCE_ROLES:
        raise contract.AdjudicationError("Adjudication source roles/order are not exact.")
    pins = expectations.production_pins
    if pins is None:
        return
    if sources.integrated_decision.expected_sha256 != pins.input_receipt_sha256:
        raise contract.AdjudicationError("Production integrated packet receipt is not exact.")
    receipts = tuple(
        JudgeReceipt(
            role=artifact.role,
            artifact_reference=artifact.artifact_reference,
            sha256=artifact.expected_sha256,
        )
        for artifact in sources.judge_artifacts
    )
    if receipts != pins.judge_receipts:
        raise contract.AdjudicationError("Production judge receipts are not exact.")
    if sources.provenance != pins.provenance:
        raise contract.AdjudicationError("Production adjudication provenance is not exact.")


def validate_provenance(raw: Any) -> AdjudicationProvenance:
    value = contract.object_value(raw, "adjudication provenance")
    keys = {
        "recorded_at",
        "base_revision",
        "baseline_semantics",
        "raw_judge_artifacts_retained",
        "raw_judge_retention_status",
    }
    if set(value) != keys:
        raise contract.AdjudicationError("Adjudication provenance schema is not exact.")
    recorded_at = contract.string_value(value.get("recorded_at"), "provenance recorded_at")
    try:
        dt.datetime.strptime(recorded_at, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as error:
        raise contract.AdjudicationError("Provenance recorded_at is not canonical UTC.") from error
    base_revision = contract.string_value(value.get("base_revision"), "provenance base revision")
    if len(base_revision) != 40 or any(
        character not in "0123456789abcdef" for character in base_revision
    ):
        raise contract.AdjudicationError("Provenance base revision is not an exact git SHA-1.")
    retained = value.get("raw_judge_artifacts_retained")
    if not isinstance(retained, bool):
        raise contract.AdjudicationError("Raw judge retention status must be boolean.")
    return AdjudicationProvenance(
        recorded_at=recorded_at,
        base_revision=base_revision,
        baseline_semantics=contract.string_value(
            value.get("baseline_semantics"), "provenance baseline semantics"
        ),
        raw_judge_artifacts_retained=retained,
        raw_judge_retention_status=contract.string_value(
            value.get("raw_judge_retention_status"), "provenance raw judge status"
        ),
    )


def validate_production_pins(
    expectations: AdjudicationExpectations,
    *,
    input_receipt_sha256: str,
    receipts: Sequence[JudgeReceipt],
    observed_judge_receipt_set_digest: str,
    decision_set_digest: str,
    observed_caveat_set_digest: str,
    provenance: AdjudicationProvenance,
) -> None:
    pins = expectations.production_pins
    if pins is None:
        return
    exact = (
        input_receipt_sha256 == pins.input_receipt_sha256
        and tuple(receipts) == pins.judge_receipts
        and observed_judge_receipt_set_digest == pins.judge_receipt_set_digest
        and provenance == pins.provenance
    )
    if not exact:
        raise contract.AdjudicationError("Retained production source pins are not exact.")
    if pins.caveat_set_digest is not None and observed_caveat_set_digest != pins.caveat_set_digest:
        raise contract.AdjudicationError("Retained production caveat-set digest is not exact.")
    if pins.decision_set_digest is not None and decision_set_digest != pins.decision_set_digest:
        raise contract.AdjudicationError("Retained production decision-set digest is not exact.")


def validate_baseline_pins(
    ledger: Sequence[Mapping[str, Any]],
    journal: Mapping[str, Any],
    expectations: AdjudicationExpectations,
) -> None:
    pins = expectations.production_pins
    if pins is None:
        return
    if _ledger_baseline_digest(ledger) != pins.ledger_baseline_digest:
        raise contract.AdjudicationError("Operational ledger baseline digest is not exact.")
    if _journal_baseline_digest(journal) != pins.journal_baseline_digest:
        raise contract.AdjudicationError("Operational journal baseline digest is not exact.")


def retained_digest_locations(
    ledger: Sequence[Mapping[str, Any]],
    journal: Mapping[str, Any],
) -> tuple[RetainedReceiptOccurrence, ...]:
    locations: list[RetainedReceiptOccurrence] = []
    for index, row in enumerate(ledger):
        adjudication = row.get("re_adjudication")
        if not isinstance(adjudication, Mapping):
            continue
        for key in LEDGER_DIGEST_KEYS:
            value = adjudication.get(key)
            if value is not None:
                _append_digest(locations, "ledger", (index, "re_adjudication", key), value)
    _journal_digest_locations(journal, locations)
    return tuple(locations)


def _journal_digest_locations(
    journal: Mapping[str, Any],
    locations: list[RetainedReceiptOccurrence],
) -> None:
    for index, draft in enumerate(_mapping_rows(journal.get("drafts"))):
        for key in ("readback_content_digest", "revision_digest"):
            _append_if_present(locations, ("drafts", index, key), draft.get(key))
    for index, audit in enumerate(_mapping_rows(journal.get("mutation_audits"))):
        audit_id = audit.get("id")
        if isinstance(audit_id, str) and _safe_mutation_audit_id(audit_id):
            locations.append(
                RetainedReceiptOccurrence(
                    authority="journal",
                    path=("mutation_audits", index, "id"),
                    value=audit_id,
                    detector="base64",
                )
            )
        binding = audit.get("binding")
        if isinstance(binding, Mapping):
            for key in ("content_digest", "draft_package_digest", "planning_digest"):
                _append_if_present(
                    locations, ("mutation_audits", index, "binding", key), binding.get(key)
                )
    sources = journal.get("sources")
    if isinstance(sources, Mapping):
        _source_digest_locations(sources, locations)
    repository = journal.get("repository")
    if isinstance(repository, Mapping):
        for key in ("head", "origin_main"):
            value = repository.get(key)
            if isinstance(value, str) and _lower_hex(value, 40):
                locations.append(
                    RetainedReceiptOccurrence(
                        authority="journal",
                        path=("repository", key),
                        value=value,
                        detector="hex40",
                    )
                )
    for index, row in enumerate(_mapping_rows(journal.get("urls"))):
        _append_if_present(
            locations,
            ("urls", index, "current_revision_digest"),
            row.get("current_revision_digest"),
        )
        adjudication = row.get("re_adjudication")
        if isinstance(adjudication, Mapping):
            for key in ("adjudication_digest", "caveat_set_digest"):
                _append_if_present(
                    locations,
                    ("urls", index, "re_adjudication", key),
                    adjudication.get(key),
                )


def _source_digest_locations(
    sources: Mapping[str, Any],
    locations: list[RetainedReceiptOccurrence],
) -> None:
    for name in JOURNAL_SOURCE_SHA256_KEYS:
        source = sources.get(name)
        if isinstance(source, Mapping):
            _append_if_present(locations, ("sources", name, "sha256"), source.get("sha256"))
    canonical = sources.get("canonical_ledger")
    if isinstance(canonical, Mapping):
        _append_if_present(
            locations,
            ("sources", "canonical_ledger", "summary_sha256"),
            canonical.get("summary_sha256"),
        )
    adjudication = sources.get("noindex_re_adjudication")
    if not isinstance(adjudication, Mapping):
        return
    for key in (
        "input_receipt_sha256",
        "judge_receipt_set_digest",
        "caveat_set_digest",
        "decision_set_digest",
    ):
        _append_if_present(
            locations, ("sources", "noindex_re_adjudication", key), adjudication.get(key)
        )
    for index, receipt in enumerate(_mapping_rows(adjudication.get("judge_receipts"))):
        _append_if_present(
            locations,
            ("sources", "noindex_re_adjudication", "judge_receipts", index, "sha256"),
            receipt.get("sha256"),
        )
    provenance = adjudication.get("provenance")
    if isinstance(provenance, Mapping):
        base_revision = provenance.get("base_revision")
        if isinstance(base_revision, str) and _lower_hex(base_revision, 40):
            locations.append(
                RetainedReceiptOccurrence(
                    authority="journal",
                    path=(
                        "sources",
                        "noindex_re_adjudication",
                        "provenance",
                        "base_revision",
                    ),
                    value=base_revision,
                    detector="hex40",
                )
            )


def _ledger_baseline_digest(ledger: Sequence[Mapping[str, Any]]) -> str:
    return contract.digest_json(
        [{key: value for key, value in row.items() if key != "re_adjudication"} for row in ledger]
    )


def _journal_baseline_digest(journal: Mapping[str, Any]) -> str:
    baseline = dict(journal)
    baseline["urls"] = [
        {key: value for key, value in row.items() if key != "re_adjudication"}
        for row in _mapping_rows(journal.get("urls"))
    ]
    summary = contract.object_value(journal.get("summary"), "journal.summary")
    baseline["summary"] = {
        key: value for key, value in summary.items() if key != "noindex_re_adjudication"
    }
    sources = contract.object_value(journal.get("sources"), "journal.sources")
    baseline_sources = {
        key: value for key, value in sources.items() if key != "noindex_re_adjudication"
    }
    canonical = contract.object_value(
        baseline_sources.get("canonical_ledger"), "journal.sources.canonical_ledger"
    )
    mutable = {
        "sha256",
        "summary_sha256",
        "summary_schema_version",
        "summary_digest_algorithm",
        "summary",
    }
    baseline_sources["canonical_ledger"] = {
        key: value for key, value in canonical.items() if key not in mutable
    }
    baseline["sources"] = baseline_sources
    return contract.digest_json(baseline)


def _mapping_rows(raw: Any) -> list[Mapping[str, Any]]:
    if not isinstance(raw, list):
        return []
    return [row for row in raw if isinstance(row, Mapping)]


def _append_if_present(
    locations: list[RetainedReceiptOccurrence],
    path: tuple[str | int, ...],
    value: Any,
) -> None:
    if value is not None:
        _append_digest(locations, "journal", path, value)


def _append_digest(
    locations: list[RetainedReceiptOccurrence],
    authority: str,
    path: tuple[str | int, ...],
    value: Any,
) -> None:
    locations.append(
        RetainedReceiptOccurrence(
            authority="ledger" if authority == "ledger" else "journal",
            path=path,
            value=contract.sha256_value(value, f"retained digest at {path}"),
            detector="hex64",
        )
    )


def _safe_mutation_audit_id(value: str) -> bool:
    prefix = "mutation_act_apply_wordpress_draft_handoff_"
    suffix = value.removeprefix(prefix)
    return value.startswith(prefix) and _lower_hex(suffix, 12)


def _lower_hex(value: str, length: int) -> bool:
    return len(value) == length and all(character in "0123456789abcdef" for character in value)
