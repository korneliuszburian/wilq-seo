"""Schema-valid delivery identity fixtures for the drift recovery read."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from wilq.content.workflow.delivery_identity import (
    ContentDeliveryClassificationLookup,
    ContentDeliveryIdentityBinding,
    ContentDeliveryIdentityCommand,
    inventory_evidence_digest,
    reconcile_content_delivery_identity,
)

WORK_ITEM_ID = "content_work_item_inventory_current"
RUN_ID = "content_production_classification_current"
RUN_DIGEST = "a" * 64
DECISION_SET_DIGEST = "b" * 64
ROW_DIGEST = "c" * 64
PUBLIC_URL = "https://www.ekologus.pl/operat-wodnoprawny/"
CANONICAL_PATH = "/operat-wodnoprawny"
EVIDENCE_IDS = ("ev_current",)


def classification_lookup(
    *,
    row_digest: str = ROW_DIGEST,
    row_status: str = "exact",
    freshness_state: str = "fresh",
    requires_refresh: bool = False,
    run_id: str = RUN_ID,
    run_digest: str = RUN_DIGEST,
) -> ContentDeliveryClassificationLookup:
    run: SimpleNamespace | None = None
    if row_status == "exact":
        run = SimpleNamespace(
            run_id=run_id,
            run_digest=run_digest,
            decision_set_digest=DECISION_SET_DIGEST,
            freshness=SimpleNamespace(
                state=freshness_state, requires_refresh=requires_refresh
            ),
            row=SimpleNamespace(
                current_work_item_id=WORK_ITEM_ID,
                canonical_path=CANONICAL_PATH,
                public_url=PUBLIC_URL,
                source_packet_row_digest=row_digest,
                primary_evidence_ids=list(EVIDENCE_IDS),
                lineage_evidence_ids=[],
                source_receipt=None,
            ),
        )
    return ContentDeliveryClassificationLookup.model_construct(
        row_status=row_status,
        run=run,
    )


def reconciled_binding() -> ContentDeliveryIdentityBinding:
    command = ContentDeliveryIdentityCommand(
        canonical_path=CANONICAL_PATH,
        public_url=PUBLIC_URL,
        current_work_item_id=WORK_ITEM_ID,
        classification_run_id=RUN_ID,
        classification_run_digest=RUN_DIGEST,
        classification_decision_set_digest=DECISION_SET_DIGEST,
        classification_source_row_digest=ROW_DIGEST,
        inventory_evidence_ids=EVIDENCE_IDS,
        inventory_evidence_digest=inventory_evidence_digest(EVIDENCE_IDS),
        final_disposition="keep",
        recorded_by="wilku",
        recorded_at=datetime(2026, 9, 27, tzinfo=UTC),
    )
    return reconcile_content_delivery_identity(command, classification_lookup())
