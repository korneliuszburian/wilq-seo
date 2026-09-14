from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast

import pytest

from wilq.content.workflow.authoring_inventory_receipt import (
    _build_content_authoring_inventory_receipt_from_catalog,
)
from wilq.content.workflow.decisions.current_blocked import (
    build_current_all_blocked_classification,
)
from wilq.content.workflow.decisions.production import (
    WAVE0_PRODUCTION_ACCEPTANCE_POLICY,
    ContentProductionClassificationRun,
    ContentProductionClassificationValidationError,
)
from wilq.content.workflow.workspace.catalog import (
    ContentInventoryCatalogItem,
    ContentInventoryCatalogResponse,
    ContentInventoryCoverage,
)
from wilq.schemas import ConnectorCoveredWindow, ContentFreshnessAssessment

ROOT = Path(__file__).resolve().parents[2]
JOURNAL = ROOT / "docs" / "content-status-214.csv"
CHECKED_AT = datetime(2026, 9, 13, 10, 0, tzinfo=UTC)
BASE_REVISION = "1" * 40


def _keep_paths() -> tuple[str, ...]:
    import csv

    with JOURNAL.open(encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["final_disposition"] == "keep"]
    return tuple(sorted(row["path"].rstrip("/") or "/" for row in rows))


def _catalog(*, work_item_suffix: str = "normal") -> ContentInventoryCatalogResponse:
    paths = _keep_paths()[::2]
    items = [
        ContentInventoryCatalogItem(
            catalog_id=f"catalog_{index}",
            work_item_id=(f"content_work_item_inventory_{work_item_suffix}_{index}"),
            url=(
                "https://ekologus.dev.proudsite.pl/"
                if path == "/"
                else f"https://ekologus.dev.proudsite.pl{path}/"
            ),
            path=path,
            content_type="post",
            material_status="url_only",
            source_connector="wordpress_ekologus",
            evidence_id="ev_wp_current",
            collected_at=CHECKED_AT,
        )
        for index, path in enumerate(paths)
    ]
    return ContentInventoryCatalogResponse(
        total_count=len(items),
        items=items,
        source_connectors=["wordpress_ekologus"],
        evidence_ids=["ev_wp_current"],
        coverage=ContentInventoryCoverage(
            status="unknown",
            source_count=len(items),
            returned_count=len(items),
            caveat="synthetic evidence-scoped coverage",
        ),
    )


def _freshness(
    *,
    requires_refresh: bool = False,
    state: Literal["fresh", "stale", "missing", "blocked"] | None = None,
    missing_connector_ids: list[str] | None = None,
    blocked_connector_ids: list[str] | None = None,
    stale_connector_ids: list[str] | None = None,
) -> ContentFreshnessAssessment:
    resolved_state: Literal["fresh", "stale", "missing", "blocked"] = (
        state if state is not None else ("stale" if requires_refresh else "fresh")
    )
    return ContentFreshnessAssessment(
        state=resolved_state,
        checked_at=CHECKED_AT,
        requires_refresh=requires_refresh,
        connector_covered_windows={
            "google_search_console": ConnectorCoveredWindow(),
            "wordpress_ekologus": ConnectorCoveredWindow(),
        },
        missing_connector_ids=missing_connector_ids or [],
        blocked_connector_ids=blocked_connector_ids or [],
        stale_connector_ids=stale_connector_ids or [],
        summary="synthetic freshness",
        next_step="synthetic next step",
    )


def _journal_rows() -> list[dict[str, str]]:
    with JOURNAL.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_journal(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _build(**kwargs: object) -> ContentProductionClassificationRun:
    return build_current_all_blocked_classification(
        catalog=cast(ContentInventoryCatalogResponse, kwargs.pop("catalog", _catalog())),
        freshness=cast(ContentFreshnessAssessment, kwargs.pop("freshness", _freshness())),
        base_revision=cast(str, kwargs.pop("base_revision", BASE_REVISION)),
        recorded_at=cast(datetime | None, kwargs.pop("recorded_at", CHECKED_AT)),
        journal_path=cast(Path | None, kwargs.pop("journal_path", None)),
        inventory_receipts=kwargs.pop("inventory_receipts", None),
    )


def test_current_builder_returns_sorted_57_row_all_blocked_run_with_history_protection() -> None:
    run = _build()

    assert isinstance(run, ContentProductionClassificationRun)
    assert tuple(row.canonical_path for row in run.rows) == _keep_paths()
    assert run.counts.model_dump() == {
        "rows": 57,
        "reuse": 0,
        "refresh": 0,
        "write": 0,
        "blocked": 57,
        "generation_allowed": 0,
        "verified_current_actions": 0,
        "verified_current_drafts": 0,
    }
    assert run.input.policy_id != WAVE0_PRODUCTION_ACCEPTANCE_POLICY.policy_id
    assert run.judge_receipt.reviewer_role == "deterministic_packet_integrity_verifier"
    assert all(
        row.decision == "blocked"
        and row.generation_allowed is False
        and row.current_work_item_id is None
        and row.retained_work_item_id is None
        and row.revision_id is None
        and row.revision_digest is None
        and row.revision_approved is False
        and row.revision_complete is False
        and row.retained_binding is None
        and row.verified_actions == ()
        and row.verified_drafts == ()
        and len(row.blockers) == 1
        for row in run.rows
    )
    bdo = next(
        row for row in run.rows if row.canonical_path == "/bdo-co-musi-wiedziec-przedsiebiorca"
    )
    assert bdo.blocked_historical_protection is not None
    protected_binding = WAVE0_PRODUCTION_ACCEPTANCE_POLICY.protected_binding
    assert protected_binding is not None
    assert bdo.blocked_historical_protection.historical_revision_id == (
        protected_binding.revision_id
    )
    assert bdo.blocked_historical_protection.historical_revision_digest == (
        protected_binding.revision_digest
    )
    assert bdo.blocked_historical_protection.current_verification_outcome == "unavailable"
    assert bdo.blocked_historical_protection.current_verification_evidence_id == "ev_wp_current"
    assert bdo.blocked_historical_protection.current_verification_checked_at.endswith("Z")


def test_catalog_work_item_url_slug_or_post_id_never_changes_current_result() -> None:
    baseline = _build(catalog=_catalog(work_item_suffix="baseline"))
    changed = _build(catalog=_catalog(work_item_suffix="https_example_slug_1991"))

    assert changed.model_copy(update={"audit": baseline.audit}) == baseline


def test_registered_current_inventory_remains_blocked_without_delivery_or_source_pack() -> None:
    catalog = _catalog().model_copy(
        update={
            "items": [
                item.model_copy(
                    update={
                        "url": (
                            "https://www.ekologus.pl/"
                            if item.path == "/"
                            else f"https://www.ekologus.pl{item.path}/"
                        ),
                        "material_status": "content_and_structure",
                        "content_summary": "material",
                    }
                )
                for item in _catalog().items
            ]
        }
    )
    receipts = {
        item.path.rstrip("/") or "/": _build_content_authoring_inventory_receipt_from_catalog(
            item=item,
            catalog=catalog,
            recorded_by="current_inventory_reconciler",
            recorded_at=CHECKED_AT,
        )
        for item in catalog.items
    }

    run = _build(catalog=catalog, inventory_receipts=receipts)
    registered = [
        row
        for row in run.rows
        if getattr(row.source_receipt, "binding_state", None) == "registered_current_inventory"
    ]

    assert registered
    assert all(row.decision == "blocked" and row.generation_allowed is False for row in registered)
    assert all(row.current_work_item_id is not None for row in registered)
    assert all(row.revision_id is None and row.verified_actions == () for row in registered)
    assert all(row.verified_drafts == () and row.retained_binding is None for row in registered)
    assert all(
        set(row.source_receipt.missing_sources)
        == {"delivery_identity_binding", "source_pack_binding"}
        for row in registered
    )


def test_current_builder_rejects_stale_state_even_when_refresh_flag_is_false() -> None:
    with pytest.raises(ContentProductionClassificationValidationError) as error:
        _build(freshness=_freshness(state="stale"))

    assert error.value.code == "freshness_state_invalid"


@pytest.mark.parametrize(
    "field",
    ["missing_connector_ids", "blocked_connector_ids", "stale_connector_ids"],
)
def test_current_builder_rejects_freshness_connector_blockers(
    field: Literal["missing_connector_ids", "blocked_connector_ids", "stale_connector_ids"],
) -> None:
    freshness = _freshness()
    freshness = freshness.model_copy(update={field: ["wordpress_ekologus"]})

    with pytest.raises(ContentProductionClassificationValidationError) as error:
        _build(freshness=freshness)

    assert error.value.code == "freshness_connector_scope_mismatch"


@pytest.mark.parametrize("evidence_id", ["ev_unlisted", " "], ids=["unlisted", "empty"])
def test_current_builder_rejects_catalog_item_evidence_outside_declared_scope(
    evidence_id: str,
) -> None:
    catalog = _catalog()
    first_item = catalog.items[0].model_copy(update={"evidence_id": evidence_id})
    mismatched_catalog = catalog.model_copy(update={"items": [first_item, *catalog.items[1:]]})

    with pytest.raises(ContentProductionClassificationValidationError) as error:
        _build(catalog=mismatched_catalog)

    assert error.value.code == "wordpress_catalog_evidence_mismatch"


def test_current_builder_requires_explicit_recorded_at() -> None:
    with pytest.raises(ContentProductionClassificationValidationError) as error:
        build_current_all_blocked_classification(
            catalog=_catalog(),
            freshness=_freshness(),
            base_revision=BASE_REVISION,
        )

    assert error.value.code == "recorded_at_required"


def test_current_builder_same_inputs_and_timestamp_have_stable_digests() -> None:
    first = _build(recorded_at=CHECKED_AT)
    second = _build(recorded_at=CHECKED_AT)

    assert first.input_digest == second.input_digest
    assert first.run_digest == second.run_digest
    assert first.run_id == second.run_id


def test_current_builder_rejects_same_count_substituted_journal_path(tmp_path: Path) -> None:
    rows = _journal_rows()
    rows[0]["path"] = "/substituted-path"
    journal = tmp_path / "same-count-substituted.csv"
    _write_journal(journal, rows)

    with pytest.raises(ContentProductionClassificationValidationError) as error:
        _build(journal_path=journal)

    assert error.value.code == "current_journal_scope_invalid"


def test_current_builder_normalizes_journal_trailing_slash_without_double_slash(
    tmp_path: Path,
) -> None:
    rows = _journal_rows()
    target_path = "/bdo-co-musi-wiedziec-przedsiebiorca"
    target = next(row for row in rows if row["path"] == target_path)
    target["path"] += "/"
    journal = tmp_path / "trailing-slash.csv"
    _write_journal(journal, rows)

    run = _build(journal_path=journal)
    row = next(item for item in run.rows if item.canonical_path == target_path)

    assert row.public_url == f"https://www.ekologus.pl{target_path}/"
    assert "//" not in row.public_url.removeprefix("https://")


@pytest.mark.parametrize(
    ("kwargs", "code"),
    [
        ({"freshness": _freshness(requires_refresh=True)}, "freshness_requires_refresh"),
        (
            {
                "catalog": _catalog().model_copy(update={"evidence_ids": []}),
            },
            "wordpress_evidence_missing",
        ),
        (
            {
                "catalog": _catalog().model_copy(
                    update={
                        "coverage": _catalog().coverage.model_copy(update={"status": "malformed"})
                    }
                )
            },
            "catalog_coverage_invalid",
        ),
        ({"base_revision": "not-a-revision"}, "base_revision_invalid"),
    ],
    ids=["stale", "missing-wp-evidence", "malformed-coverage", "invalid-base-revision"],
)
def test_current_builder_rejects_unsafe_or_unusable_current_inputs(
    kwargs: dict[str, object],
    code: str,
) -> None:
    with pytest.raises(ContentProductionClassificationValidationError) as error:
        _build(**kwargs)

    assert error.value.code == code
