"""Public read-only current-page identity from fresh exact material evidence."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Query

from apps.api.wilq_api.routers import content_current_page_evidence
from wilq.content.workflow.current_page_evidence import CurrentPageEvidenceResponse
from wilq.content.workflow.current_page_identity_v3 import (
    CurrentPageIdentityV3Response,
    resolve_current_page_identity_v3,
)

EvidenceLoader = Callable[[str], CurrentPageEvidenceResponse]


def register_content_current_page_identity_v3_route(
    router: APIRouter,
    *,
    evidence_loader: EvidenceLoader | None = None,
) -> None:
    load_evidence = evidence_loader or (
        lambda work_item_id: content_current_page_evidence.read_current_page_evidence(
            work_item_id=work_item_id
        )
    )

    @router.get(
        "/api/content/work-items/{work_item_id}/current-identity-v3",
        response_model=CurrentPageIdentityV3Response,
    )
    def read_current_page_identity_v3(
        work_item_id: str,
        expected_identity_digest: str | None = Query(
            default=None, pattern=r"^[0-9a-f]{64}$"
        ),
        expected_evidence_digest: str | None = Query(
            default=None, pattern=r"^[0-9a-f]{64}$"
        ),
    ) -> CurrentPageIdentityV3Response:
        return resolve_current_page_identity_v3(
            work_item_id,
            load_evidence(work_item_id),
            expected_identity_digest=expected_identity_digest,
            expected_evidence_digest=expected_evidence_digest,
        )
