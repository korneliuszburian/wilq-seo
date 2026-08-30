from __future__ import annotations

import json
import shutil
import sqlite3
import stat
from contextlib import closing
from hashlib import sha256
from pathlib import Path

import pytest
from pydantic import ValidationError

from scripts.inventory_sqlite_schema import main as inventory_main
from wilq.content.knowledge.private_source_reviews import PrivateSourceReviewStore
from wilq.content.knowledge.public_source_reviews import PublicSourceReviewStore
from wilq.content.planning.generated_proposal_store import ContentPlanningProposalStore
from wilq.content.planning.generation_claim_store import (
    ContentPlanningGenerationClaimStore,
)
from wilq.content.quality.semantic_review_store import ContentSemanticReviewStore
from wilq.content.regulatory.source_fact_proposals import (
    RegulatorySourceFactProposalStore,
)
from wilq.content.regulatory.source_reviews import RegulatorySourceReviewStore
from wilq.content.regulatory.source_snapshots import RegulatorySourceSnapshotStore
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.storage.local_state import LocalStateStore
from wilq.storage.schema_versions import SQLITE_SCHEMA_VERSION
from wilq.storage.sqlite_schema_inventory import (
    SqliteSchemaInventory,
    SqliteSchemaInventoryError,
    canonical_sqlite_schema_inventory_json,
    inspect_sqlite_schema,
)

APPLICATION_SHA256 = "a" * 64
SEED_SHA256 = "b" * 64
EXPECTED_POST_S5_TABLES = frozenset(
    {
        "action_mutation_audits",
        "action_validation_states",
        "ads_strategy_reviews",
        "ads_target_guardrail_confirmations",
        "audit_events",
        "codex_runs",
        "codex_stop_events",
        "codex_stop_events_legacy",
        "codex_stop_reconciliation_batches",
        "connector_refresh_runs",
        "content_draft_revision_reviews",
        "content_draft_revisions",
        "content_human_reviews",
        "content_learning_proposal_history",
        "content_learning_proposals",
        "content_measurement_outcome_history",
        "content_measurement_outcomes",
        "content_measurement_window_history",
        "content_measurement_windows",
        "content_new_page_briefs",
        "content_new_page_foundations",
        "content_new_page_revision_apply_claims",
        "content_planning_generation_claims",
        "content_planning_generation_jobs",
        "content_planning_proposal_repairs",
        "content_planning_proposals",
        "content_planning_reviews",
        "content_private_source_reviews",
        "content_production_classifications",
        "content_refresh_preparation_authorizations",
        "content_public_deployments",
        "content_public_source_reviews",
        "content_quality_reviews",
        "content_regulatory_source_fact_proposals",
        "content_regulatory_source_reviews",
        "content_regulatory_source_snapshots",
        "content_section_focus",
        "content_semantic_reviews",
        "content_target_mapping_confirmations",
        "content_wordpress_draft_execution_history",
        "content_wordpress_draft_executions",
        "content_wordpress_revision_apply_claims",
        "content_workflow_audits",
        "job_runs",
        "social_reuse_child_proposals",
        "social_reuse_proposals",
        "social_reuse_reviews",
        "workflow_runs",
    }
)


def _seed_post_s5(path: Path) -> None:
    LocalStateStore(path).status()
    ContentWorkflowStore(path).list_draft_revisions("missing")
    with ContentPlanningProposalStore(path).run_transaction():
        pass
    for store in (
        ContentPlanningGenerationClaimStore(path),
        PrivateSourceReviewStore(path),
        PublicSourceReviewStore(path),
        RegulatorySourceFactProposalStore(path),
        RegulatorySourceSnapshotStore(path),
        RegulatorySourceReviewStore(path),
    ):
        with closing(store._connect()) as connection:
            connection.commit()
    with closing(ContentSemanticReviewStore(path)._write_connection()) as connection:
        connection.commit()


def _seed_ordered_schema(path: Path, statements: list[str]) -> None:
    with sqlite3.connect(path) as connection:
        for statement in statements:
            connection.execute(statement)
        connection.execute(f"PRAGMA user_version = {SQLITE_SCHEMA_VERSION}")


def _small_schema_statements() -> list[str]:
    return [
        """
        CREATE TABLE alpha (
          id INTEGER PRIMARY KEY,
          label TEXT NOT NULL DEFAULT ''
        )
        """,
        """
        CREATE TABLE beta (
          id TEXT PRIMARY KEY,
          alpha_id INTEGER NOT NULL,
          FOREIGN KEY (alpha_id) REFERENCES alpha (id)
        )
        """,
        "CREATE INDEX idx_beta_alpha ON beta (alpha_id)",
    ]


def _application_schema_objects(path: Path) -> dict[str, list[str]]:
    with sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True) as connection:
        rows = connection.execute(
            """
            SELECT type, name
            FROM sqlite_schema
            ORDER BY type, name
            """
        ).fetchall()
    return {
        object_type: sorted(
            name
            for row_type, name in rows
            if row_type == object_type and not name.startswith("sqlite_")
        )
        for object_type in ("index", "table", "trigger")
    }


def _valid_inventory_payload(path: Path) -> dict[str, object]:
    _seed_ordered_schema(path, _small_schema_statements())
    return inspect_sqlite_schema(
        path,
        application_sha256=APPLICATION_SHA256,
        seed_sha256=SEED_SHA256,
    ).model_dump(mode="python")


@pytest.mark.parametrize("invalid_size", ["4096", 4096.0, True, -1])
def test_inventory_receipt_rejects_non_strict_or_negative_source_sizes(
    tmp_path: Path,
    invalid_size: object,
) -> None:
    payload = _valid_inventory_payload(tmp_path / "invalid-size.sqlite3")
    source_bytes = payload["source_bytes"]
    assert isinstance(source_bytes, dict)
    source_bytes["size_bytes"] = invalid_size

    with pytest.raises(ValidationError) as raised:
        SqliteSchemaInventory.model_validate(payload)

    assert raised.value.errors(include_url=False)[0]["loc"] == (
        "source_bytes",
        "size_bytes",
    )


@pytest.mark.parametrize(
    "invalid_digest",
    [b"a" * 64, "A" * 64, "a" * 63, "g" * 64],
)
def test_inventory_receipt_rejects_non_strict_or_malformed_digests(
    tmp_path: Path,
    invalid_digest: object,
) -> None:
    payload = _valid_inventory_payload(tmp_path / "invalid-digest.sqlite3")
    source_bytes = payload["source_bytes"]
    assert isinstance(source_bytes, dict)
    source_bytes["sha256"] = invalid_digest

    with pytest.raises(ValidationError) as raised:
        SqliteSchemaInventory.model_validate(payload)

    assert raised.value.errors(include_url=False)[0]["loc"] == (
        "source_bytes",
        "sha256",
    )


def test_inventory_receipt_rejects_unknown_fields(tmp_path: Path) -> None:
    payload = _valid_inventory_payload(tmp_path / "unknown-field.sqlite3")
    payload["unexpected"] = "not-in-wilq_sqlite_schema_inventory_v1"

    with pytest.raises(ValidationError) as raised:
        SqliteSchemaInventory.model_validate(payload)

    assert raised.value.errors(include_url=False)[0]["loc"] == ("unexpected",)
    assert raised.value.errors(include_url=False)[0]["type"] == "extra_forbidden"


def test_post_s5_inventory_is_complete_lineage_bound_and_byte_exact(tmp_path: Path) -> None:
    path = tmp_path / "post-s5.sqlite3"
    _seed_post_s5(path)
    before_bytes = path.read_bytes()
    before_mode = stat.S_IMODE(path.stat().st_mode)
    expected_objects = _application_schema_objects(path)

    assert set(expected_objects["table"]) == EXPECTED_POST_S5_TABLES

    inventory = inspect_sqlite_schema(
        path,
        application_sha256=APPLICATION_SHA256,
        seed_sha256=SEED_SHA256,
    )

    assert inventory.identity.sqlite_user_version == SQLITE_SCHEMA_VERSION == 8
    assert inventory.identity.sqlite_application_id == 0
    assert inventory.identity.application_sha256 == APPLICATION_SHA256
    assert inventory.identity.seed_sha256 == SEED_SHA256
    assert inventory.compatibility.status == "unverified_post_s5"
    assert inventory.compatibility.reasons == ("expected_identity_missing",)
    assert [item.name for item in inventory.catalog.tables] == expected_objects["table"]
    assert [item.name for item in inventory.catalog.indexes] == expected_objects["index"]
    assert [item.name for item in inventory.catalog.triggers] == expected_objects["trigger"]
    assert inventory.catalog.unsupported_objects == ()
    legacy_table = next(
        item for item in inventory.catalog.tables if item.name == "codex_stop_events_legacy"
    )
    assert [column.name for column in legacy_table.columns] == [
        "batch_id",
        "manifest_sha256",
        "source_id",
        "started_at",
        "payload_json",
        "payload_sha256",
        "copied_at",
    ]
    assert inventory.source_bytes.sha256 == sha256(before_bytes).hexdigest()
    assert inventory.source_bytes.size_bytes == len(before_bytes)
    assert inventory.source_bytes.preserved is True
    assert path.read_bytes() == before_bytes
    assert stat.S_IMODE(path.stat().st_mode) == before_mode
    assert not any(Path(f"{path}{suffix}").exists() for suffix in ("-journal", "-shm", "-wal"))

    exact = inspect_sqlite_schema(
        path,
        application_sha256=APPLICATION_SHA256,
        seed_sha256=SEED_SHA256,
        expected_identity_sha256=inventory.identity.identity_sha256,
    )
    assert exact.identity == inventory.identity
    assert exact.catalog == inventory.catalog
    assert exact.compatibility.status == "exact_post_s5"
    assert exact.compatibility.reasons == ()
    assert str(path) not in canonical_sqlite_schema_inventory_json(exact)


def test_catalog_and_identity_are_canonical_across_creation_order(tmp_path: Path) -> None:
    statements = _small_schema_statements()
    first_path = tmp_path / "first.sqlite3"
    second_path = tmp_path / "second.sqlite3"
    _seed_ordered_schema(first_path, statements)
    _seed_ordered_schema(second_path, [statements[1], statements[0], statements[2]])

    first = inspect_sqlite_schema(
        first_path,
        application_sha256=APPLICATION_SHA256,
        seed_sha256=SEED_SHA256,
    )
    second = inspect_sqlite_schema(
        second_path,
        application_sha256=APPLICATION_SHA256,
        seed_sha256=SEED_SHA256,
    )

    assert first.catalog == second.catalog
    assert first.identity == second.identity
    assert first.identity.catalog_sha256 == (
        "".join(
            (
                "feb217c277be24b3e202",  # pragma: allowlist secret
                "392b8bb968f9879bd28b",  # pragma: allowlist secret
                "8aa543b5becde42de34d",  # pragma: allowlist secret
                "9c1c",  # pragma: allowlist secret
            )
        )
    )
    assert first.identity.identity_sha256 == (
        "".join(
            (
                "781035633961d069fc03d5e",  # pragma: allowlist secret
                "68f652fe9bef030c6a977c",  # pragma: allowlist secret
                "468fd9c9ef05fd5c9c5",  # pragma: allowlist secret
            )
        )
    )
    assert first.source_bytes.sha256 != second.source_bytes.sha256
    assert canonical_sqlite_schema_inventory_json(first) == (
        canonical_sqlite_schema_inventory_json(
            inspect_sqlite_schema(
                first_path,
                application_sha256=APPLICATION_SHA256,
                seed_sha256=SEED_SHA256,
            )
        )
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "DROP TABLE beta",
        "CREATE TABLE gamma (id INTEGER PRIMARY KEY, note TEXT)",
        "DROP INDEX idx_beta_alpha",
        "CREATE INDEX idx_alpha_label ON alpha (label)",
        """
        CREATE TRIGGER trg_alpha_after_insert
        AFTER INSERT ON alpha
        BEGIN
          UPDATE alpha SET label = label WHERE id = NEW.id;
        END
        """,
        "ALTER TABLE alpha ADD COLUMN changed INTEGER NOT NULL DEFAULT 0",
        "CREATE VIEW alpha_ids AS SELECT id FROM alpha",
    ],
)
def test_missing_extra_or_changed_schema_objects_fail_exact_identity(
    tmp_path: Path,
    mutation: str,
) -> None:
    baseline_path = tmp_path / "baseline.sqlite3"
    changed_path = tmp_path / "changed.sqlite3"
    _seed_ordered_schema(baseline_path, _small_schema_statements())
    baseline = inspect_sqlite_schema(
        baseline_path,
        application_sha256=APPLICATION_SHA256,
        seed_sha256=SEED_SHA256,
    )
    shutil.copy2(baseline_path, changed_path)
    with sqlite3.connect(changed_path) as connection:
        connection.execute(mutation)
    changed_bytes = changed_path.read_bytes()

    changed = inspect_sqlite_schema(
        changed_path,
        application_sha256=APPLICATION_SHA256,
        seed_sha256=SEED_SHA256,
        expected_identity_sha256=baseline.identity.identity_sha256,
    )

    assert changed.identity.catalog_sha256 != baseline.identity.catalog_sha256
    assert changed.identity.identity_sha256 != baseline.identity.identity_sha256
    assert changed.compatibility.status == "unsupported_schema_identity"
    assert "identity_sha256_mismatch" in changed.compatibility.reasons
    assert changed_path.read_bytes() == changed_bytes
    if mutation.startswith("CREATE VIEW"):
        assert changed.compatibility.reasons == (
            "unsupported_object_type",
            "identity_sha256_mismatch",
        )


@pytest.mark.parametrize(
    ("application_sha256", "seed_sha256"),
    [("c" * 64, SEED_SHA256), (APPLICATION_SHA256, "d" * 64)],
)
def test_changed_authoritative_lineage_digest_fails_exact_identity(
    tmp_path: Path,
    application_sha256: str,
    seed_sha256: str,
) -> None:
    path = tmp_path / "lineage.sqlite3"
    _seed_ordered_schema(path, _small_schema_statements())
    baseline = inspect_sqlite_schema(
        path,
        application_sha256=APPLICATION_SHA256,
        seed_sha256=SEED_SHA256,
    )

    changed = inspect_sqlite_schema(
        path,
        application_sha256=application_sha256,
        seed_sha256=seed_sha256,
        expected_identity_sha256=baseline.identity.identity_sha256,
    )

    assert changed.catalog == baseline.catalog
    assert changed.identity.catalog_sha256 == baseline.identity.catalog_sha256
    assert changed.identity.identity_sha256 != baseline.identity.identity_sha256
    assert changed.compatibility.status == "unsupported_schema_identity"
    assert changed.compatibility.reasons == ("identity_sha256_mismatch",)


@pytest.mark.parametrize(
    ("application_sha256", "seed_sha256", "expected_reasons"),
    [
        (
            None,
            None,
            ("application_sha256_missing", "seed_sha256_missing"),
        ),
        (None, SEED_SHA256, ("application_sha256_missing",)),
        (APPLICATION_SHA256, None, ("seed_sha256_missing",)),
    ],
    ids=["both", "application", "seed"],
)
def test_missing_authoritative_lineage_never_claims_exact_identity(
    tmp_path: Path,
    application_sha256: str | None,
    seed_sha256: str | None,
    expected_reasons: tuple[str, ...],
) -> None:
    path = tmp_path / "missing-lineage.sqlite3"
    _seed_ordered_schema(path, _small_schema_statements())
    baseline = inspect_sqlite_schema(
        path,
        application_sha256=application_sha256,
        seed_sha256=seed_sha256,
    )

    candidate = inspect_sqlite_schema(
        path,
        application_sha256=application_sha256,
        seed_sha256=seed_sha256,
        expected_identity_sha256=baseline.identity.identity_sha256,
    )

    assert candidate.identity.identity_sha256 == baseline.identity.identity_sha256
    assert candidate.compatibility.status == "unverified_post_s5"
    assert candidate.compatibility.reasons == expected_reasons


@pytest.mark.parametrize("user_version", [SQLITE_SCHEMA_VERSION - 1, SQLITE_SCHEMA_VERSION + 1])
def test_unsupported_schema_version_is_classified_without_mutation(
    tmp_path: Path,
    user_version: int,
) -> None:
    path = tmp_path / f"unsupported-v{user_version}.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE preserved (id TEXT PRIMARY KEY, payload TEXT)")
        connection.execute(f"PRAGMA user_version = {user_version}")
    before = path.read_bytes()

    inventory = inspect_sqlite_schema(path)

    assert inventory.identity.sqlite_user_version == user_version
    assert inventory.compatibility.status == "unsupported_schema_identity"
    assert inventory.compatibility.reasons == ("unsupported_user_version",)
    assert path.read_bytes() == before
    with sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == user_version
        assert connection.execute(
            "SELECT name FROM sqlite_schema WHERE type = 'table' AND name = 'preserved'"
        ).fetchone() == ("preserved",)


def test_cli_is_uri_safe_deterministic_and_never_upgrades_legacy_source(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "stan # D1? żółć.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE legacy (id TEXT PRIMARY KEY)")
        connection.execute(f"PRAGMA user_version = {SQLITE_SCHEMA_VERSION - 1}")
    before = path.read_bytes()
    before_mode = stat.S_IMODE(path.stat().st_mode)
    argv = ["--sqlite-path", str(path)]

    assert inventory_main(argv) == 3
    first_output = capsys.readouterr().out
    assert inventory_main(argv) == 3
    second_output = capsys.readouterr().out

    assert first_output == second_output
    payload = json.loads(first_output)
    assert payload["compatibility"] == {
        "expected_identity_sha256": None,
        "reasons": ["unsupported_user_version"],
        "status": "unsupported_schema_identity",
    }
    assert payload["identity"]["sqlite_user_version"] == SQLITE_SCHEMA_VERSION - 1
    assert str(path) not in first_output
    assert path.read_bytes() == before
    assert stat.S_IMODE(path.stat().st_mode) == before_mode
    assert not any(Path(f"{path}{suffix}").exists() for suffix in ("-journal", "-shm", "-wal"))


@pytest.mark.parametrize("suffix", ["-journal", "-shm", "-wal"])
def test_preexisting_sqlite_sidecar_is_blocked_before_inspection(
    tmp_path: Path,
    suffix: str,
) -> None:
    path = tmp_path / "not-isolated.sqlite3"
    _seed_ordered_schema(path, _small_schema_statements())
    before = path.read_bytes()
    sidecar = Path(f"{path}{suffix}")
    sidecar.write_bytes(b"untrusted-sidecar")

    with pytest.raises(SqliteSchemaInventoryError, match="isolated file"):
        inspect_sqlite_schema(path)

    assert path.read_bytes() == before
    assert sidecar.read_bytes() == b"untrusted-sidecar"


def test_missing_source_is_blocked_without_creating_a_database(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "missing.sqlite3"

    assert inventory_main(["--sqlite-path", str(path)]) == 2

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "blocked"
    assert payload["error"] == "SQLite source file is required"
    assert not path.exists()
