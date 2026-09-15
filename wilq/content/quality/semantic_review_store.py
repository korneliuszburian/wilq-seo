from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from wilq.content.quality.review_packet_binding import (
    ContentReviewBindingBlocker,
    ContentReviewClaimToken,
)
from wilq.content.quality.semantic_review_contracts import (
    ContentSemanticReview,
    ContentSemanticReviewBlocker,
)
from wilq.content.workflow.documents.codex_revision_commit import (
    codex_completion_state,
    persist_codex_completion,
)
from wilq.content.workflow.runtime.codex_run_lifecycle import effective_deadline
from wilq.schemas import CodexRun
from wilq.schemas.core import utc_now
from wilq.security.redaction import redact_mapping
from wilq.storage.local_state import DEFAULT_STATE_DB, state_db_path
from wilq.storage.private_paths import prepare_private_store_path
from wilq.storage.schema_versions import (
    ensure_sqlite_schema_version,
    reject_newer_sqlite_schema,
)


class SemanticReviewStorageActivationRequired(RuntimeError):
    pass


class SemanticReviewConflict(RuntimeError):
    pass


class SemanticReviewDeadlineExpired(SemanticReviewConflict):
    pass


@dataclass(frozen=True, slots=True)
class SemanticReviewClaim:
    run: CodexRun | None = None
    review: ContentSemanticReview | None = None
    newly_claimed: bool = False
    blocker: ContentSemanticReviewBlocker | None = None


SemanticReviewClaimGuard = Callable[
    [sqlite3.Connection], ContentSemanticReviewBlocker | None
]


def validate_content_review_claim_token(
    connection: sqlite3.Connection,
    token: ContentReviewClaimToken | None,
) -> ContentReviewBindingBlocker | None:
    if token is None:
        return None
    validators = (
        _validate_claim_revision,
        _validate_claim_proposal,
        _validate_claim_packet,
        _validate_claim_source_pack,
        _validate_claim_identity,
        _validate_claim_classification,
        _validate_claim_source_facts,
    )
    for validator in validators:
        blocker = validator(connection, token)
        if blocker is not None:
            return blocker
    return None


def _validate_claim_revision(
    connection: sqlite3.Connection,
    token: ContentReviewClaimToken,
) -> ContentReviewBindingBlocker | None:
    row = _claim_json(
        connection,
        "SELECT payload_json FROM content_draft_revisions WHERE revision_id = ?",
        (token.revision_id,),
    )
    expected = {
        "work_item_id": token.work_item_id,
        "revision_id": token.revision_id,
        "content_digest": token.revision_digest,
        "planning_digest": token.planning_digest,
        "planning_input_digest": token.planning_input_digest,
        "research_packet_id": token.packet_id,
        "research_packet_digest": token.packet_digest,
    }
    if row is None or any(row.get(key) != value for key, value in expected.items()):
        return _claim_blocker(
            "stale_revision",
            "Rewizja zmieniła się przed uruchomieniem review",
            "Bieżąca rewizja nie odpowiada tokenowi preflight.",
        )
    return None


def _validate_claim_proposal(
    connection: sqlite3.Connection,
    token: ContentReviewClaimToken,
) -> ContentReviewBindingBlocker | None:
    row = _claim_json(
        connection,
        """
        SELECT payload_json FROM content_planning_proposals
        WHERE work_item_id = ? AND planning_input_digest = ?
        ORDER BY proposal_version DESC LIMIT 1
        """,
        (token.work_item_id, token.planning_input_digest),
    )
    expected = {
        "planning_digest": token.planning_digest,
        "planning_input_digest": token.planning_input_digest,
        "research_packet_id": token.packet_id,
        "research_packet_digest": token.packet_digest,
    }
    if row is None or (
        token.proposal_id is not None and row.get("proposal_id") != token.proposal_id
    ) or any(row.get(key) != value for key, value in expected.items()):
        return _claim_blocker(
            "planning_digest_mismatch",
            "Proposal zmienił się przed uruchomieniem review",
            "Bieżący proposal nie odpowiada tokenowi preflight.",
        )
    return None


def _validate_claim_packet(
    connection: sqlite3.Connection,
    token: ContentReviewClaimToken,
) -> ContentReviewBindingBlocker | None:
    row = _claim_json(
        connection,
        "SELECT payload_json FROM content_research_packets WHERE packet_id = ?",
        (token.packet_id,),
    )
    context = {} if row is None else row.get("context_receipt") or {}
    expected = {
        "packet_id": token.packet_id,
        "packet_digest": token.packet_digest,
        "status": "exact_current",
        "current_work_item_id": token.work_item_id,
        "source_pack_binding_id": token.source_pack_binding_id,
        "source_pack_binding_digest": token.source_pack_binding_digest,
        "identity_binding_id": token.identity_binding_id,
        "identity_binding_digest": token.identity_binding_digest,
        "source_fact_registry_digest": token.source_fact_registry_digest,
        "source_facts_digest": token.source_facts_digest,
    }
    if row is None or any(row.get(key) != value for key, value in expected.items()) or (
        token.current_packet_status not in {None, "current"}
        or (
            token.current_source_pack_binding_id is not None
            and token.current_source_pack_binding_id != token.source_pack_binding_id
        )
        or (
            token.current_source_pack_binding_digest is not None
            and token.current_source_pack_binding_digest != token.source_pack_binding_digest
        )
        or (
            token.current_identity_binding_id is not None
            and token.current_identity_binding_id != token.identity_binding_id
        )
        or (
            token.current_identity_binding_digest is not None
            and token.current_identity_binding_digest != token.identity_binding_digest
        )
        or context.get("classification_run_id") != token.classification_run_id
        or context.get("classification_run_digest") != token.classification_run_digest
    ):
        return _claim_blocker(
            "research_packet_conflict",
            "Research packet nie jest aktualny",
            "Bieżący packet nie odpowiada tokenowi preflight.",
        )
    return None


def _validate_claim_source_pack(
    connection: sqlite3.Connection,
    token: ContentReviewClaimToken,
) -> ContentReviewBindingBlocker | None:
    row = _claim_row(
        connection,
        """
        SELECT binding_id, binding_digest, identity_binding_id,
               identity_binding_digest, current_work_item_id, source_facts_digest,
               payload_json, status
        FROM content_source_pack_bindings WHERE binding_id = ?
        """,
        (token.source_pack_binding_id,),
    )
    latest = _claim_row(
        connection,
        """
        SELECT binding_id, binding_digest, source_facts_digest
        FROM content_source_pack_bindings
        WHERE current_work_item_id = ?
        ORDER BY recorded_at DESC, binding_id DESC LIMIT 1
        """,
        (token.work_item_id,),
    )
    expected = {
        "binding_id": token.source_pack_binding_id,
        "binding_digest": token.source_pack_binding_digest,
        "identity_binding_id": token.identity_binding_id,
        "identity_binding_digest": token.identity_binding_digest,
        "current_work_item_id": token.work_item_id,
        "status": "exact_current",
    }
    if (
        row is None
        or latest is None
        or any(row.get(key) != value for key, value in expected.items())
        or (
        latest.get("binding_id")
        != (token.current_source_pack_binding_id or token.source_pack_binding_id)
        or latest.get("binding_digest")
        != (token.current_source_pack_binding_digest or token.source_pack_binding_digest)
        )
    ):
        return _claim_blocker(
            "research_packet_conflict",
            "Source pack zmienił się przed uruchomieniem review",
            "Latest source-pack binding nie odpowiada packet tokenowi.",
        )
    return None


def _validate_claim_identity(
    connection: sqlite3.Connection,
    token: ContentReviewClaimToken,
) -> ContentReviewBindingBlocker | None:
    row = _claim_row(
        connection,
        """
        SELECT binding_id, binding_digest, current_work_item_id,
               classification_run_id, classification_run_digest,
               classification_source_row_digest, status
        FROM content_delivery_identity_bindings WHERE binding_id = ?
        """,
        (token.identity_binding_id,),
    )
    latest = _claim_row(
        connection,
        """
        SELECT binding_id, binding_digest FROM content_delivery_identity_bindings
        WHERE current_work_item_id = ?
        ORDER BY recorded_at DESC, binding_id DESC LIMIT 1
        """,
        (token.work_item_id,),
    )
    expected = {
        "binding_id": token.identity_binding_id,
        "binding_digest": token.identity_binding_digest,
        "current_work_item_id": token.work_item_id,
        "classification_run_id": token.classification_run_id,
        "classification_run_digest": token.classification_run_digest,
        "classification_source_row_digest": token.classification_source_row_digest,
        "status": "exact_current",
    }
    if (
        row is None
        or latest is None
        or any(row.get(key) != value for key, value in expected.items())
        or (
        latest.get("binding_id")
        != (token.current_identity_binding_id or token.identity_binding_id)
        or latest.get("binding_digest")
        != (token.current_identity_binding_digest or token.identity_binding_digest)
        )
    ):
        return _claim_blocker(
            "research_packet_conflict",
            "Identity binding zmienił się przed uruchomieniem review",
            "Latest delivery identity nie odpowiada packet tokenowi.",
        )
    return None


def _validate_claim_classification(
    connection: sqlite3.Connection,
    token: ContentReviewClaimToken,
) -> ContentReviewBindingBlocker | None:
    if token.classification_run_id is None:
        return None
    row = _claim_row(
        connection,
        """
        SELECT run_id, run_digest, payload_json
        FROM content_production_classifications WHERE run_id = ?
        """,
        (token.classification_run_id,),
    )
    latest = _claim_row(
        connection,
        """
        SELECT run_id, run_digest FROM content_production_classifications
        ORDER BY recorded_at DESC, rowid DESC LIMIT 1
        """,
        (),
    )
    if row is None or latest is None or row.get("run_digest") != token.classification_run_digest:
        return _claim_blocker(
            "research_packet_conflict",
            "Classification zmieniła się przed uruchomieniem review",
            "Bieżąca klasyfikacja nie odpowiada context receipt packetu.",
        )
    rows = _json_value(row.get("payload_json"), "rows")
    current = next(
        (item for item in rows if item.get("current_work_item_id") == token.work_item_id),
        None,
    )
    if latest.get("run_id") != token.classification_run_id or latest.get(
        "run_digest"
    ) != token.classification_run_digest or (
        current is not None
        and current.get("source_packet_row_digest") != token.classification_source_row_digest
    ):
        return _claim_blocker(
            "research_packet_conflict",
            "Classification zmieniła się przed uruchomieniem review",
            "Bieżący classification row nie odpowiada exact context receipt.",
        )
    return None


def _validate_claim_source_facts(
    connection: sqlite3.Connection,
    token: ContentReviewClaimToken,
) -> ContentReviewBindingBlocker | None:
    if token.source_fact_receipt_id is None:
        return None
    row = _claim_row(
        connection,
        """
        SELECT receipt_id, receipt_digest, payload_json
        FROM content_source_fact_authority_receipts
        WHERE receipt_id = ? AND identity_binding_id = ? AND current_work_item_id = ?
        """,
        (token.source_fact_receipt_id, token.identity_binding_id, token.work_item_id),
    )
    latest = _claim_row(
        connection,
        """
        SELECT receipt_id, receipt_digest FROM content_source_fact_authority_receipts
        WHERE identity_binding_id = ? AND current_work_item_id = ?
        ORDER BY rowid DESC LIMIT 1
        """,
        (token.identity_binding_id, token.work_item_id),
    )
    payload = {} if row is None else _json_value(row.get("payload_json"))
    snapshot = payload.get("authority_snapshot") or {}
    if row is None or latest is None or (
        row.get("receipt_digest") != token.source_fact_receipt_digest
        or latest.get("receipt_id") != token.source_fact_receipt_id
        or latest.get("receipt_digest") != token.source_fact_receipt_digest
        or snapshot.get("context_digest") != token.source_fact_snapshot_digest
        or snapshot.get("source_fact_provenance_digest") != token.source_fact_provenance_digest
    ):
        return _claim_blocker(
            "research_packet_conflict",
            "Source-fact authority zmieniła się przed uruchomieniem review",
            "Latest source-fact receipt nie odpowiada exact context receipt.",
        )
    return None


def _claim_row(
    connection: sqlite3.Connection,
    query: str,
    parameters: tuple[object, ...],
) -> dict[str, Any] | None:
    try:
        row = connection.execute(query, parameters).fetchone()
    except sqlite3.OperationalError:
        return None
    return None if row is None else dict(row)


def _claim_json(
    connection: sqlite3.Connection,
    query: str,
    parameters: tuple[object, ...],
) -> dict[str, Any] | None:
    row = _claim_row(connection, query, parameters)
    return None if row is None else _json_value(row.get("payload_json"))


def _json_value(payload: object, key: str | None = None) -> Any:
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except (TypeError, ValueError):
            payload = None
    if not isinstance(payload, dict):
        return [] if key == "rows" else {}
    value = payload if key is None else payload.get(key, [])
    return value if isinstance(value, (dict, list)) else {}


def _claim_blocker(
    code: str,
    label: str,
    reason: str,
) -> ContentReviewBindingBlocker:
    return ContentReviewBindingBlocker(
        code=code,
        label=label,
        reason=reason,
        next_step="Odśwież workspace i uruchom review dla bieżącej exact rewizji.",
    )


def content_semantic_review_store() -> ContentSemanticReviewStore:
    return ContentSemanticReviewStore(state_db_path())


class ContentSemanticReviewStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def write_ready(self) -> bool:
        if self.path != DEFAULT_STATE_DB:
            return True
        connection = self._read_connection()
        if connection is None:
            return False
        with connection:
            return _table_exists(connection, "content_semantic_reviews")

    def latest(self, work_item_id: str) -> ContentSemanticReview | None:
        connection = self._read_connection()
        if connection is None:
            return None
        with connection:
            if not _table_exists(connection, "content_semantic_reviews"):
                return None
            row = connection.execute(
                """
                SELECT payload_json
                FROM content_semantic_reviews
                WHERE work_item_id = ?
                ORDER BY created_at DESC, review_id DESC
                LIMIT 1
                """,
                (work_item_id,),
            ).fetchone()
        return _review_from_row(row)

    def for_revision(
        self,
        work_item_id: str,
        revision_id: str,
        revision_digest: str,
    ) -> ContentSemanticReview | None:
        connection = self._read_connection()
        if connection is None:
            return None
        with connection:
            if not _table_exists(connection, "content_semantic_reviews"):
                return None
            row = _exact_review_row(
                connection,
                work_item_id,
                revision_id,
                revision_digest,
            )
        return _review_from_row(row)

    def for_revision_id(
        self,
        work_item_id: str,
        revision_id: str,
    ) -> ContentSemanticReview | None:
        connection = self._read_connection()
        if connection is None:
            return None
        with connection:
            if not _table_exists(connection, "content_semantic_reviews"):
                return None
            row = connection.execute(
                """
                SELECT payload_json
                FROM content_semantic_reviews
                WHERE work_item_id = ?
                  AND revision_id = ?
                  AND criteria_version = 'wilq_semantic_content_review_v1'
                LIMIT 1
                """,
                (work_item_id, revision_id),
            ).fetchone()
        return _review_from_row(row)

    def save_generated(
        self,
        review: ContentSemanticReview,
        completed_run: CodexRun,
    ) -> ContentSemanticReview:
        safe_review, safe_run = _validated_models(review, completed_run)
        with self._write_connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if (
                _exact_review_row(
                    connection,
                    safe_review.work_item_id,
                    safe_review.revision_id,
                    safe_review.revision_digest,
                )
                is not None
            ):
                raise SemanticReviewConflict("Semantic review appeared concurrently.")
            if codex_completion_state(connection, safe_run) != "started":
                raise SemanticReviewConflict("Semantic review run is already completed.")
            if utc_now() >= effective_deadline(safe_run):
                raise SemanticReviewDeadlineExpired(
                    "Semantic review deadline expired before atomic commit."
                )
            connection.execute(
                """
                INSERT INTO content_semantic_reviews (
                  review_id, work_item_id, revision_id, revision_digest,
                  criteria_version, created_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    safe_review.review_id,
                    safe_review.work_item_id,
                    safe_review.revision_id,
                    safe_review.revision_digest,
                    safe_review.criteria_version,
                    safe_review.created_at.isoformat(),
                    safe_review.model_dump_json(),
                ),
            )
            persist_codex_completion(connection, safe_run)
        return safe_review

    def claim_run(
        self,
        *,
        work_item_id: str,
        revision_id: str,
        revision_digest: str,
        endpoint: str,
        evidence_ids: list[str],
        planning_input_digest: str | None,
        timeout_seconds: float,
        claim_guard: SemanticReviewClaimGuard | None = None,
    ) -> SemanticReviewClaim:
        """Atomically claim one active semantic run for an exact revision."""
        from wilq.storage.local_state import LocalStateStore

        LocalStateStore(self.path).status()
        with self._write_connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if claim_guard is not None:
                blocker = claim_guard(connection)
                if blocker is not None:
                    return SemanticReviewClaim(blocker=blocker)
            review_row = _exact_review_row(
                connection, work_item_id, revision_id, revision_digest
            )
            review = _review_from_row(review_row)
            if review is not None:
                return SemanticReviewClaim(review=review)
            runs = connection.execute(
                "SELECT payload_json FROM codex_runs ORDER BY started_at DESC, id DESC"
            ).fetchall()
            for row in runs:
                run = CodexRun.model_validate_json(cast(str, row["payload_json"]))
                if (
                    run.status == "started"
                    and run.hook == "content_semantic_review"
                    and run.planning_input_digest == planning_input_digest
                    and endpoint in run.used_endpoints
                ):
                    if utc_now() >= effective_deadline(run):
                        expired = run.model_copy(
                            update={
                                "status": "failed",
                                "completed_at": utc_now(),
                                "error": "semantic_review_timeout",
                            }
                        )
                        connection.execute(
                            "UPDATE codex_runs SET started_at = ?, payload_json = ? WHERE id = ?",
                            (
                                expired.started_at.isoformat(),
                                json.dumps(
                                    expired.model_dump(mode="json"),
                                    sort_keys=True,
                                    separators=(",", ":"),
                                ),
                                expired.id,
                            ),
                        )
                        continue
                    return SemanticReviewClaim(run=run)
            run = CodexRun(
                id=f"codex_content_semantic_review_{uuid4().hex}",
                skill="wilq-content-operator",
                hook="content_semantic_review",
                source="wilq_api",
                status="started",
                used_endpoints=[endpoint],
                evidence_ids=list(dict.fromkeys(evidence_ids)),
                planning_input_digest=planning_input_digest,
                deadline_at=utc_now() + timedelta(seconds=timeout_seconds),
            )
            payload_json = json.dumps(
                run.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
            )
            connection.execute(
                "INSERT INTO codex_runs (id, started_at, payload_json) VALUES (?, ?, ?)",
                (run.id, run.started_at.isoformat(), payload_json),
            )
            return SemanticReviewClaim(run=run, newly_claimed=True)

    def _write_connection(self) -> sqlite3.Connection:
        prepare_private_store_path(
            self.path,
            normalize_existing_parent=self.path == DEFAULT_STATE_DB,
        )
        connection = sqlite3.connect(self.path)
        self.path.chmod(0o600)
        connection.row_factory = sqlite3.Row
        reject_newer_sqlite_schema(connection)
        if self.path == DEFAULT_STATE_DB and not _table_exists(
            connection, "content_semantic_reviews"
        ):
            connection.close()
            raise SemanticReviewStorageActivationRequired(
                "Semantic-review storage requires an approved maintenance window."
            )
        connection.execute(_CREATE_TABLE)
        ensure_sqlite_schema_version(connection)
        return connection

    def _read_connection(self) -> sqlite3.Connection | None:
        if not self.path.exists():
            return None
        connection = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        reject_newer_sqlite_schema(connection)
        return connection


_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS content_semantic_reviews (
  review_id TEXT PRIMARY KEY,
  work_item_id TEXT NOT NULL,
  revision_id TEXT NOT NULL,
  revision_digest TEXT NOT NULL,
  criteria_version TEXT NOT NULL,
  created_at TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  UNIQUE (work_item_id, revision_id, revision_digest, criteria_version)
)
"""


def _exact_review_row(
    connection: sqlite3.Connection,
    work_item_id: str,
    revision_id: str,
    revision_digest: str,
) -> sqlite3.Row | None:
    return cast(
        sqlite3.Row | None,
        connection.execute(
            """
            SELECT payload_json
            FROM content_semantic_reviews
            WHERE work_item_id = ?
              AND revision_id = ?
              AND revision_digest = ?
              AND criteria_version = 'wilq_semantic_content_review_v1'
            LIMIT 1
            """,
            (work_item_id, revision_id, revision_digest),
        ).fetchone(),
    )


def _review_from_row(row: sqlite3.Row | None) -> ContentSemanticReview | None:
    if row is None:
        return None
    return ContentSemanticReview.model_validate(json.loads(cast(str, row["payload_json"])))


def _table_exists(connection: sqlite3.Connection, name: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (name,),
        ).fetchone()
        is not None
    )


def _validated_models(
    review: ContentSemanticReview,
    completed_run: CodexRun,
) -> tuple[ContentSemanticReview, CodexRun]:
    safe_review = ContentSemanticReview.model_validate(
        redact_mapping(review.model_dump(mode="json"))
    )
    safe_run = CodexRun.model_validate(redact_mapping(completed_run.model_dump(mode="json")))
    if safe_review.codex_run_id != safe_run.id:
        raise ValueError("Semantic review must reference its exact Codex run.")
    if safe_run.status != "completed" or safe_run.completed_at is None or safe_run.error:
        raise ValueError("Semantic review requires one successful terminal Codex run.")
    return safe_review, safe_run


__all__ = [
    "ContentSemanticReviewStore",
    "SemanticReviewConflict",
    "SemanticReviewDeadlineExpired",
    "SemanticReviewClaim",
    "SemanticReviewStorageActivationRequired",
    "content_semantic_review_store",
    "validate_content_review_claim_token",
]
