from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers import content_revision_html_package
from wilq.content.handoff.html_package import build_content_revision_html_package
from wilq.content.workflow.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionPageAssets,
    ContentDraftRevisionReview,
    ContentDraftRevisionSection,
)


def test_html_package_carries_the_exact_approved_revision_and_its_lineage() -> None:
    revision = _approved_revision()
    package = build_content_revision_html_package(revision, _exact_review(revision))

    assert package.manifest.model_dump() == {
        "work_item_id": revision.work_item_id,
        "revision_id": revision.revision_id,
        "content_digest": revision.content_digest,
        "final_canonical_url": revision.final_canonical_url,
        "evidence_ids": ["ev_section"],
        "source_material_ids": ["material_bdo"],
        "knowledge_card_ids": ["knowledge_bdo"],
        "section_count": 1,
    }
    assert package.file_name == "wilq-exact-revision-content_revision_approved.html"
    assert package.html_document.startswith("<!doctype html>")
    assert revision.content_digest in package.html_document
    assert "<h1>BDO</h1>" in package.html_document
    assert "Treść sekcji." in package.html_document
    assert "Nie jest gotowym układem ani zapisem WordPress." in package.html_document


def test_html_package_rejects_a_review_for_a_different_exact_revision() -> None:
    revision = _approved_revision()
    review = _exact_review(revision).model_copy(update={"revision_digest": "b" * 64})

    with pytest.raises(ValueError, match="exact revision and digest"):
        build_content_revision_html_package(revision, review)


def test_html_package_endpoint_keeps_a_historical_approved_revision_exact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    historical = _approved_revision()
    current = historical.model_copy(
        update={
            "revision_id": "content_revision_current",
            "revision_number": 2,
            "content_digest": "c" * 64,
            "title": "BDO — nowsza wersja",
        }
    )
    reviews = {
        historical.revision_id: _exact_review(historical),
        current.revision_id: _exact_review(current),
    }

    class RevisionStore:
        def list_draft_revisions(self, work_item_id: str) -> list[ContentDraftRevision]:
            assert work_item_id == historical.work_item_id
            return [historical, current]

        def load_draft_revision_review(
            self,
            *,
            work_item_id: str,
            revision_id: str,
        ) -> ContentDraftRevisionReview | None:
            assert work_item_id == historical.work_item_id
            return reviews.get(revision_id)

    monkeypatch.setattr(
        content_revision_html_package,
        "content_workflow_store",
        lambda: cast(object, RevisionStore()),
    )
    app = FastAPI()
    router = APIRouter()
    content_revision_html_package.register_content_revision_html_package_route(router)
    app.include_router(router)

    response = TestClient(app).get(
        f"/api/content/work-items/{historical.work_item_id}/draft-revisions/"
        f"{historical.revision_id}/html-package"
    )

    assert response.status_code == 200
    package = response.json()
    assert package["manifest"]["revision_id"] == historical.revision_id
    assert package["manifest"]["content_digest"] == historical.content_digest
    assert historical.content_digest in package["html_document"]
    assert current.content_digest not in package["html_document"]


def _approved_revision() -> ContentDraftRevision:
    return ContentDraftRevision(
        revision_id="content_revision_approved",
        work_item_id="content_work_item_bdo",
        revision_number=1,
        content_digest="a" * 64,
        draft_package_id="draft_package_bdo",
        draft_package_digest="b" * 64,
        final_canonical_url="https://www.ekologus.pl/bdo/",
        title="BDO",
        page_assets=ContentDraftRevisionPageAssets(
            wordpress_title="BDO",
            meta_title="BDO",
            meta_description="Opis BDO",
            h1="BDO",
            lead="Wprowadzenie."
        ),
        sections=[
            ContentDraftRevisionSection(
                section_id="section_1",
                heading="Sekcja",
                body_markdown="Treść sekcji.",
                content_html="<p>Treść sekcji.</p>",
                evidence_ids=["ev_section"],
                source_material_ids=["material_bdo"],
                knowledge_card_ids=["knowledge_bdo"],
            )
        ],
        created_by="operator_local_dashboard",
        created_at=datetime(2026, 7, 23, tzinfo=UTC),
    )


def _exact_review(revision: ContentDraftRevision) -> ContentDraftRevisionReview:
    return ContentDraftRevisionReview(
        decision_id="content_revision_review_approved",
        decision_number=1,
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revision_digest=revision.content_digest,
        decision="approved",
        reviewed_by="operator_local_dashboard",
        checked_items=["Przeczytano dokładną treść tej wersji."],
        evidence_ids=["ev_section"],
        created_at=datetime(2026, 7, 23, tzinfo=UTC),
    )
