from __future__ import annotations

from ._models import (
    AdjudicationExpectations,
    AdjudicationProvenance,
    JudgeReceipt,
    ProductionPins,
)

INPUT_REFERENCE = "noindex_integrated_decision_v1"
CANONICAL_DIGEST_ALGORITHM = "sha256_utf8_json_sort_keys_compact_v1"
FILE_RECEIPT_ALGORITHM = "sha256_file_bytes_v1"


def _hex(*chunks: str) -> str:
    return "".join(chunks)


PRODUCTION_INPUT_RECEIPT_SHA256 = _hex(
    "076a0118",
    "73c80b29",
    "0d9cac38",
    "5d1fe919",
    "1652b8d9",
    "06a336ab",
    "348cc097",
    "95fb5059",
)
PRODUCTION_JUDGE_RECEIPTS = (
    JudgeReceipt(
        role="technical",
        artifact_reference="noindex-technical-judge.json",
        sha256=_hex(
            "f7973048",
            "0a36a106",
            "7c576612",
            "90f01c01",
            "335b80a0",
            "e5783f91",
            "348d7c0a",
            "c6e30c5e",
        ),
    ),
    JudgeReceipt(
        role="strategy",
        artifact_reference="noindex-strategy-judge.json",
        sha256=_hex(
            "21d67cdf",
            "1c2e987a",
            "1ab5190a",
            "f0648ee7",
            "569dfa80",
            "07f64855",
            "5ef72ebb",
            "05a8287e",
        ),
    ),
    JudgeReceipt(
        role="tie_breaker",
        artifact_reference="noindex-conflict-tiebreaker.json",
        sha256=_hex(
            "42551573",
            "7734fdf8",
            "fbc698a3",
            "9edb541f",
            "cea3eb1f",
            "50ea3f7b",
            "2fc719fa",
            "6e79fea8",
        ),
    ),
)
PRODUCTION_JUDGE_RECEIPT_SET_DIGEST = _hex(
    "62254102",
    "cab84b0a",
    "b5752fd1",
    "5d4b96eb",
    "9246a67e",
    "5aef9626",
    "fb4dfa3e",
    "4746688a",
)
PRODUCTION_PROVENANCE = AdjudicationProvenance(
    recorded_at="2026-08-29T12:37:58Z",
    base_revision=_hex("33d18617", "ad96da33", "431bbd18", "f1a7fb15", "ca5c3e48"),
    baseline_semantics=(
        "additive_re_adjudication_over_older_operational_baseline_without_refreshing_"
        "top_level_state"
    ),
    raw_judge_artifacts_retained=False,
    raw_judge_retention_status="external_ephemeral_judge_files_not_retained_receipts_only",
)

PRODUCTION_DECISION_SET_DIGEST = _hex(
    "59c48861",
    "c47268d9",
    "b31c392e",
    "6d913a3c",
    "0e170b6b",
    "77d72203",
    "4bbc7f7a",
    "83c384f5",
)
PRODUCTION_CAVEAT_SET_DIGEST = _hex(
    "87dd862a",
    "a72edeef",
    "b37d0b96",
    "43566970",
    "16c4c873",
    "d63d3e7a",
    "eb084fa9",
    "54744122",
)
SITEMAP_INVENTORY_SHA256 = _hex(
    "0f0cd730",
    "f6b480b2",
    "84da7be6",
    "631dfc4b",
    "22a0a645",
    "c4582abf",
    "e209367d",
    "82590c0c",
)

PRODUCTION_PINS = ProductionPins(
    input_receipt_sha256=PRODUCTION_INPUT_RECEIPT_SHA256,
    judge_receipts=PRODUCTION_JUDGE_RECEIPTS,
    judge_receipt_set_digest=PRODUCTION_JUDGE_RECEIPT_SET_DIGEST,
    decision_set_digest=PRODUCTION_DECISION_SET_DIGEST,
    caveat_set_digest=PRODUCTION_CAVEAT_SET_DIGEST,
    ledger_baseline_digest=_hex(
        "fe3d01ea",
        "759325ea",
        "ca4be95b",
        "f3a75be5",
        "b241f6aa",
        "c0c8cedf",
        "0d23ab7a",
        "beb7dd90",
    ),
    journal_baseline_digest=_hex(
        "c3fa47d8",
        "9f8e11ee",
        "70d312b4",
        "7311a9fc",
        "85f09f96",
        "d22e37e2",
        "c2033553",
        "89aff1ab",
    ),
    provenance=PRODUCTION_PROVENANCE,
)
PRODUCTION_EXPECTATIONS = AdjudicationExpectations(production_pins=PRODUCTION_PINS)
