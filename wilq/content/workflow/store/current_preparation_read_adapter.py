"""Transaction-bound read adapters for current refresh-preparation receipts.

The persistence guards run inside a caller-owned SQLite transaction.  They
must therefore re-read every readiness input from that exact connection;
calling a store method here would open a second connection and could observe a
different fixed point.
"""

from __future__ import annotations

import sqlite3
from typing import cast

from wilq.content.workflow.current_preparation_readiness_contracts import (
    ContentCurrentPreparationReadiness,
)
from wilq.content.workflow.decisions.production import (
    ContentProductionClassificationProjection,
    ContentProductionClassificationRow,
    ContentProductionClassificationRun,
    project_content_production_classification,
)
from wilq.content.workflow.delivery_identity import ContentDeliveryIdentityBinding
from wilq.content.workflow.source_fact_authority import ContentSourceFactAuthorityReceipt
from wilq.content.workflow.source_pack_binding import ContentSourcePackBinding
from wilq.content.workflow.store.store_delivery_identity import binding_from_row
from wilq.content.workflow.store.store_production_classification import (
    load_latest_production_classification_from_connection,
)
from wilq.content.workflow.store.store_source_pack_binding import (
    _binding_from_source_pack_row,
)


class TransactionBoundCurrentPreparationReadAdapter:
    """Implement readiness read protocols without acquiring another connection."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def load_latest_production_classification(
        self,
    ) -> ContentProductionClassificationRun | None:
        if not _table_exists(self.connection, "content_production_classifications"):
            return None
        return load_latest_production_classification_from_connection(self.connection)

    def load_content_delivery_identity(
        self,
        binding_id: str,
    ) -> ContentDeliveryIdentityBinding | None:
        if not _table_exists(self.connection, "content_delivery_identity_bindings"):
            return None
        row = self.connection.execute(
            "SELECT * FROM content_delivery_identity_bindings WHERE binding_id = ?",
            (binding_id,),
        ).fetchone()
        return None if row is None else binding_from_row(row)

    def list_content_source_pack_bindings(
        self,
        *,
        current_work_item_id: str | None = None,
    ) -> list[ContentSourcePackBinding]:
        if not _table_exists(self.connection, "content_source_pack_bindings"):
            return []
        query = "SELECT * FROM content_source_pack_bindings"
        parameters: tuple[object, ...] = ()
        if current_work_item_id is not None:
            query += " WHERE current_work_item_id = ?"
            parameters = (current_work_item_id,)
        query += " ORDER BY recorded_at ASC, binding_id ASC"
        rows = self.connection.execute(query, parameters).fetchall()
        return [_binding_from_source_pack_row(row) for row in rows]

    def load_production_classification_for_work_item(
        self,
        work_item_id: str,
    ) -> ContentProductionClassificationProjection | None:
        run = self.load_latest_production_classification()
        if run is None:
            return None
        row = run.for_work_item(work_item_id)
        return None if row is None else project_content_production_classification(run, row)

    def load_content_source_fact_authority_receipt_for_identity(
        self,
        identity_binding_id: str,
        current_work_item_id: str,
        source_fact_ids: tuple[str, ...],
    ) -> ContentSourceFactAuthorityReceipt | None:
        """Read the append-only row authority using this transaction's snapshot.

        ``source_fact_ids`` is intentionally not used to select an older
        receipt.  The canonical store reader returns the newest receipt for
        the identity/work item so changed fact sets become a typed blocker in
        the shared source-pack validator.
        """

        del source_fact_ids
        if not _table_exists(self.connection, "content_source_fact_authority_receipts"):
            return None
        rows = self.connection.execute(
            """
            SELECT payload_json
            FROM content_source_fact_authority_receipts
            WHERE identity_binding_id = ?
              AND current_work_item_id = ?
            ORDER BY rowid ASC
            """,
            (identity_binding_id, current_work_item_id),
        ).fetchall()
        receipts: list[ContentSourceFactAuthorityReceipt] = []
        for row in rows:
            try:
                receipts.append(
                    ContentSourceFactAuthorityReceipt.model_validate_json(
                        cast(str, row["payload_json"]),
                        strict=True,
                    )
                )
            except Exception:
                # Match the public store reader: malformed append-only rows
                # are not authority and must not hide a later valid receipt.
                continue
        return receipts[-1] if receipts else None


def resolve_current_preparation_readiness_from_connection(
    connection: sqlite3.Connection,
    work_item_id: str,
    *,
    run: ContentProductionClassificationRun,
    row: ContentProductionClassificationRow,
) -> ContentCurrentPreparationReadiness:
    """Resolve readiness from one caller-owned SQLite transaction."""

    from wilq.content.workflow.current_preparation_readiness import (
        resolve_current_preparation_readiness,
    )

    return resolve_current_preparation_readiness(
        TransactionBoundCurrentPreparationReadAdapter(connection),
        work_item_id,
        run=run,
        row=row,
    )


def _table_exists(connection: sqlite3.Connection, name: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (name,),
        ).fetchone()
        is not None
    )


__all__ = [
    "TransactionBoundCurrentPreparationReadAdapter",
    "resolve_current_preparation_readiness_from_connection",
]
