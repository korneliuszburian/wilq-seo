from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers import social as social_router
from wilq.content.workflow.revisions import ContentDraftRevision
from wilq.content.workflow.store import ContentWorkflowStore
from wilq.social.history import (
    audit_social_history_metadata_payload,
    build_social_history_inventory,
)
from wilq.social.reuse import (
    SocialReuseProposal,
    SocialReuseProposalRequest,
    SocialReuseReview,
    build_social_reuse_proposal,
)


def test_social_reuse_rejects_stale_revision_before_history_or_persistence(
    monkeypatch,
) -> None:
    revision = _revision()
    store = _FakeStore(
        revision,
        status="approved",
    )
    monkeypatch.setattr(social_router, "content_workflow_store", lambda: store)
    client = TestClient(app)

    response = client.post(
        "/api/social/reuse-proposals",
        json={
            "work_item_id": revision.work_item_id,
            "expected_revision_id": revision.revision_id,
            "expected_revision_digest": "0" * 64,
            "platform": "linkedin",
            "audience": "przedsiębiorcy",
            "angle": "konkretny pierwszy krok",
            "body": "Sprawdź pierwszy krok.",
            "claim_ids": ["claim_1"],
            "measurement_hypothesis": "Obserwujemy wejścia na stronę.",
        },
    )

    assert response.status_code == 409
    assert response.json()["status"] == "stale"
    assert response.json()["blocker"] == "stale_revision"
    assert store.saved is None


def test_social_reuse_stays_blocked_until_history_is_review_ready(monkeypatch) -> None:
    revision = _revision()
    store = _FakeStore(revision, status="approved")
    monkeypatch.setattr(social_router, "content_workflow_store", lambda: store)
    monkeypatch.setattr(
        social_router,
        "build_social_history_inventory_from_env",
        lambda *_args: build_social_history_inventory({}, {}),
    )
    client = TestClient(app)

    response = client.post(
        "/api/social/reuse-proposals",
        json={
            "work_item_id": revision.work_item_id,
            "expected_revision_id": revision.revision_id,
            "expected_revision_digest": revision.content_digest,
            "platform": "facebook",
            "audience": "przedsiębiorcy",
            "angle": "konkretny pierwszy krok",
            "body": "Sprawdź pierwszy krok.",
            "claim_ids": ["claim_1"],
            "measurement_hypothesis": "Obserwujemy wejścia na stronę.",
        },
    )

    assert response.status_code == 409
    assert response.json()["status"] == "blocked"
    assert response.json()["blocker"] == "social_history_not_reviewed"
    assert store.saved is None


def test_social_reuse_store_is_idempotent_for_exact_revision(tmp_path) -> None:
    revision = _revision()
    inventory = build_social_history_inventory(
        {},
        {},
        audit_social_history_metadata_payload(
            {
                "items": [
                    {"channel": "linkedin", **_history_fields("linkedin")},
                    {"channel": "facebook", **_history_fields("facebook")},
                ]
            }
        ),
        metadata_source_configured=True,
    )
    proposal = build_social_reuse_proposal(
        SocialReuseProposalRequest(
            work_item_id=revision.work_item_id,
            expected_revision_id=revision.revision_id,
            expected_revision_digest=revision.content_digest,
            platform="linkedin",
            audience="przedsiębiorcy",
            angle="konkretny pierwszy krok",
            body="Sprawdź pierwszy krok.",
            claim_ids=["claim_1"],
            measurement_hypothesis="Obserwujemy wejścia na stronę.",
        ),
        revision,
        inventory,
        now=datetime(2026, 7, 18, tzinfo=UTC),
    )
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")

    first = store.save_social_reuse_proposal(proposal)
    second = store.save_social_reuse_proposal(proposal.model_copy(update={"body": "Inny tekst."}))

    assert first.proposal_digest == second.proposal_digest
    assert second.body == first.body
    assert store.get_social_reuse_proposal(proposal.proposal_id) == first


def test_social_reuse_read_becomes_stale_when_history_digest_changes(monkeypatch) -> None:
    revision = _revision()
    inventory = build_social_history_inventory(
        {},
        {},
        audit_social_history_metadata_payload(
            {
                "items": [
                    {"channel": "linkedin", **_history_fields("linkedin")},
                    {"channel": "facebook", **_history_fields("facebook")},
                ]
            }
        ),
    )
    proposal = build_social_reuse_proposal(
        SocialReuseProposalRequest(
            work_item_id=revision.work_item_id,
            expected_revision_id=revision.revision_id,
            expected_revision_digest=revision.content_digest,
            platform="linkedin",
            audience="przedsiębiorcy",
            angle="konkretny pierwszy krok",
            body="Sprawdź pierwszy krok.",
            claim_ids=["claim_1"],
            measurement_hypothesis="Obserwujemy wejścia na stronę.",
        ),
        revision,
        inventory,
        now=datetime(2026, 7, 18, tzinfo=UTC),
    )
    store = _FakeStore(revision, status="approved")
    store.saved = proposal
    monkeypatch.setattr(social_router, "content_workflow_store", lambda: store)
    monkeypatch.setattr(
        social_router,
        "build_social_history_inventory_from_env",
        lambda *_args: build_social_history_inventory({}, {}),
    )
    response = TestClient(app).get(
        f"/api/social/reuse-proposals/{proposal.proposal_id}"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "stale"
    assert response.json()["blocker"] == "social_history_changed"


def test_social_reuse_review_records_human_decision_and_is_idempotent(monkeypatch) -> None:
    revision = _revision()
    inventory = build_social_history_inventory(
        {},
        {},
        audit_social_history_metadata_payload(
            {
                "items": [
                    {"channel": "linkedin", **_history_fields("linkedin")},
                    {"channel": "facebook", **_history_fields("facebook")},
                ]
            }
        ),
        metadata_source_configured=True,
    )
    proposal = build_social_reuse_proposal(
        SocialReuseProposalRequest(
            work_item_id=revision.work_item_id,
            expected_revision_id=revision.revision_id,
            expected_revision_digest=revision.content_digest,
            platform="linkedin",
            audience="przedsiębiorcy",
            angle="konkretny pierwszy krok",
            body="Sprawdź pierwszy krok.",
            claim_ids=["claim_1"],
            measurement_hypothesis="Obserwujemy wejścia na stronę.",
        ),
        revision,
        inventory,
        now=datetime(2026, 7, 18, tzinfo=UTC),
    )
    store = _FakeStore(revision, status="approved")
    store.saved = proposal
    monkeypatch.setattr(social_router, "content_workflow_store", lambda: store)
    monkeypatch.setattr(
        social_router,
        "build_social_history_inventory_from_env",
        lambda *_args: inventory,
    )
    payload = {
        "expected_proposal_digest": proposal.proposal_digest,
        "reviewed_by": "wilku",
        "decision": "approved",
        "checked_items": ["claimy", "CTA"],
        "evidence_ids": ["ev_source_1"],
    }

    first = TestClient(app).post(
        f"/api/social/reuse-proposals/{proposal.proposal_id}/review",
        json=payload,
    )
    repeated = TestClient(app).post(
        f"/api/social/reuse-proposals/{proposal.proposal_id}/review",
        json=payload,
    )

    assert first.status_code == 200, first.json()
    assert first.json()["status"] == "recorded"
    assert first.json()["review"]["decision"] == "approved"
    assert repeated.status_code == 200
    assert repeated.json()["status"] == "idempotent"
    assert repeated.json()["review"]["review_id"] == first.json()["review"]["review_id"]


def _revision() -> ContentDraftRevision:
    return ContentDraftRevision.model_validate(
        {
            "schema_version": "wilq_content_draft_revision_v1",
            "revision_id": "revision_social_1",
            "work_item_id": "work_social_1",
            "revision_number": 1,
            "content_digest": "a" * 64,
            "draft_package_id": "package_social_1",
            "draft_package_digest": "b" * 64,
            "final_canonical_url": "https://www.ekologus.pl/test/",
            "title": "Testowa treść",
            "sections": [
                {
                    "heading": "Pierwszy krok",
                    "body_markdown": "Treść oparta na źródle.",
                    "evidence_ids": ["ev_source_1"],
                    "claim_ids": ["claim_1"],
                }
            ],
            "created_by": "test",
            "created_at": datetime.now(UTC),
        }
    )


def _history_fields(channel: str) -> dict[str, str]:
    return {
        "published_at": "2026-07-01",
        "topic": "bezpieczny temat",
        "service": "doradztwo",
        "claim": "claim z review",
        "cta": "Sprawdź szczegóły",
        "format": "post",
        "post_url_or_id": f"{channel}-1",
        "source_evidence_id": f"ev_{channel}_history",
    }


class _FakeStore:
    def __init__(self, revision: ContentDraftRevision, *, status: str) -> None:
        self.revision = revision
        self.status = status
        self.saved: SocialReuseProposal | None = None
        self.saved_review: SocialReuseReview | None = None

    def load_draft_revision_state(self, work_item_id: str):
        return SimpleNamespace(
            status=self.status,
            latest_revision=self.revision
            if work_item_id == self.revision.work_item_id
            else None,
        )

    def save_social_reuse_proposal(self, proposal: SocialReuseProposal) -> SocialReuseProposal:
        self.saved = proposal
        return proposal

    def get_social_reuse_proposal(self, proposal_id: str):
        return self.saved if self.saved and self.saved.proposal_id == proposal_id else None

    def latest_social_reuse_review(self, proposal_id: str):
        if self.saved_review and self.saved_review.proposal_id == proposal_id:
            return self.saved_review
        return None

    def save_social_reuse_review(self, review: SocialReuseReview) -> SocialReuseReview:
        self.saved_review = review
        return review
