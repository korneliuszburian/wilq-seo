from __future__ import annotations

import hashlib
import json
from collections import Counter
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from scripts.content_dev_authoring_inventory import (
    ACF_SCHEMA_VERSION,
    JOURNAL_SCHEMA_VERSION,
    LEDGER_SCHEMA_VERSION,
    OUTPUT_SCHEMA_VERSION,
    SITEMAP_SCHEMA_VERSION,
    InventoryBuildError,
    ProjectionExpectations,
    SourceProvenance,
    build_dev_authoring_inventory,
    main,
    render_inventory,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_PATH = REPO_ROOT / "docs/content-dev-authoring-inventory-20260828.json"
DEV_ORIGIN = "https://ekologus.dev.proudsite.pl"
OBSERVED_PATH = "/Dok%C5%82adny"
MISSING_PATH = "/brak"
SOURCE_KEYS = ("sitemap", "acf", "journal", "ledger")
SYNTHETIC_EXPECTATIONS = ProjectionExpectations(
    target_count=2,
    rest_object_count=1,
    endpoint_counts=(("posts", 1),),
    authoring_counts=(("acf_flexible_content", 1),),
    keep_count=1,
    keep_rest_object_count=1,
)
SYNTHETIC_REFS = {key: f"docs/{key}.json" for key in SOURCE_KEYS}
SYNTHETIC_REFS["ledger"] = "docs/ledger.jsonl"
SYNTHETIC_PROVENANCE = {
    key: SourceProvenance(SYNTHETIC_REFS[key], character * 64)
    for key, character in zip(SOURCE_KEYS, "abcd", strict=True)
}


def _join_sha256_chunks(*chunks: str) -> str:
    assert chunks and all(len(chunk) <= 8 for chunk in chunks)
    digest = "".join(chunks)
    assert len(digest) == 64
    return digest


PRODUCTION_HASHES = {
    "sitemap": _join_sha256_chunks(
        "0f0cd730",
        "f6b480b2",
        "84da7be6",
        "631dfc4b",
        "22a0a645",
        "c4582abf",
        "e209367d",
        "82590c0c",
    ),
    "acf": _join_sha256_chunks(
        "97281a48",
        "774c1893",
        "d80c2355",
        "55074d9c",
        "7502d680",
        "74479c7b",
        "59795357",
        "a64e1a80",
    ),
    "journal": _join_sha256_chunks(
        "53700d90",
        "d3cb78f8",
        "9fd6e214",
        "66478130",
        "3ecb5375",
        "6f856dc2",
        "59559a1c",
        "1fdaa0d6",
    ),
    "ledger": _join_sha256_chunks(
        "d57cbdd9",
        "89c9970a",
        "597563c1",
        "6fc10086",
        "9ce93f5b",
        "d0dc5623",
        "4d50e787",
        "5facbab2",
    ),
}
PRODUCTION_REFS = {
    "sitemap": "docs/content-sitemap-inventory-20260828.json",
    "acf": "docs/content-acf-inventory-20260828.json",
    "journal": "docs/content-dev-state-journal-20260828.json",
    "ledger": "docs/content-canonical-ledger-20260828.jsonl",
}
ARTIFACT_SHA256 = _join_sha256_chunks(
    "9737b6a3",
    "09d13e40",
    "c662f943",
    "892849ee",
    "6c14419e",
    "1c04f3c4",
    "16ad4032",
    "db01b245",
)


def test_builder_projects_exact_allowlisted_values_and_ignores_old_only_rows() -> None:
    inventory = build_fixture(*synthetic_sources())
    assert inventory["schema_version"] == OUTPUT_SCHEMA_VERSION
    assert inventory["inventory_role"] == "authoring_target"
    assert inventory["read_only"] is True
    for key in (
        "source_refetch_performed",
        "generation_performed",
        "raw_body_retained",
        "publish_allowed",
        "write_authorized",
        "robot_ready",
    ):
        assert inventory[key] is False
    assert inventory["summary"] == {
        "target_count": 2,
        "rest_object_observed_count": 1,
        "rest_object_not_observed_count": 1,
        "endpoint_counts": {"posts": 1},
        "authoring_counts": {"acf_flexible_content": 1},
        "keep_count": 1,
        "keep_rest_object_observed_count": 1,
        "input_schema_versions": {
            "sitemap": SITEMAP_SCHEMA_VERSION,
            "acf": ACF_SCHEMA_VERSION,
            "journal": JOURNAL_SCHEMA_VERSION,
            "ledger": LEDGER_SCHEMA_VERSION,
        },
        "input_generated_at": {
            "sitemap": "2026-08-28",
            "acf": "2026-08-28T09:30:39Z",
            "journal": "2026-08-28T08:53:33Z",
        },
        "source_refs": {key: value.source_ref for key, value in SYNTHETIC_PROVENANCE.items()},
        "source_sha256": {key: value.sha256 for key, value in SYNTHETIC_PROVENANCE.items()},
    }
    rows = {row["path"]: row for row in inventory["rows"]}
    assert set(rows) == {OBSERVED_PATH, MISSING_PATH}
    observed = rows[OBSERVED_PATH]
    assert observed | {} == {
        **common_output_row(OBSERVED_PATH, "keep", "  własny/status:v9  "),
        "rest_object_observed": True,
        "blocker": None,
        "object_id": 42,
        "post_type": "post",
        "endpoint": "posts",
        "status": "private-review",
        "modified": "2026-08-27T11:22:33+02:00",
        "modified_gmt": "2026-08-27T09:22:33Z",
        "authoring_mode": "acf_flexible_content",
        "raw_values_retained": False,
        "acf_root_fields": ["zeta-root", "flexible-news"],
        "acf_field_names": ["cta", "body", "content", "title"],
        "acf_layouts": [
            {
                "root_field": "flexible-news",
                "layout_name": "content_data",
                "row_index": 3,
                "field_names": ["title", "body", "content"],
            }
        ],
    }
    missing = rows[MISSING_PATH]
    assert missing["rest_object_observed"] is False
    assert missing["blocker"]["code"] == "rest_object_not_observed"
    assert all(missing[key] is None for key in nullable_rest_fields())


def test_builder_is_deterministic_and_never_projects_raw_source_material() -> None:
    sitemap, acf, journal, ledger = synthetic_sources()
    first = build_fixture(sitemap, acf, journal, ledger)
    sitemap["rows"].reverse()
    journal["urls"].reverse()
    ledger.reverse()
    second = build_fixture(sitemap, acf, journal, ledger)

    assert render_inventory(first) == render_inventory(second)
    serialized = render_inventory(second).decode()
    for sentinel in ("SECRET_BODY", "SECRET_ACF_VALUE", "SECRET_CONNECTOR"):
        assert sentinel not in serialized
    assert '"body":' not in serialized
    assert '"connector_evidence"' not in serialized
    assert '"acf_digest"' not in serialized


def test_builder_and_cli_require_ledger_payload_hash_ref_and_schema(
    tmp_path: Path,
) -> None:
    sitemap, acf, journal, _ = synthetic_sources()
    incomplete = {key: value for key, value in SYNTHETIC_PROVENANCE.items() if key != "ledger"}
    with pytest.raises(TypeError):
        build_dev_authoring_inventory(  # type: ignore[call-arg]
            sitemap,
            acf,
            journal,
            provenance=SYNTHETIC_PROVENANCE,
            expectations=SYNTHETIC_EXPECTATIONS,
        )
    with pytest.raises(InventoryBuildError, match="provenance source keys"):
        build_dev_authoring_inventory(
            sitemap,
            acf,
            journal,
            [],
            provenance=incomplete,
            expectations=SYNTHETIC_EXPECTATIONS,
        )
    paths, hashes, _ = write_synthetic_sources(tmp_path)
    arguments = cli_arguments(paths, hashes, tmp_path / "output.json")
    ledger_index = arguments.index("--ledger")
    del arguments[ledger_index : ledger_index + 6]
    with pytest.raises(SystemExit):
        main(arguments, expectations=SYNTHETIC_EXPECTATIONS)


@pytest.mark.parametrize("source", SOURCE_KEYS)
def test_builder_rejects_wrong_source_schema(source: str) -> None:
    sitemap, acf, journal, ledger = synthetic_sources()
    selected: Any = {"sitemap": sitemap, "acf": acf, "journal": journal, "ledger": ledger}[source]
    if source == "ledger":
        selected[0]["schema_version"] = "unsupported"
    else:
        selected["schema_version"] = "unsupported"
    with pytest.raises(InventoryBuildError, match="schema_version"):
        build_fixture(sitemap, acf, journal, ledger)


@pytest.mark.parametrize(
    ("source", "key"),
    [
        ("sitemap", "read_only"),
        ("acf", "read_only"),
        ("acf_summary", "raw_values_retained"),
        ("acf_row", "raw_values_retained"),
        *[
            ("journal_safety", key)
            for key in (
                "delete_performed",
                "deployment_performed",
                "env_values_read",
                "generation_performed",
                "new_generation_allowed",
                "private_packet_read",
                "read_only_run",
                "vendor_write_performed",
            )
        ],
        *[
            (source, key)
            for source in ("journal_row", "ledger_row")
            for key in (
                "publish_allowed",
                "write_authorized",
                "robot_ready",
            )
        ],
    ],
)
def test_builder_rejects_every_read_only_safety_violation(source: str, key: str) -> None:
    sitemap, acf, journal, ledger = synthetic_sources()
    selected = {
        "sitemap": sitemap,
        "acf": acf,
        "acf_summary": acf["summary"],
        "acf_row": acf["objects"][0],
        "journal_safety": journal["safety"],
        "journal_row": journal["urls"][0],
        "ledger_row": ledger[0],
    }[source]
    selected[key] = not selected[key]
    with pytest.raises(InventoryBuildError, match=key):
        build_fixture(sitemap, acf, journal, ledger)


BAD_ORIGIN_URLS = [
    f"http://ekologus.dev.proudsite.pl{OBSERVED_PATH}",
    f"https://other.example{OBSERVED_PATH}",
    f"https://user@ekologus.dev.proudsite.pl{OBSERVED_PATH}",
    f"https://ekologus.dev.proudsite.pl:443{OBSERVED_PATH}",
    f"{DEV_ORIGIN}{OBSERVED_PATH}?preview=1",
    f"{DEV_ORIGIN}{OBSERVED_PATH}#fragment",
]


@pytest.mark.parametrize(
    ("source", "bad_url"),
    [("journal", value) for value in BAD_ORIGIN_URLS]
    + [("ledger", value) for value in BAD_ORIGIN_URLS]
    + [
        ("journal", f"{DEV_ORIGIN}/dok%C5%82adny"),
        ("journal", f"{DEV_ORIGIN}{OBSERVED_PATH}/"),
        ("ledger", f"{DEV_ORIGIN}{OBSERVED_PATH}//"),
    ],
)
def test_builder_rejects_nonexact_journal_and_ledger_identity(source: str, bad_url: str) -> None:
    sitemap, acf, journal, ledger = synthetic_sources()
    if source == "journal":
        journal["urls"][0]["url"] = bad_url
    else:
        ledger[0]["url"] = bad_url
    match = "exact dev origin|URL/path mismatch|absolute URL path"
    with pytest.raises(InventoryBuildError, match=match):
        build_fixture(sitemap, acf, journal, ledger)


@pytest.mark.parametrize("source", ["journal", "ledger"])
@pytest.mark.parametrize(
    "bad_url",
    [
        pytest.param(f" {DEV_ORIGIN}{OBSERVED_PATH}", id="leading-space"),
        pytest.param(f"\n{DEV_ORIGIN}{OBSERVED_PATH}", id="leading-newline"),
        pytest.param(f"{DEV_ORIGIN}\t{OBSERVED_PATH}", id="embedded-tab"),
        pytest.param(f"{DEV_ORIGIN}{OBSERVED_PATH}\r", id="trailing-cr"),
        pytest.param(f"{DEV_ORIGIN}{OBSERVED_PATH}\n", id="trailing-lf"),
        pytest.param(f"{DEV_ORIGIN}\0{OBSERVED_PATH}", id="nul"),
        pytest.param(f"{DEV_ORIGIN}\x7f{OBSERVED_PATH}", id="del"),
    ],
)
def test_builder_rejects_raw_whitespace_and_ascii_controls_in_dev_urls(
    source: str, bad_url: str
) -> None:
    sitemap, acf, journal, ledger = synthetic_sources()
    if source == "journal":
        journal["urls"][0]["url"] = bad_url
    else:
        ledger[0]["url"] = bad_url
    with pytest.raises(InventoryBuildError, match="raw whitespace or ASCII control"):
        build_fixture(sitemap, acf, journal, ledger)


@pytest.mark.parametrize("source", ["journal", "ledger"])
@pytest.mark.parametrize("bad_value", ["archive", "KEEP", " keep", ""])
def test_builder_rejects_any_noncanonical_disposition(source: str, bad_value: str) -> None:
    sitemap, acf, journal, ledger = synthetic_sources()
    if source == "journal":
        journal["urls"][1]["final_disposition"] = bad_value
    else:
        ledger[1]["final_disposition"] = bad_value
    with pytest.raises(InventoryBuildError, match="final_disposition"):
        build_fixture(sitemap, acf, journal, ledger)


@pytest.mark.parametrize("disposition", ["noindex", "redirect", "remove"])
def test_builder_accepts_each_nonkeep_disposition(disposition: str) -> None:
    sitemap, acf, journal, ledger = synthetic_sources()
    journal["urls"][0]["final_disposition"] = disposition
    ledger[0]["final_disposition"] = disposition
    expectations = replace(SYNTHETIC_EXPECTATIONS, keep_count=0, keep_rest_object_count=0)
    inventory = build_fixture(sitemap, acf, journal, ledger, expectations=expectations)
    assert inventory["rows"][0]["final_disposition"] == disposition


@pytest.mark.parametrize(
    ("case", "match"),
    [
        ("duplicate_sitemap_path", "Duplicate sitemap path"),
        ("duplicate_membership", "Duplicate value"),
        ("duplicate_journal_url", "Duplicate journal URL"),
        ("duplicate_ledger_path", "Duplicate normalized ledger path"),
        ("duplicate_acf_path", "Duplicate ACF path"),
        ("duplicate_object_id", "Duplicate ACF object_id"),
        ("acf_outside_sitemap", "outside the sitemap"),
        ("acf_membership", "ACF sitemap membership"),
        ("endpoint_type", "endpoint/post type"),
        ("journal_path_set", "journal/sitemap path set"),
        ("ledger_path_set", "ledger/sitemap normalized path set"),
        ("ledger_disposition", "ledger disposition"),
        ("layout_row_index", "row_index must be explicit"),
    ],
)
def test_builder_rejects_duplicate_identity_and_cross_source_drift(case: str, match: str) -> None:
    sitemap, acf, journal, ledger = synthetic_sources()
    expectations = SYNTHETIC_EXPECTATIONS
    if case.startswith("duplicate_acf") or case == "duplicate_object_id":
        add_second_rest_object(acf)
        expectations = two_rest_expectations()
    if case == "duplicate_sitemap_path":
        sitemap["rows"][1] = deepcopy(sitemap["rows"][0])
    elif case == "duplicate_membership":
        sitemap["rows"][0]["dev_sitemaps"] *= 2
    elif case == "duplicate_journal_url":
        journal["urls"][1]["url"] = journal["urls"][0]["url"]
    elif case == "duplicate_ledger_path":
        ledger[1]["url"] = f"{DEV_ORIGIN}{OBSERVED_PATH}"
    elif case == "duplicate_acf_path":
        acf["objects"][1]["path"] = OBSERVED_PATH
    elif case == "duplicate_object_id":
        acf["objects"][1]["object_id"] = 42
    elif case == "acf_outside_sitemap":
        acf["objects"][0]["path"] = "/outside"
    elif case == "acf_membership":
        acf["objects"][0]["sitemap"] = ["page-sitemap.xml"]
    elif case == "endpoint_type":
        acf["objects"][0]["type"] = "page"
    elif case == "journal_path_set":
        journal["urls"][1].update(path="/else", url=f"{DEV_ORIGIN}/else")
    elif case == "ledger_path_set":
        ledger[1]["url"] = f"{DEV_ORIGIN}/else/"
    elif case == "ledger_disposition":
        ledger[0]["final_disposition"] = "redirect"
    else:
        del acf["objects"][0]["acf_layouts"][0]["row_index"]
    with pytest.raises(InventoryBuildError, match=match):
        build_fixture(sitemap, acf, journal, ledger, expectations=expectations)


@pytest.mark.parametrize(
    "invalid_path",
    [
        "/segment//child",
        "/segment/../child",
        "/segment/./child",
        "/segment\\child",
        "/segment\nchild",
    ],
)
def test_builder_rejects_noncanonical_raw_paths(invalid_path: str) -> None:
    sitemap, acf, journal, ledger = synthetic_sources()
    sitemap["rows"][0]["path"] = invalid_path
    with pytest.raises(InventoryBuildError, match="exact absolute URL path"):
        build_fixture(sitemap, acf, journal, ledger)


@pytest.mark.parametrize(
    ("expectations", "match"),
    [
        (replace(SYNTHETIC_EXPECTATIONS, target_count=3), "sitemap target count"),
        (replace(SYNTHETIC_EXPECTATIONS, endpoint_counts=(("pages", 1),)), "ACF endpoint counts"),
        (replace(SYNTHETIC_EXPECTATIONS, keep_rest_object_count=0), "derived keep REST"),
    ],
)
def test_builder_rejects_wrong_explicit_expectations(
    expectations: ProjectionExpectations, match: str
) -> None:
    with pytest.raises(InventoryBuildError, match=match):
        build_fixture(*synthetic_sources(), expectations=expectations)


@pytest.mark.parametrize("problem", ["absolute_ref", "bad_sha", "missing_ledger"])
def test_builder_requires_complete_repo_relative_source_lineage(problem: str) -> None:
    provenance = dict(SYNTHETIC_PROVENANCE)
    if problem == "absolute_ref":
        provenance["sitemap"] = SourceProvenance("/tmp/sitemap.json", "a" * 64)
    elif problem == "bad_sha":
        provenance["sitemap"] = SourceProvenance("docs/sitemap.json", "a" * 63)
    else:
        del provenance["ledger"]
    with pytest.raises(InventoryBuildError, match="repo-relative|SHA-256|source keys"):
        build_dev_authoring_inventory(
            *synthetic_sources(),
            provenance=provenance,
            expectations=SYNTHETIC_EXPECTATIONS,
        )


def test_cli_generation_and_check_are_reproducible_without_rewrite(tmp_path: Path) -> None:
    paths, hashes, original = write_synthetic_sources(tmp_path)
    output_path = tmp_path / "inventory.json"
    arguments = cli_arguments(paths, hashes, output_path)
    assert main(arguments, expectations=SYNTHETIC_EXPECTATIONS) == 0
    generated = output_path.read_bytes()
    mtime = output_path.stat().st_mtime_ns
    assert main([*arguments, "--check"], expectations=SYNTHETIC_EXPECTATIONS) == 0
    assert output_path.read_bytes() == generated
    assert output_path.stat().st_mtime_ns == mtime
    assert {key: path.read_bytes() for key, path in paths.items()} == original
    output_path.write_bytes(generated + b" ")
    assert main([*arguments, "--check"], expectations=SYNTHETIC_EXPECTATIONS) == 1
    assert output_path.read_bytes() == generated + b" "


def test_cli_hash_mismatch_and_missing_check_output_never_create_output(tmp_path: Path) -> None:
    paths, hashes, _ = write_synthetic_sources(tmp_path)
    output_path = tmp_path / "inventory.json"
    arguments = cli_arguments(paths, hashes, output_path)
    bad_hash_arguments = list(arguments)
    hash_index = bad_hash_arguments.index("--ledger-sha256") + 1
    bad_hash_arguments[hash_index] = "0" * 64
    assert main(bad_hash_arguments, expectations=SYNTHETIC_EXPECTATIONS) == 1
    assert not output_path.exists()
    assert main([*arguments, "--check"], expectations=SYNTHETIC_EXPECTATIONS) == 1
    assert not output_path.exists()


@pytest.mark.parametrize("alias_kind", ["same_path", "hardlink", "symlink"])
def test_cli_never_overwrites_or_aliases_an_input(tmp_path: Path, alias_kind: str) -> None:
    paths, hashes, original = write_synthetic_sources(tmp_path)
    if alias_kind == "same_path":
        output_path = paths["sitemap"]
    else:
        output_path = tmp_path / f"{alias_kind}.json"
        if alias_kind == "hardlink":
            output_path.hardlink_to(paths["sitemap"])
        else:
            output_path.symlink_to(paths["sitemap"])
    assert main(cli_arguments(paths, hashes, output_path), expectations=SYNTHETIC_EXPECTATIONS) == 1
    assert paths["sitemap"].read_bytes() == original["sitemap"]


def test_production_sources_rebuild_the_byte_exact_retained_artifact() -> None:
    paths = {key: REPO_ROOT / ref for key, ref in PRODUCTION_REFS.items()}
    arguments = cli_arguments(paths, PRODUCTION_HASHES, ARTIFACT_PATH, refs=PRODUCTION_REFS)
    assert main([*arguments, "--check"]) == 0
    artifact_bytes = ARTIFACT_PATH.read_bytes()
    assert hashlib.sha256(artifact_bytes).hexdigest() == ARTIFACT_SHA256
    artifact = json.loads(artifact_bytes)
    assert render_inventory(artifact) == artifact_bytes
    summary = artifact["summary"]
    assert summary["source_refs"] == PRODUCTION_REFS
    assert summary["source_sha256"] == PRODUCTION_HASHES
    assert (
        summary["target_count"],
        summary["rest_object_observed_count"],
        summary["rest_object_not_observed_count"],
        summary["keep_count"],
        summary["keep_rest_object_observed_count"],
    ) == (214, 175, 39, 57, 57)
    rows = artifact["rows"]
    assert Counter(row["final_disposition"] for row in rows) == {
        "keep": 57,
        "noindex": 87,
        "redirect": 46,
        "remove": 24,
    }
    assert sum(row["rest_object_observed"] for row in rows) == 175
    assert all(
        row["dev_url"] == (DEV_ORIGIN if row["path"] == "/" else DEV_ORIGIN + row["path"])
        for row in rows
    )
    assert all(
        row["publish_allowed"] is False
        and row["write_authorized"] is False
        and row["robot_ready"] is False
        and row["new_generation_allowed"] is False
        for row in rows
    )


def sitemap_source() -> dict[str, Any]:
    return {
        "schema_version": SITEMAP_SCHEMA_VERSION,
        "generated_at": "2026-08-28",
        "read_only": True,
        "summary": {
            "dev_entries": 2,
            "dev_unique_paths": 2,
            "dev_sitemap_counts": {"category-sitemap.xml": 1, "post-sitemap.xml": 1},
        },
        "rows": [
            {"path": OBSERVED_PATH, "dev_sitemaps": ["post-sitemap.xml"]},
            {"path": MISSING_PATH, "dev_sitemaps": ["category-sitemap.xml"]},
            {"path": "/old-only", "dev_sitemaps": []},
        ],
    }


def acf_source() -> dict[str, Any]:
    return {
        "schema_version": ACF_SCHEMA_VERSION,
        "generated_at": "2026-08-28T09:30:39Z",
        "read_only": True,
        "summary": {"raw_values_retained": False},
        "objects": [
            {
                "path": OBSERVED_PATH,
                "endpoint": "posts",
                "type": "post",
                "object_id": 42,
                "status": "private-review",
                "modified": "2026-08-27T11:22:33+02:00",
                "modified_gmt": "2026-08-27T09:22:33Z",
                "sitemap": ["post-sitemap.xml"],
                "in_dev_sitemap": True,
                "sitemap_match": True,
                "authoring_mode": "acf_flexible_content",
                "raw_values_retained": False,
                "acf_root_fields": ["zeta-root", "flexible-news"],
                "acf_field_names": ["cta", "body", "content", "title"],
                "acf_layouts": [
                    {
                        "root_field": "flexible-news",
                        "layout_name": "content_data",
                        "row_index": 3,
                        "field_names": ["title", "body", "content"],
                        "raw_value": "SECRET_ACF_VALUE",
                    }
                ],
                "body": "SECRET_BODY",
                "acf_digest": "SECRET_DIGEST",
            }
        ],
    }


def journal_source() -> dict[str, Any]:
    return {
        "schema_version": JOURNAL_SCHEMA_VERSION,
        "generated_at": "2026-08-28T08:53:33Z",
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
        "summary": {"url_rows": 2, "keep_rows": 1, "non_survivor_rows": 1},
        "urls": [
            journal_row(OBSERVED_PATH, "keep", "  własny/status:v9  "),
            journal_row(MISSING_PATH, "noindex", "audit_only_no_content"),
        ],
    }


def journal_row(path: str, disposition: str, delivery_status: str) -> dict[str, Any]:
    return {
        "path": path,
        "url": DEV_ORIGIN + path,
        "final_disposition": disposition,
        "delivery_status": delivery_status,
        "publish_allowed": False,
        "write_authorized": False,
        "robot_ready": False,
        "connector_evidence": {"raw": "SECRET_CONNECTOR"},
    }


def ledger_source() -> list[dict[str, Any]]:
    return [ledger_row(OBSERVED_PATH, "keep"), ledger_row(MISSING_PATH, "noindex")]


def ledger_row(path: str, disposition: str) -> dict[str, Any]:
    return {
        "schema_version": LEDGER_SCHEMA_VERSION,
        "url": f"{DEV_ORIGIN}{path}/",
        "final_disposition": disposition,
        "publish_allowed": False,
        "write_authorized": False,
        "robot_ready": False,
    }


def synthetic_sources() -> tuple[
    dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]
]:
    return sitemap_source(), acf_source(), journal_source(), ledger_source()


def build_fixture(
    sitemap: dict[str, Any],
    acf: dict[str, Any],
    journal: dict[str, Any],
    ledger: list[dict[str, Any]],
    *,
    expectations: ProjectionExpectations = SYNTHETIC_EXPECTATIONS,
) -> dict[str, Any]:
    return build_dev_authoring_inventory(
        sitemap,
        acf,
        journal,
        ledger,
        provenance=SYNTHETIC_PROVENANCE,
        expectations=expectations,
    )


def add_second_rest_object(acf: dict[str, Any]) -> None:
    second = deepcopy(acf["objects"][0])
    second.update(path=MISSING_PATH, object_id=43, sitemap=["category-sitemap.xml"])
    acf["objects"].append(second)


def two_rest_expectations() -> ProjectionExpectations:
    return replace(
        SYNTHETIC_EXPECTATIONS,
        rest_object_count=2,
        endpoint_counts=(("posts", 2),),
        authoring_counts=(("acf_flexible_content", 2),),
    )


def common_output_row(path: str, disposition: str, delivery_status: str) -> dict[str, Any]:
    membership = "post-sitemap.xml" if path == OBSERVED_PATH else "category-sitemap.xml"
    return {
        "inventory_role": "authoring_target",
        "sitemap_observed": True,
        "dev_sitemaps": [membership],
        "path": path,
        "dev_url": DEV_ORIGIN + path,
        "final_disposition": disposition,
        "delivery_status": delivery_status,
        "publish_allowed": False,
        "write_authorized": False,
        "robot_ready": False,
        "new_generation_allowed": False,
    }


def nullable_rest_fields() -> tuple[str, ...]:
    return (
        "object_id",
        "post_type",
        "endpoint",
        "status",
        "modified",
        "modified_gmt",
        "authoring_mode",
        "raw_values_retained",
        "acf_root_fields",
        "acf_field_names",
        "acf_layouts",
    )


def write_synthetic_sources(
    directory: Path,
) -> tuple[dict[str, Path], dict[str, str], dict[str, bytes]]:
    sitemap, acf, journal, ledger = synthetic_sources()
    payloads = {
        "sitemap": json_bytes(sitemap),
        "acf": json_bytes(acf),
        "journal": json_bytes(journal),
        "ledger": (
            "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in ledger) + "\n"
        ).encode(),
    }
    paths = {key: directory / Path(SYNTHETIC_REFS[key]).name for key in SOURCE_KEYS}
    for key, path in paths.items():
        path.write_bytes(payloads[key])
    hashes = {key: hashlib.sha256(value).hexdigest() for key, value in payloads.items()}
    return paths, hashes, payloads


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n").encode()


def cli_arguments(
    paths: dict[str, Path],
    hashes: dict[str, str],
    output_path: Path,
    *,
    refs: dict[str, str] = SYNTHETIC_REFS,
) -> list[str]:
    arguments = []
    for key in SOURCE_KEYS:
        arguments.extend(
            [
                f"--{key}",
                str(paths[key]),
                f"--{key}-sha256",
                hashes[key],
                f"--{key}-ref",
                refs[key],
            ]
        )
    return [*arguments, "--output", str(output_path)]
