from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pytest

from scripts import reconcile_content_noindex_adjudication as cli
from wilq.content.adjudication import (
    AdjudicationError,
    NoindexAdjudicationSources,
    ReconciliationResult,
    SourceArtifact,
    validate_retained_noindex_authorities,
)
from wilq.content.adjudication._judges import (
    REDIRECT_BASIS_SUFFIX,
    _resolve_json_pointer,
    _validate_caveat_pointers,
)
from wilq.content.adjudication._models import AdjudicationExpectations, EvidenceCaveat
from wilq.content.adjudication._service import reconcile_noindex_adjudication as reconcile_engine

REPO_ROOT = Path(__file__).resolve().parents[2]
LEDGER_PATH = REPO_ROOT / "docs/content-canonical-ledger-20260828.jsonl"
JOURNAL_PATH = REPO_ROOT / "docs/content-dev-state-journal-20260828.json"


def _hex(*chunks: str) -> str:
    return "".join(chunks)


INPUT_RECEIPT = _hex(
    "076a0118",
    "73c80b29",
    "0d9cac38",
    "5d1fe919",
    "1652b8d9",
    "06a336ab",
    "348cc097",
    "95fb5059",
)
JUDGE_SET_DIGEST = _hex(
    "62254102",
    "cab84b0a",
    "b5752fd1",
    "5d4b96eb",
    "9246a67e",
    "5aef9626",
    "fb4dfa3e",
    "4746688a",
)
DECISION_SET_DIGEST = _hex(
    "59c48861",
    "c47268d9",
    "b31c392e",
    "6d913a3c",
    "0e170b6b",
    "77d72203",
    "4bbc7f7a",
    "83c384f5",
)
CAVEAT_SET_DIGEST = _hex(
    "87dd862a",
    "a72edeef",
    "b37d0b96",
    "43566970",
    "16c4c873",
    "d63d3e7a",
    "eb084fa9",
    "54744122",
)
BASE_REVISION = _hex(
    "33d18617",
    "ad96da33",
    "431bbd18",
    "f1a7fb15",
    "ca5c3e48",
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


def test_public_validator_accepts_exact_pinned_production_authorities() -> None:
    ledger_bytes = LEDGER_PATH.read_bytes()
    journal_bytes = JOURNAL_PATH.read_bytes()

    validated = validate_retained_noindex_authorities(ledger_bytes, journal_bytes)
    ledger = _parse_ledger(ledger_bytes)
    journal = json.loads(journal_bytes)
    reviewed = [row["re_adjudication"] for row in ledger if "re_adjudication" in row]
    source = journal["sources"]["noindex_re_adjudication"]

    assert validated.decision_set_digest == DECISION_SET_DIGEST
    assert validated.caveat_set_digest == CAVEAT_SET_DIGEST
    assert len(validated.receipt_occurrences) > 900
    assert len(ledger) == len(journal["urls"]) == 214
    assert _counts(ledger, "final_disposition") == {
        "keep": 57,
        "noindex": 87,
        "redirect": 46,
        "remove": 24,
    }
    assert _counts(reviewed, "recommended_action") == {
        "blocked": 9,
        "keep": 25,
        "noindex": 17,
        "redirect": 36,
    }
    assert sum(row["status"] == "resolved" for row in reviewed) == 78
    assert sum(row["status"] == "blocked" for row in reviewed) == 9
    assert sum(row["selected_authority"] == "tie_breaker" for row in reviewed) == 13
    assert sum(row["confidence_authority"] == "tie_breaker" for row in reviewed) == 13
    assert (
        sum(row["confidence_authority"] == "integrator_decision_packet" for row in reviewed) == 74
    )
    assert all(row["input_receipt_sha256"] == INPUT_RECEIPT for row in reviewed)
    assert all(row["judge_receipt_set_digest"] == JUDGE_SET_DIGEST for row in reviewed)
    assert all(row["caveat_set_digest"] == CAVEAT_SET_DIGEST for row in reviewed)
    assert len(source["caveats"]) == 14
    assert sum(caveat["status"] == "active" for caveat in source["caveats"]) == 13
    assert all("*" not in caveat["source_path"] for caveat in source["caveats"])
    corrected = next(
        caveat
        for caveat in source["caveats"]
        if caveat["caveat_id"] == "strategy_sitemap_scope_discrepancy"
    )
    assert corrected["status"] == "superseded"
    assert corrected["disposition"] == "corrected_by_canonical_sitemap_inventory"
    assert corrected["correction"] == {
        "statement_pl": (
            "215 wpisów <loc> w sitemapach dev odpowiada 214 unikalnym ścieżkom; "
            "/baza-wiedzy/ występuje w page-sitemap.xml i category-sitemap.xml, "
            "więc nie istnieje 215. unikalny URL."
        ),
        "source_reference": "docs/content-sitemap-inventory-20260828.json",
        "source_sha256": SITEMAP_INVENTORY_SHA256,
        "evidence_ids": ["ev_refresh_refresh_wordpress_ekologus_722938c36872"],
        "observed_entry_count": 215,
        "unique_path_count": 214,
        "duplicate_path": "/baza-wiedzy/",
        "duplicate_sitemaps": ["category-sitemap.xml", "page-sitemap.xml"],
    }
    assert source["provenance"] == {
        "recorded_at": "2026-08-29T12:37:58Z",
        "base_revision": BASE_REVISION,
        "baseline_semantics": (
            "additive_re_adjudication_over_older_operational_baseline_without_refreshing_"
            "top_level_state"
        ),
        "raw_judge_artifacts_retained": False,
        "raw_judge_retention_status": ("external_ephemeral_judge_files_not_retained_receipts_only"),
    }
    assert all(
        row[flag] is False
        for row in ledger
        for flag in ("publish_allowed", "write_authorized", "robot_ready")
    )


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ("receipts", "source pins"),
        ("decision_swap", "decision-set digest"),
        ("caveat_drift", "caveat-set digest"),
    ),
)
def test_public_validator_rejects_coherent_authority_rewrites(
    mutation: str,
    message: str,
) -> None:
    ledger = _parse_ledger(LEDGER_PATH.read_bytes())
    journal = json.loads(JOURNAL_PATH.read_bytes())
    if mutation == "receipts":
        _rewrite_receipts(ledger, journal)
    elif mutation == "decision_swap":
        _swap_keep_and_noindex(ledger)
    else:
        _rewrite_caveat_set(ledger, journal)
    ledger_bytes, journal_bytes = _refresh_pair(ledger, journal)

    with pytest.raises(AdjudicationError, match=message):
        validate_retained_noindex_authorities(ledger_bytes, journal_bytes)


def test_thin_cli_writes_and_checks_domain_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = _cli_inputs(tmp_path)
    ledger_output = tmp_path / "ledger-output.jsonl"
    journal_output = tmp_path / "journal-output.json"
    result = ReconciliationResult(
        ledger_bytes=b'{"ledger": true}\n',
        journal_bytes=b'{"journal": true}\n',
        input_receipt_sha256="1" * 64,
        decision_set_digest="2" * 64,
        caveat_set_digest="3" * 64,
    )
    monkeypatch.setattr(cli, "reconcile_noindex_adjudication", lambda _sources: result)
    arguments = [
        *inputs,
        "--recorded-at",
        "2026-08-29T12:37:58Z",
        "--base-revision",
        BASE_REVISION,
        "--ledger-output",
        str(ledger_output),
        "--journal-output",
        str(journal_output),
    ]

    assert cli.main(arguments) == 0
    assert ledger_output.read_bytes() == result.ledger_bytes
    assert journal_output.read_bytes() == result.journal_bytes
    assert cli.main([*arguments, "--check"]) == 0


def test_synthetic_bytes_reconcile_through_engine_and_atomic_pair_writer(
    tmp_path: Path,
) -> None:
    sources, expectations = _synthetic_sources()

    result = reconcile_engine(sources, expectations=expectations)
    ledger_output = tmp_path / "ledger.jsonl"
    journal_output = tmp_path / "journal.json"
    cli._write_pair(
        ledger_output,
        result.ledger_bytes,
        journal_output,
        result.journal_bytes,
    )

    assert cli._outputs_match(ledger_output, journal_output, result)
    assert (
        reconcile_engine(
            _replace_authorities(sources, result), expectations=expectations
        ).ledger_bytes
        == result.ledger_bytes
    )


def test_strict_json_pointer_resolves_rfc6901_escapes() -> None:
    payload = {"a/b": {"~key": ["tekst"]}}

    assert _resolve_json_pointer(payload, "/a~1b/~0key/0") == "tekst"


@pytest.mark.parametrize(
    "pointer",
    ("missing", "/missing", "/items/-", "/items/01", "/items/١", "/items/１", "/~2"),
)
def test_strict_json_pointer_rejects_invalid_or_missing_paths(pointer: str) -> None:
    with pytest.raises(AdjudicationError, match="JSON Pointer"):
        _resolve_json_pointer({"items": ["tekst"]}, pointer)


def test_caveat_pointer_must_resolve_to_exact_string() -> None:
    caveat = EvidenceCaveat(
        caveat_id="synthetic_non_string",
        source_role="strategy",
        artifact_reference="strategy.json",
        source_path="/value",
        text="tekst",
        evidence_ids=(),
        status="active",
        disposition="applies",
        correction=None,
    )

    with pytest.raises(AdjudicationError, match="exact text"):
        _validate_caveat_pointers((caveat,), {"strategy": {"value": 7}})


@pytest.mark.parametrize(
    "case",
    (
        "packet_symlink",
        "technical_hardlink",
        "strategy",
        "tie_breaker",
        "ledger_to_journal",
        "journal_to_ledger",
    ),
)
def test_cli_rejects_immutable_and_cross_authority_output_aliases(
    case: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs, paths = _cli_fixture(tmp_path)
    ledger_output = tmp_path / "ledger-output.jsonl"
    journal_output = tmp_path / "journal-output.json"
    if case == "packet_symlink":
        ledger_output.symlink_to(paths["decision-packet"])
    elif case == "technical_hardlink":
        os.link(paths["technical-judge"], ledger_output)
    elif case == "strategy":
        ledger_output = paths["strategy-judge"]
    elif case == "tie_breaker":
        ledger_output = paths["tie-breaker-judge"]
    elif case == "ledger_to_journal":
        ledger_output = paths["journal"]
    else:
        journal_output = paths["ledger"]
    before = {name: path.read_bytes() for name, path in paths.items()}

    def unexpected_domain_call(_sources: object) -> ReconciliationResult:
        raise AssertionError("domain must not run after unsafe path resolution")

    monkeypatch.setattr(cli, "reconcile_noindex_adjudication", unexpected_domain_call)
    arguments = [
        *inputs,
        "--recorded-at",
        "2026-08-29T12:37:58Z",
        "--base-revision",
        BASE_REVISION,
        "--ledger-output",
        str(ledger_output),
        "--journal-output",
        str(journal_output),
    ]

    assert cli.main(arguments) == 1
    assert {name: path.read_bytes() for name, path in paths.items()} == before


def _rewrite_receipts(ledger: list[dict[str, Any]], journal: dict[str, Any]) -> None:
    source = journal["sources"]["noindex_re_adjudication"]
    source["input_receipt_sha256"] = "0" * 64
    for index, receipt in enumerate(source["judge_receipts"], start=1):
        receipt["sha256"] = str(index) * 64
    judge_set = _digest(
        {
            "schema_version": "content_noindex_judge_receipt_set_v1",
            "judge_receipts": source["judge_receipts"],
        }
    )
    source["judge_receipt_set_digest"] = judge_set
    for row in ledger:
        adjudication = row.get("re_adjudication")
        if adjudication is not None:
            adjudication["input_receipt_sha256"] = "0" * 64
            adjudication["judge_receipt_set_digest"] = judge_set


def _swap_keep_and_noindex(ledger: list[dict[str, Any]]) -> None:
    reviewed = [row for row in ledger if "re_adjudication" in row]
    keep = next(row for row in reviewed if row["re_adjudication"]["recommended_action"] == "keep")
    noindex = next(
        row for row in reviewed if row["re_adjudication"]["recommended_action"] == "noindex"
    )
    keep["re_adjudication"]["recommended_action"] = "noindex"
    noindex["re_adjudication"]["recommended_action"] = "keep"
    for row in (keep, noindex):
        adjudication = row["re_adjudication"]
        adjudication["decision_receipt_sha256"] = _decision_receipt(row, adjudication)


def _rewrite_caveat_set(ledger: list[dict[str, Any]], journal: dict[str, Any]) -> None:
    source = journal["sources"]["noindex_re_adjudication"]
    source["caveats"][0]["text"] += " Drift kontrolny."
    caveat_digest = _digest(
        {
            "schema_version": "content_noindex_caveat_set_v1",
            "caveats": source["caveats"],
        }
    )
    source["caveat_set_digest"] = caveat_digest
    for row in ledger:
        adjudication = row.get("re_adjudication")
        if adjudication is not None:
            adjudication["caveat_set_digest"] = caveat_digest


def _refresh_pair(
    ledger: list[dict[str, Any]],
    journal: dict[str, Any],
) -> tuple[bytes, bytes]:
    journal_by_path = {row["path"]: row for row in journal["urls"]}
    path_digests: list[dict[str, str]] = []
    for row in ledger:
        adjudication = row.get("re_adjudication")
        if adjudication is None:
            continue
        payload = {
            key: value for key, value in adjudication.items() if key != "adjudication_digest"
        }
        adjudication["adjudication_digest"] = _digest(payload)
        path = _path(row["url"])
        resume = journal_by_path[path]["re_adjudication"]
        resume.update(
            {
                "adjudication_digest": adjudication["adjudication_digest"],
                "caveat_set_digest": adjudication["caveat_set_digest"],
                "recommended_action": adjudication["recommended_action"],
                "recommended_target_url": adjudication["recommended_target_url"],
                "status": adjudication["status"],
                "blockers": adjudication["blockers"],
            }
        )
        path_digests.append(
            {"path": path, "adjudication_digest": adjudication["adjudication_digest"]}
        )
    decision_set = _digest(
        {
            "schema_version": "content_noindex_re_adjudication_source_v2",
            "path_adjudication_digests": sorted(path_digests, key=lambda item: item["path"]),
        }
    )
    journal["sources"]["noindex_re_adjudication"]["decision_set_digest"] = decision_set
    ledger_bytes = _render_ledger(ledger)
    journal["sources"]["canonical_ledger"]["sha256"] = hashlib.sha256(ledger_bytes).hexdigest()
    return ledger_bytes, _render_journal(journal)


def _decision_receipt(row: dict[str, Any], adjudication: dict[str, Any]) -> str:
    return _digest(
        {
            "url": row["url"],
            "current_disposition": "noindex",
            "proposed_disposition": adjudication["recommended_action"],
            "target_url": adjudication["recommended_target_url"],
            "confidence": adjudication["confidence"],
            "evidence_ids": adjudication["evidence_ids"],
            "decision_basis": adjudication["decision_basis_pl"],
            "blockers": adjudication["blockers"],
        }
    )


def _cli_inputs(tmp_path: Path) -> list[str]:
    return _cli_fixture(tmp_path)[0]


def _cli_fixture(tmp_path: Path) -> tuple[list[str], dict[str, Path]]:
    arguments: list[str] = []
    paths: dict[str, Path] = {}
    for option, filename in (
        ("decision-packet", "integrated.json"),
        ("technical-judge", "technical.json"),
        ("strategy-judge", "strategy.json"),
        ("tie-breaker-judge", "tie.json"),
        ("ledger", "ledger.jsonl"),
        ("journal", "journal.json"),
    ):
        path = tmp_path / filename
        path.write_bytes((option + "\n").encode())
        paths[option] = path
        arguments.extend([f"--{option}", str(path), f"--{option}-sha256", "a" * 64])
    return arguments, paths


def _synthetic_sources() -> tuple[NoindexAdjudicationSources, AdjudicationExpectations]:
    paths = ("/source-a", "/source-b", "/source-c", "/source-d")
    actions = ("redirect", "keep", "blocked", "redirect")
    targets = ("/source-b", None, None, "/terminal")
    confidences = ("high", "medium", "high", "medium")
    strategy_recommendations = (
        "merge_redirect",
        "keep_refresh",
        "needs_more_evidence",
        "merge_redirect",
    )
    technical_classifications = (
        "noindex_candidate",
        "keep_candidate",
        "needs_content_review",
        "merge_redirect_candidate",
    )
    packet: list[dict[str, Any]] = []
    technical_rows: list[dict[str, Any]] = []
    strategy_rows: list[dict[str, Any]] = []
    for path, action, target, confidence, recommendation, classification in zip(
        paths,
        actions,
        targets,
        confidences,
        strategy_recommendations,
        technical_classifications,
        strict=True,
    ):
        url = _dev_url(path)
        strategy_reason = f"Strategia dla {path}."
        technical_reason = f"Technika dla {path}."
        evidence = [
            "ev_refresh_refresh_google_search_console_1b3e7318dbb9",
            "ev_refresh_refresh_wordpress_ekologus_722938c36872",
            _receipt(path),
        ]
        basis = f"Werdykt stratega: {strategy_reason} Ocena techniczna: {technical_reason}"
        if path == "/source-a":
            basis = "Tie-breaker dla konfliktu techniczno-strategicznego: Rozstrzygnięcie A."
        if action == "redirect":
            basis += REDIRECT_BASIS_SUFFIX
        blockers = ["Brak syntetycznego dowodu."] if action == "blocked" else []
        packet.append(
            {
                "url": url,
                "current_disposition": "noindex",
                "proposed_disposition": action,
                "target_url": _public_url(target) if target else None,
                "confidence": confidence,
                "evidence_ids": sorted([*evidence, "ev_baseline"]),
                "decision_basis": basis,
                "blockers": blockers,
            }
        )
        technical_rows.append(
            {
                "url": url,
                "classification": classification,
                "confidence": confidence,
                "rationale": technical_reason,
            }
        )
        strategy_rows.append(
            {
                "url": url,
                "recommendation": recommendation,
                "candidate_target_url": _public_url(target) if target else None,
                "reason_pl": strategy_reason,
                "evidence_ids": evidence,
                "evidence_limitations": _synthetic_strategy_limitations(),
                "scope_caveat": _sitemap_scope_caveat(),
            }
        )
    technical = {
        "scope": {"limitations": ["Cohort only.", "Dev noindex global.", "Redirect gated."]},
        "rows": technical_rows,
    }
    tie = {
        "global_evidence_caveats": [f"Tie caveat {index}." for index in range(7)],
        "decisions": [
            {
                "url": _dev_url("/source-a"),
                "decision": "merge_redirect",
                "proposed_target_url": _public_url("/source-b"),
                "confidence": "high",
                "reason_pl": "Rozstrzygnięcie A.",
                "evidence_ids": strategy_rows[0]["evidence_ids"],
            }
        ],
    }
    return _synthetic_bundle(paths, packet, technical, strategy_rows, tie)


def _synthetic_bundle(
    paths: tuple[str, ...],
    packet: list[dict[str, Any]],
    technical: dict[str, Any],
    strategy_rows: list[dict[str, Any]],
    tie: dict[str, Any],
) -> tuple[NoindexAdjudicationSources, AdjudicationExpectations]:
    ledger = [
        *[_synthetic_ledger_row(path, "noindex") for path in paths],
        _synthetic_ledger_row("/terminal", "keep"),
        _synthetic_ledger_row("/old-redirect", "redirect", target="/terminal"),
        _synthetic_ledger_row("/removed", "remove"),
    ]
    sources = NoindexAdjudicationSources(
        integrated_decision=_source("integrated_decision", "integrated.json", packet),
        technical_judge=_source("technical", "technical.json", technical),
        strategy_judge=_source("strategy", "strategy.json", strategy_rows),
        tie_breaker_judge=_source("tie_breaker", "tie.json", tie),
        ledger=_raw_source("canonical_ledger", "ledger.jsonl", _render_ledger(ledger)),
        journal=_source("state_journal", "journal.json", _synthetic_journal(ledger)),
        recorded_at="2026-08-29T12:37:58Z",
        base_revision=BASE_REVISION,
    )
    return sources, AdjudicationExpectations(
        ledger_rows=7,
        operational_counts=(("keep", 1), ("noindex", 4), ("redirect", 1), ("remove", 1)),
        decision_rows=4,
        recommendation_counts=(
            ("blocked", 1),
            ("keep", 1),
            ("noindex", 0),
            ("redirect", 2),
            ("remove", 0),
        ),
        resolved_rows=3,
        blocked_rows=1,
        production_pins=None,
    )


def _replace_authorities(
    sources: NoindexAdjudicationSources,
    result: ReconciliationResult,
) -> NoindexAdjudicationSources:
    return NoindexAdjudicationSources(
        integrated_decision=sources.integrated_decision,
        technical_judge=sources.technical_judge,
        strategy_judge=sources.strategy_judge,
        tie_breaker_judge=sources.tie_breaker_judge,
        ledger=_raw_source("canonical_ledger", "ledger.jsonl", result.ledger_bytes),
        journal=_raw_source("state_journal", "journal.json", result.journal_bytes),
        recorded_at=sources.recorded_at,
        base_revision=sources.base_revision,
    )


def _synthetic_ledger_row(
    path: str,
    disposition: str,
    *,
    target: str | None = None,
) -> dict[str, Any]:
    public = _public_url(path)
    redirect = _public_url(target) if target else None
    return {
        "schema_version": "content_canonical_ledger_row_v1",
        "url": _dev_url(path),
        "public_url": public,
        "final_disposition": disposition,
        "canonical_owner_url": public if disposition == "keep" else redirect,
        "redirect_target_url": redirect,
        "merge_target_url": None,
        "lineage_status": (
            "canonical_target_verified"
            if disposition == "keep"
            else "redirect_target_verified"
            if disposition == "redirect"
            else "non_survivor_no_target_expected"
        ),
        "production_readback_receipt_id": _receipt(path),
        "target_readback_receipt_id": _receipt(target) if target else None,
        "decision_basis": "synthetic_baseline",
        "evidence_ids": ["ev_baseline"],
        "source_pack_id": None,
        "work_item_ids": [],
        "publish_allowed": False,
        "write_authorized": False,
        "robot_ready": False,
    }


def _synthetic_journal(ledger: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "dev_content_state_journal_v1",
        "generated_at": "2026-08-28T08:53:33Z",
        "purpose": "Synthetic baseline.",
        "safety": {
            "delete_performed": False,
            "deployment_performed": False,
            "env_values_read": False,
            "generation_performed": False,
            "new_generation_allowed": False,
            "private_packet_read": False,
            "read_only_run": True,
            "vendor_write_performed": False,
        },
        "sources": {
            "canonical_ledger": {
                "path": "ledger.jsonl",
                "sha256": "a" * 64,
                "summary_sha256": "b" * 64,
                "rows": 7,
                "redirect_target_receipts": 1,
                "read_only": True,
            }
        },
        "summary": {"url_rows": 7},
        "urls": [
            {
                "path": _path(row["url"]),
                "url": row["url"],
                "final_disposition": row["final_disposition"],
                "publish_allowed": False,
                "write_authorized": False,
                "robot_ready": False,
            }
            for row in ledger
        ],
    }


def _synthetic_strategy_limitations() -> list[str]:
    return ["GSC one day.", "WordPress partial.", "GA4 and Ahrefs not URL-level."]


def _sitemap_scope_caveat() -> str:
    return (
        "Fresh WordPress sitemap reports 215 URLs while the canonical ledger has 214; "
        "this audit covers the 87 ledger rows marked noindex, and the extra sitemap URL "
        "still requires reconciliation."
    )


def _source(role: str, reference: str, payload: Any) -> SourceArtifact:
    return _raw_source(role, reference, _json_bytes(payload))


def _raw_source(role: str, reference: str, content: bytes) -> SourceArtifact:
    return SourceArtifact(role, reference, content, hashlib.sha256(content).hexdigest())


def _json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode()


def _dev_url(path: str) -> str:
    return "https://ekologus.dev.proudsite.pl" + path + "/"


def _public_url(path: str | None) -> str:
    assert path is not None
    return "https://www.ekologus.pl" + path + "/"


def _receipt(path: str | None) -> str:
    assert path is not None
    return "public_http_readback_" + path.strip("/").replace("-", "_")


def _parse_ledger(raw: bytes) -> list[dict[str, Any]]:
    return [json.loads(line) for line in raw.decode().splitlines()]


def _render_ledger(rows: list[dict[str, Any]]) -> bytes:
    lines = [json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows]
    return ("\n".join(lines) + "\n").encode()


def _render_journal(journal: dict[str, Any]) -> bytes:
    return (json.dumps(journal, ensure_ascii=False, indent=2) + "\n").encode()


def _digest(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    return hashlib.sha256(raw).hexdigest()


def _path(url: str) -> str:
    return "/" + url.split("/", 3)[-1].strip("/")


def _counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    return {
        value: sum(row[key] == value for row in rows)
        for value in sorted({row[key] for row in rows})
    }
