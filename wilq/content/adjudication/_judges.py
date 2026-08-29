from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from pathlib import PurePosixPath
from typing import Any, cast

from . import _contract as contract
from ._models import (
    CaveatCorrection,
    CaveatDisposition,
    CaveatStatus,
    EvidenceCaveat,
    JudgeLineage,
    JudgeReceipt,
    JudgeRowLineage,
    SourceArtifact,
)
from ._policy import (
    FILE_RECEIPT_ALGORITHM,
    PRODUCTION_INPUT_RECEIPT_SHA256,
    PRODUCTION_JUDGE_RECEIPTS,
    SITEMAP_INVENTORY_SHA256,
)

RECEIPT_SET_SCHEMA_VERSION = "content_noindex_judge_receipt_set_v1"
CAVEAT_SET_SCHEMA_VERSION = "content_noindex_caveat_set_v1"
JUDGE_ROLES = ("technical", "strategy", "tie_breaker")
RECEIPT_KEYS = frozenset({"role", "artifact_reference", "sha256", "algorithm"})
CAVEAT_KEYS = frozenset(
    {
        "caveat_id",
        "source_role",
        "artifact_reference",
        "source_path",
        "text",
        "evidence_ids",
        "status",
        "disposition",
        "correction",
    }
)
CORRECTION_KEYS = frozenset(
    {
        "statement_pl",
        "source_reference",
        "source_sha256",
        "evidence_ids",
        "observed_entry_count",
        "unique_path_count",
        "duplicate_path",
        "duplicate_sitemaps",
    }
)

TECHNICAL_CLASSIFICATIONS = frozenset(
    {
        "keep_candidate",
        "merge_redirect_candidate",
        "needs_content_review",
        "noindex_candidate",
        "remove_candidate",
    }
)
STRATEGY_RECOMMENDATIONS = frozenset(
    {"keep_refresh", "merge_redirect", "needs_more_evidence", "noindex", "remove"}
)
TIE_BREAKER_DECISIONS = frozenset(
    {"keep_refresh", "merge_redirect", "needs_more_evidence", "noindex", "remove"}
)
ACTION_BY_RECOMMENDATION = {
    "keep_refresh": "keep",
    "merge_redirect": "redirect",
    "needs_more_evidence": "blocked",
    "noindex": "noindex",
    "remove": "blocked",
}
REDIRECT_BASIS_SUFFIX = (
    " Cel przekierowania zweryfikowano jako odrębny, bezpieczny w rejestrze 214; "
    "docelowy wiersz kończy jako keep, bez pętli i łańcucha."
)
GA4_EVIDENCE_ID = "ev_refresh_refresh_google_analytics_4_a251af59265b"
AHREFS_EVIDENCE_ID = "ev_refresh_refresh_ahrefs_cd955c67ff83"
TECHNICAL_CAVEAT_CODES = (
    "technical_cohort_exact_text_only",
    "technical_dev_noindex_is_global",
    "technical_redirect_requires_reviewed_action",
)
STRATEGY_CAVEAT_CODES = (
    "strategy_gsc_single_day_partial",
    "strategy_wordpress_inventory_partial",
    "strategy_ga4_ahrefs_not_url_level",
    "strategy_sitemap_scope_discrepancy",
)
TIE_BREAKER_CAVEAT_CODES = (
    "tie_gsc_absence_not_no_demand",
    "tie_gsc_exact_signal_scope",
    "tie_wordpress_inventory_partial",
    "tie_ahrefs_http403_no_url_backlink_proof",
    "tie_ga4_stale_no_url_level",
    "tie_no_destructive_remove_without_backlink_proof",
    "tie_redirect_requires_content_preconditions",
)


def validate_judge_artifacts(
    artifacts: Sequence[SourceArtifact],
    integrated_packet: Sequence[Mapping[str, Any]],
    *,
    integrated_packet_sha256: str,
    ledger_rows: Mapping[str, Mapping[str, Any]],
) -> JudgeLineage:
    if len(artifacts) != len(JUDGE_ROLES):
        raise contract.AdjudicationError("Exactly three judge artifacts are required.")
    by_role: dict[str, SourceArtifact] = {}
    payloads: dict[str, Any] = {}
    for artifact in artifacts:
        if artifact.role not in JUDGE_ROLES or artifact.role in by_role:
            raise contract.AdjudicationError("Judge artifact roles must be exact and unique.")
        reference = _artifact_reference(artifact.artifact_reference)
        contract.sha256_value(artifact.expected_sha256, f"{artifact.role} judge SHA-256")
        observed = hashlib.sha256(artifact.content).hexdigest()
        if observed != artifact.expected_sha256:
            raise contract.AdjudicationError(
                f"SHA-256 mismatch for {artifact.role} judge artifact."
            )
        by_role[artifact.role] = SourceArtifact(
            role=artifact.role,
            artifact_reference=reference,
            content=artifact.content,
            expected_sha256=artifact.expected_sha256,
        )
        payloads[artifact.role] = contract.parse_json(
            artifact.content,
            f"{artifact.role} judge artifact",
        )
    if set(by_role) != set(JUDGE_ROLES):
        raise contract.AdjudicationError("Judge artifact role set is incomplete.")
    receipts = tuple(
        JudgeReceipt(
            role=role,
            artifact_reference=by_role[role].artifact_reference,
            sha256=by_role[role].expected_sha256,
        )
        for role in JUDGE_ROLES
    )
    _validate_production_bundle_binding(receipts, integrated_packet_sha256)
    rows = _validate_judge_packet_relationship(
        payloads,
        integrated_packet,
        ledger_rows=ledger_rows,
    )
    caveats = _derive_caveats(payloads, by_role)
    return JudgeLineage(
        receipts=receipts,
        receipt_set_digest=judge_receipt_set_digest(receipts),
        caveats=caveats,
        caveat_set_digest=caveat_set_digest(caveats),
        rows=rows,
    )


def validate_retained_judge_receipts(raw: Any) -> tuple[JudgeReceipt, ...]:
    values = contract.array_value(raw, "judge_receipts")
    if len(values) != len(JUDGE_ROLES):
        raise contract.AdjudicationError("Retained judge receipt count is not exact.")
    receipts: list[JudgeReceipt] = []
    for index, (raw_receipt, expected_role) in enumerate(zip(values, JUDGE_ROLES, strict=True)):
        receipt = contract.object_value(raw_receipt, f"judge_receipts[{index}]")
        if set(receipt) != RECEIPT_KEYS or receipt.get("role") != expected_role:
            raise contract.AdjudicationError("Retained judge receipt schema/order is not exact.")
        if receipt.get("algorithm") != FILE_RECEIPT_ALGORITHM:
            raise contract.AdjudicationError("Retained judge receipt algorithm is not exact.")
        receipts.append(
            JudgeReceipt(
                role=expected_role,
                artifact_reference=_artifact_reference(receipt.get("artifact_reference")),
                sha256=contract.sha256_value(
                    receipt.get("sha256"), f"retained {expected_role} judge SHA-256"
                ),
            )
        )
    return tuple(receipts)


def validate_retained_caveats(raw: Any) -> tuple[EvidenceCaveat, ...]:
    values = contract.array_value(raw, "caveats")
    caveats: list[EvidenceCaveat] = []
    seen_ids: set[str] = set()
    for index, raw_caveat in enumerate(values):
        caveat = contract.object_value(raw_caveat, f"caveats[{index}]")
        if set(caveat) != CAVEAT_KEYS:
            raise contract.AdjudicationError("Retained caveat schema is not exact.")
        caveat_id = contract.string_value(caveat.get("caveat_id"), "caveat_id")
        if caveat_id in seen_ids:
            raise contract.AdjudicationError("Retained caveat IDs must be unique.")
        seen_ids.add(caveat_id)
        evidence_ids = contract.string_list(caveat.get("evidence_ids"), "caveat evidence_ids")
        if evidence_ids != sorted(evidence_ids) or len(evidence_ids) != len(set(evidence_ids)):
            raise contract.AdjudicationError("Retained caveat evidence IDs are not canonical.")
        status = contract.string_value(caveat.get("status"), "caveat status")
        disposition = contract.string_value(caveat.get("disposition"), "caveat disposition")
        correction = _validated_correction(caveat.get("correction"))
        if (status, disposition, correction is None) not in {
            ("active", "applies", True),
            ("superseded", "corrected_by_canonical_sitemap_inventory", False),
        }:
            raise contract.AdjudicationError("Retained caveat disposition is not coherent.")
        caveats.append(
            EvidenceCaveat(
                caveat_id=caveat_id,
                source_role=contract.string_value(caveat.get("source_role"), "caveat role"),
                artifact_reference=_artifact_reference(caveat.get("artifact_reference")),
                source_path=contract.string_value(caveat.get("source_path"), "caveat path"),
                text=contract.string_value(caveat.get("text"), "caveat text"),
                evidence_ids=tuple(evidence_ids),
                status=cast(CaveatStatus, status),
                disposition=cast(CaveatDisposition, disposition),
                correction=correction,
            )
        )
    return tuple(caveats)


def _validated_correction(raw: Any) -> CaveatCorrection | None:
    if raw is None:
        return None
    value = contract.object_value(raw, "caveat correction")
    if set(value) != CORRECTION_KEYS:
        raise contract.AdjudicationError("Caveat correction schema is not exact.")
    evidence_ids = contract.string_list(value.get("evidence_ids"), "caveat correction evidence_ids")
    duplicate_sitemaps = contract.string_list(
        value.get("duplicate_sitemaps"), "caveat correction duplicate_sitemaps"
    )
    if evidence_ids != sorted(evidence_ids) or duplicate_sitemaps != sorted(duplicate_sitemaps):
        raise contract.AdjudicationError("Caveat correction arrays are not canonical.")
    observed = value.get("observed_entry_count")
    unique = value.get("unique_path_count")
    if type(observed) is not int or type(unique) is not int:
        raise contract.AdjudicationError("Caveat correction counts must be integers.")
    if len(duplicate_sitemaps) != 2:
        raise contract.AdjudicationError("Caveat correction duplicate sitemap set is not exact.")
    return CaveatCorrection(
        statement_pl=contract.string_value(value.get("statement_pl"), "correction statement"),
        source_reference=contract.string_value(
            value.get("source_reference"), "correction source reference"
        ),
        source_sha256=contract.sha256_value(
            value.get("source_sha256"), "correction source SHA-256"
        ),
        evidence_ids=tuple(evidence_ids),
        observed_entry_count=observed,
        unique_path_count=unique,
        duplicate_path=contract.string_value(
            value.get("duplicate_path"), "correction duplicate path"
        ),
        duplicate_sitemaps=cast(tuple[str, str], tuple(duplicate_sitemaps)),
    )


def judge_receipt_set_digest(receipts: Sequence[JudgeReceipt]) -> str:
    return contract.digest_json(
        {
            "schema_version": RECEIPT_SET_SCHEMA_VERSION,
            "judge_receipts": [receipt.as_json() for receipt in receipts],
        }
    )


def caveat_set_digest(caveats: Sequence[EvidenceCaveat]) -> str:
    return contract.digest_json(
        {
            "schema_version": CAVEAT_SET_SCHEMA_VERSION,
            "caveats": [caveat.as_json() for caveat in caveats],
        }
    )


def _derive_caveats(
    payloads: Mapping[str, Any],
    artifacts: Mapping[str, SourceArtifact],
) -> tuple[EvidenceCaveat, ...]:
    technical = contract.object_value(payloads["technical"], "technical judge artifact")
    scope = contract.object_value(technical.get("scope"), "technical judge scope")
    technical_texts = contract.string_list(
        scope.get("limitations"),
        "technical judge scope limitations",
    )
    strategy_rows = contract.object_list(payloads["strategy"], "strategy judge artifact")
    if not strategy_rows:
        raise contract.AdjudicationError("Strategy judge artifact has no rows.")
    strategy_texts = contract.string_list(
        strategy_rows[0].get("evidence_limitations"),
        "strategy evidence limitations",
    )
    scope_caveat = contract.string_value(
        strategy_rows[0].get("scope_caveat"),
        "strategy scope caveat",
    )
    for index, row in enumerate(strategy_rows[1:], start=1):
        if row.get("evidence_limitations") != strategy_rows[0].get("evidence_limitations"):
            raise contract.AdjudicationError(f"Strategy evidence limitations drift at row {index}.")
        if row.get("scope_caveat") != scope_caveat:
            raise contract.AdjudicationError(f"Strategy scope caveat drift at row {index}.")
    tie_breaker = contract.object_value(payloads["tie_breaker"], "tie-breaker judge artifact")
    tie_texts = contract.string_list(
        tie_breaker.get("global_evidence_caveats"),
        "tie-breaker global evidence caveats",
    )
    if (
        len(technical_texts) != len(TECHNICAL_CAVEAT_CODES)
        or len(strategy_texts) + 1 != len(STRATEGY_CAVEAT_CODES)
        or len(tie_texts) != len(TIE_BREAKER_CAVEAT_CODES)
    ):
        raise contract.AdjudicationError("Judge caveat source shape is not exact.")
    records = [
        *_caveat_records(
            "technical",
            artifacts["technical"].artifact_reference,
            "/scope/limitations",
            TECHNICAL_CAVEAT_CODES,
            technical_texts,
            ((), (), ()),
        ),
        *_caveat_records(
            "strategy",
            artifacts["strategy"].artifact_reference,
            "/0/evidence_limitations",
            STRATEGY_CAVEAT_CODES[:3],
            strategy_texts,
            (
                (contract.GSC_PARTIAL_EVIDENCE_ID,),
                (contract.WORDPRESS_PARTIAL_EVIDENCE_ID,),
                (AHREFS_EVIDENCE_ID, GA4_EVIDENCE_ID),
            ),
        ),
        EvidenceCaveat(
            caveat_id=STRATEGY_CAVEAT_CODES[3],
            source_role="strategy",
            artifact_reference=artifacts["strategy"].artifact_reference,
            source_path="/0/scope_caveat",
            text=scope_caveat,
            evidence_ids=(contract.WORDPRESS_PARTIAL_EVIDENCE_ID,),
            status="superseded",
            disposition="corrected_by_canonical_sitemap_inventory",
            correction=_sitemap_scope_correction(),
        ),
        *_caveat_records(
            "tie_breaker",
            artifacts["tie_breaker"].artifact_reference,
            "/global_evidence_caveats",
            TIE_BREAKER_CAVEAT_CODES,
            tie_texts,
            (
                (contract.GSC_PARTIAL_EVIDENCE_ID,),
                (contract.GSC_PARTIAL_EVIDENCE_ID,),
                (contract.WORDPRESS_PARTIAL_EVIDENCE_ID,),
                (AHREFS_EVIDENCE_ID,),
                (GA4_EVIDENCE_ID,),
                (AHREFS_EVIDENCE_ID,),
                (),
            ),
        ),
    ]
    result = tuple(records)
    _validate_caveat_pointers(result, payloads)
    return result


def _sitemap_scope_correction() -> CaveatCorrection:
    return CaveatCorrection(
        statement_pl=(
            "215 wpisów <loc> w sitemapach dev odpowiada 214 unikalnym ścieżkom; "
            "/baza-wiedzy/ występuje w page-sitemap.xml i category-sitemap.xml, "
            "więc nie istnieje 215. unikalny URL."
        ),
        source_reference="docs/content-sitemap-inventory-20260828.json",
        source_sha256=SITEMAP_INVENTORY_SHA256,
        evidence_ids=(contract.WORDPRESS_PARTIAL_EVIDENCE_ID,),
        observed_entry_count=215,
        unique_path_count=214,
        duplicate_path="/baza-wiedzy/",
        duplicate_sitemaps=("category-sitemap.xml", "page-sitemap.xml"),
    )


def _caveat_records(
    role: str,
    artifact_reference: str,
    source_path: str,
    codes: Sequence[str],
    texts: Sequence[str],
    evidence_ids: Sequence[tuple[str, ...]],
) -> tuple[EvidenceCaveat, ...]:
    return tuple(
        EvidenceCaveat(
            caveat_id=code,
            source_role=role,
            artifact_reference=artifact_reference,
            source_path=f"{source_path}/{index}",
            text=text,
            evidence_ids=ids,
            status="active",
            disposition="applies",
            correction=None,
        )
        for index, (code, text, ids) in enumerate(zip(codes, texts, evidence_ids, strict=True))
    )


def _validate_caveat_pointers(
    caveats: Sequence[EvidenceCaveat],
    payloads: Mapping[str, Any],
) -> None:
    for caveat in caveats:
        payload = payloads.get(caveat.source_role)
        if payload is None:
            raise contract.AdjudicationError(f"Caveat source role is missing: {caveat.source_role}")
        resolved = _resolve_json_pointer(payload, caveat.source_path)
        if not isinstance(resolved, str) or resolved != caveat.text:
            raise contract.AdjudicationError(
                f"Caveat source pointer does not resolve to its exact text: {caveat.caveat_id}"
            )


def _resolve_json_pointer(payload: Any, pointer: str) -> Any:
    if pointer == "":
        return payload
    if not pointer.startswith("/"):
        raise contract.AdjudicationError("JSON Pointer must start with '/'.")
    current = payload
    for raw_token in pointer[1:].split("/"):
        token = _decode_pointer_token(raw_token)
        if isinstance(current, Mapping):
            if token not in current:
                raise contract.AdjudicationError(f"JSON Pointer object key is missing: {token}")
            current = current[token]
            continue
        if isinstance(current, list):
            ascii_index = bool(token) and all("0" <= character <= "9" for character in token)
            if not ascii_index or (len(token) > 1 and token.startswith("0")):
                raise contract.AdjudicationError(f"JSON Pointer array index is invalid: {token}")
            index = int(token)
            if index >= len(current):
                raise contract.AdjudicationError(f"JSON Pointer array index is missing: {token}")
            current = current[index]
            continue
        raise contract.AdjudicationError("JSON Pointer traverses a scalar value.")
    return current


def _decode_pointer_token(token: str) -> str:
    result: list[str] = []
    index = 0
    while index < len(token):
        character = token[index]
        if character != "~":
            result.append(character)
            index += 1
            continue
        if index + 1 >= len(token) or token[index + 1] not in {"0", "1"}:
            raise contract.AdjudicationError("JSON Pointer has an invalid '~' escape.")
        result.append("~" if token[index + 1] == "0" else "/")
        index += 2
    return "".join(result)


def _validate_judge_packet_relationship(
    payloads: Mapping[str, Any],
    integrated_packet: Sequence[Mapping[str, Any]],
    *,
    ledger_rows: Mapping[str, Mapping[str, Any]],
) -> tuple[JudgeRowLineage, ...]:
    technical = contract.object_value(payloads["technical"], "technical judge artifact")
    strategy_rows = contract.object_list(payloads["strategy"], "strategy judge artifact")
    tie_breaker = contract.object_value(payloads["tie_breaker"], "tie-breaker judge artifact")
    technical_rows = contract.object_list(
        technical.get("rows"),
        "technical judge rows",
    )
    tie_rows = contract.object_list(tie_breaker.get("decisions"), "tie-breaker decisions")
    packet_by_url = _rows_by_url(integrated_packet, "integrated decision packet")
    technical_by_url = _rows_by_url(technical_rows, "technical judge rows")
    strategy_by_url = _rows_by_url(strategy_rows, "strategy judge rows")
    tie_by_url = _rows_by_url(tie_rows, "tie-breaker decisions")
    if set(technical_by_url) != set(packet_by_url) or set(strategy_by_url) != set(packet_by_url):
        raise contract.AdjudicationError("Judge URL sets do not match the integrated packet.")

    conflicts: set[str] = set()
    for url in packet_by_url:
        classification = contract.string_value(
            technical_by_url[url].get("classification"),
            f"technical classification for {url}",
        )
        recommendation = contract.string_value(
            strategy_by_url[url].get("recommendation"),
            f"strategy recommendation for {url}",
        )
        if classification not in TECHNICAL_CLASSIFICATIONS:
            raise contract.AdjudicationError(f"Unsupported technical classification: {url}")
        if recommendation not in STRATEGY_RECOMMENDATIONS:
            raise contract.AdjudicationError(f"Unsupported strategy recommendation: {url}")
        if (
            classification in {"noindex_candidate", "remove_candidate"}
            and recommendation == "merge_redirect"
        ):
            conflicts.add(url)
    if set(tie_by_url) != conflicts:
        raise contract.AdjudicationError(
            "Tie-breaker URL set does not match exact judge conflicts."
        )

    row_lineage: list[JudgeRowLineage] = []
    for url in sorted(packet_by_url):
        integrated = packet_by_url[url]
        path = contract.dev_path(url, f"integrated URL {url}")
        ledger_row = ledger_rows.get(path)
        if ledger_row is None:
            raise contract.AdjudicationError(f"Judge URL is missing from the ledger: {url}")
        row_lineage.append(
            _validate_integrated_row(
                url,
                integrated,
                technical=technical_by_url[url],
                strategy=strategy_by_url[url],
                tie_breaker=tie_by_url.get(url),
                ledger_row=ledger_row,
            )
        )
    return tuple(row_lineage)


def _validate_integrated_row(
    url: str,
    integrated: Mapping[str, Any],
    *,
    technical: Mapping[str, Any],
    strategy: Mapping[str, Any],
    tie_breaker: Mapping[str, Any] | None,
    ledger_row: Mapping[str, Any],
) -> JudgeRowLineage:
    selected = tie_breaker or strategy
    key = "decision" if tie_breaker is not None else "recommendation"
    recommendation = contract.string_value(selected.get(key), f"selected decision for {url}")
    allowed = TIE_BREAKER_DECISIONS if tie_breaker is not None else STRATEGY_RECOMMENDATIONS
    if recommendation not in allowed:
        raise contract.AdjudicationError(f"Unsupported selected judge decision: {url}")
    expected_action = ACTION_BY_RECOMMENDATION[recommendation]
    if integrated.get("proposed_disposition") != expected_action:
        raise contract.AdjudicationError(
            f"Integrated action does not match the selected judge decision: {url}"
        )
    target_key = "proposed_target_url" if tie_breaker is not None else "candidate_target_url"
    expected_target = selected.get(target_key) if expected_action == "redirect" else None
    if integrated.get("target_url") != expected_target:
        raise contract.AdjudicationError(
            f"Integrated target does not match the selected judge decision: {url}"
        )
    _validate_confidence(url, integrated, tie_breaker=tie_breaker)
    expected_basis = _canonical_decision_basis(
        url,
        expected_action,
        technical=technical,
        strategy=strategy,
        tie_breaker=tie_breaker,
    )
    if integrated.get("decision_basis") != expected_basis:
        raise contract.AdjudicationError(
            f"Integrated decision basis does not preserve judge reasoning: {url}"
        )
    _validate_evidence_union(
        url,
        integrated,
        strategy=strategy,
        tie_breaker=tie_breaker,
        ledger_row=ledger_row,
    )
    return JudgeRowLineage(
        url=url,
        technical_row_digest=contract.digest_json(technical),
        strategy_row_digest=contract.digest_json(strategy),
        tie_breaker_row_digest=(
            contract.digest_json(tie_breaker) if tie_breaker is not None else None
        ),
        selected_authority="tie_breaker" if tie_breaker is not None else "strategy",
        confidence_authority=(
            "tie_breaker" if tie_breaker is not None else "integrator_decision_packet"
        ),
    )


def _validate_confidence(
    url: str,
    integrated: Mapping[str, Any],
    *,
    tie_breaker: Mapping[str, Any] | None,
) -> None:
    observed = contract.string_value(integrated.get("confidence"), f"confidence for {url}")
    if observed not in contract.CONFIDENCE_VALUES:
        raise contract.AdjudicationError(f"Unsupported integrated confidence: {url}")
    if tie_breaker is None:
        return
    expected = contract.string_value(
        tie_breaker.get("confidence"),
        f"tie-breaker confidence for {url}",
    )
    if expected not in contract.CONFIDENCE_VALUES or observed != expected:
        raise contract.AdjudicationError(
            f"Integrated confidence does not match the tie-breaker: {url}"
        )


def _canonical_decision_basis(
    url: str,
    action: str,
    *,
    technical: Mapping[str, Any],
    strategy: Mapping[str, Any],
    tie_breaker: Mapping[str, Any] | None,
) -> str:
    strategy_reason = contract.string_value(
        strategy.get("reason_pl"),
        f"strategy reason for {url}",
    )
    if tie_breaker is not None:
        tie_reason = contract.string_value(
            tie_breaker.get("reason_pl"),
            f"tie-breaker reason for {url}",
        )
        basis = f"Tie-breaker dla konfliktu techniczno-strategicznego: {tie_reason}"
    elif strategy.get("recommendation") == "remove":
        basis = (
            f"Blokada bezpieczeństwa: strateg proponował remove ({strategy_reason}), ale brak "
            "dowodu backlinkowego na poziomie URL. Bez takiego dowodu usunięcie nie jest "
            "dopuszczalne."
        )
    else:
        technical_reason = contract.string_value(
            technical.get("rationale"),
            f"technical rationale for {url}",
        )
        basis = f"Werdykt stratega: {strategy_reason} Ocena techniczna: {technical_reason}"
    return basis + (REDIRECT_BASIS_SUFFIX if action == "redirect" else "")


def _validate_evidence_union(
    url: str,
    integrated: Mapping[str, Any],
    *,
    strategy: Mapping[str, Any],
    tie_breaker: Mapping[str, Any] | None,
    ledger_row: Mapping[str, Any],
) -> None:
    strategy_ids = _evidence_ids(strategy.get("evidence_ids"), f"strategy evidence for {url}")
    ledger_ids = _evidence_ids(ledger_row.get("evidence_ids"), f"ledger evidence for {url}")
    expected = sorted(set(strategy_ids) | set(ledger_ids))
    integrated_ids = _evidence_ids(
        integrated.get("evidence_ids"),
        f"integrated evidence for {url}",
    )
    if integrated_ids != expected:
        raise contract.AdjudicationError(
            f"Integrated evidence is not the exact judge/ledger union: {url}"
        )
    if tie_breaker is not None:
        tie_ids = _evidence_ids(
            tie_breaker.get("evidence_ids"),
            f"tie-breaker evidence for {url}",
        )
        if not set(tie_ids).issubset(expected):
            raise contract.AdjudicationError(
                f"Tie-breaker evidence is outside the canonical evidence union: {url}"
            )


def _evidence_ids(value: Any, context: str) -> list[str]:
    values = contract.string_list(value, context)
    if len(values) != len(set(values)):
        raise contract.AdjudicationError(f"Duplicate evidence ID in {context}.")
    return values


def _validate_production_bundle_binding(
    receipts: Sequence[JudgeReceipt],
    integrated_packet_sha256: str,
) -> bool:
    contract.sha256_value(integrated_packet_sha256, "integrated packet SHA-256")
    production_judges = tuple(receipts) == PRODUCTION_JUDGE_RECEIPTS
    production_packet = integrated_packet_sha256 == PRODUCTION_INPUT_RECEIPT_SHA256
    if production_judges != production_packet:
        raise contract.AdjudicationError(
            "Production judges and integrated packet must use the exact reviewed receipt bundle."
        )
    return production_judges


def _rows_by_url(
    rows: Sequence[Mapping[str, Any]],
    context: str,
) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for index, raw in enumerate(rows):
        row = contract.object_value(raw, f"{context}[{index}]")
        url = contract.string_value(row.get("url"), f"{context}[{index}].url")
        contract.dev_path(url, f"{context}[{index}].url")
        if url in result:
            raise contract.AdjudicationError(f"Duplicate judge URL in {context}: {url}")
        result[url] = row
    return result


def _artifact_reference(value: Any) -> str:
    reference = contract.string_value(value, "judge artifact reference")
    if (
        PurePosixPath(reference).name != reference
        or "/" in reference
        or "\\" in reference
        or not reference.endswith(".json")
    ):
        raise contract.AdjudicationError("Judge artifact reference must be a JSON basename.")
    return reference
