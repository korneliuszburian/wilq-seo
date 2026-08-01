from __future__ import annotations

import json

import pytest

import wilq.content.regulatory.source_fact_proposals as proposals_module
from wilq.codex.app_server import CodexAppServerTurnResult
from wilq.content.regulatory.policy import regulatory_source_candidates
from wilq.content.regulatory.source_fact_proposals import (
    ContentRegulatorySourceFactProposalReviewCommand,
    RegulatorySourceFactProposalStore,
    generate_source_fact_proposal,
    review_source_fact_proposal,
)
from wilq.content.regulatory.source_reviews import RegulatorySourceReviewStore
from wilq.content.regulatory.source_snapshots import RegulatorySourceSnapshotStore
from wilq.storage.local_state import LocalStateStore


class _Client:
    def __init__(self, output: object) -> None:
        self.output = output
        self.requests = []

    def run_structured_turn(self, request):
        self.requests.append(request)
        return CodexAppServerTurnResult(status="completed", output_text=json.dumps(self.output))


def _stores(tmp_path):
    path = tmp_path / "wilq.sqlite3"
    return (
        RegulatorySourceFactProposalStore(path),
        RegulatorySourceSnapshotStore(path),
        RegulatorySourceReviewStore(path),
        LocalStateStore(path),
    )


def test_fact_proposal_is_exact_human_gated_and_never_persists_raw_source_body(tmp_path) -> None:
    candidate = regulatory_source_candidates()[0]
    proposal_store, snapshot_store, review_store, run_store = _stores(tmp_path)
    client = _Client(
        {
            "source_sufficiency": "sufficient",
            "insufficiency_reason": None,
            "proposed_fact": (
                "Oficjalne źródło opisuje obowiązek wyłącznie w zakresie wskazanym "
                "dla tego kandydata i wymaga dalszej oceny działalności firmy."
            ),
            "source_excerpt": "TOP_SECRET_OFFICIAL_SOURCE_BODY",
            "covered_requirement_ids": list(candidate.requirement_ids),
        }
    )
    result = generate_source_fact_proposal(
        candidate_id=candidate.candidate_id,
        client=client,
        proposal_store=proposal_store,
        snapshot_store=snapshot_store,
        run_store=run_store,
        reader=lambda _: (b"TOP_SECRET_OFFICIAL_SOURCE_BODY", "text/html"),
    )

    assert result.status == "ready"
    assert result.proposal is not None
    proposal = result.proposal
    assert proposal.human_review_required is True
    assert proposal.covered_requirement_ids == sorted(candidate.requirement_ids)
    assert "TOP_SECRET_OFFICIAL_SOURCE_BODY" not in proposal_store.path.read_text(errors="ignore")
    assert "TOP_SECRET_OFFICIAL_SOURCE_BODY" in client.requests[0].untrusted_context

    review = review_source_fact_proposal(
        proposal_id=proposal.proposal_id,
        command=ContentRegulatorySourceFactProposalReviewCommand(
            expected_source_snapshot_id=proposal.source_snapshot_id,
            expected_source_snapshot_digest=proposal.source_snapshot_digest,
            decision="accepted",
            reviewer="Wilku",
        ),
        proposal_store=proposal_store,
        review_store=review_store,
    )
    assert review.decision == "accepted"
    assert review.reviewed_fact == proposal.proposed_fact


def test_invalid_requirement_binding_blocks_before_proposal_or_human_review(tmp_path) -> None:
    candidate = regulatory_source_candidates()[0]
    proposal_store, snapshot_store, review_store, run_store = _stores(tmp_path)
    result = generate_source_fact_proposal(
        candidate_id=candidate.candidate_id,
        client=_Client(
            {
                "source_sufficiency": "sufficient",
                "insufficiency_reason": None,
                "proposed_fact": "To jest pozornie poprawny fact, ale odnosi się do obcego wymogu.",
                "source_excerpt": "Oficjalny tekst źródła dla testu.",
                "covered_requirement_ids": ["other_requirement"],
            }
        ),
        proposal_store=proposal_store,
        snapshot_store=snapshot_store,
        run_store=run_store,
        reader=lambda _: ("Oficjalny tekst źródła dla testu.".encode(), "text/html"),
    )

    assert result.status == "blocked"
    assert proposal_store.latest(candidate.candidate_id) is None
    assert review_store.list_reviews() == []


def test_proposal_review_rejects_stale_snapshot_without_human_review(tmp_path) -> None:
    candidate = regulatory_source_candidates()[0]
    proposal_store, snapshot_store, review_store, run_store = _stores(tmp_path)
    result = generate_source_fact_proposal(
        candidate_id=candidate.candidate_id,
        client=_Client(
            {
                "source_sufficiency": "sufficient",
                "insufficiency_reason": None,
                "proposed_fact": (
                    "Dokładny fact z oficjalnego źródła wymaga sprawdzenia przez człowieka."
                ),
                "source_excerpt": "Oficjalny tekst źródła dla testu.",
                "covered_requirement_ids": list(candidate.requirement_ids),
            }
        ),
        proposal_store=proposal_store,
        snapshot_store=snapshot_store,
        run_store=run_store,
        reader=lambda _: ("Oficjalny tekst źródła dla testu.".encode(), "text/html"),
    )
    assert result.proposal is not None
    with pytest.raises(ValueError, match="snapshot changed"):
        review_source_fact_proposal(
            proposal_id=result.proposal.proposal_id,
            command=ContentRegulatorySourceFactProposalReviewCommand(
                expected_source_snapshot_id=result.proposal.source_snapshot_id,
                expected_source_snapshot_digest="a" * 64,
                decision="accepted",
                reviewer="Wilku",
            ),
            proposal_store=proposal_store,
            review_store=review_store,
        )
    assert review_store.list_reviews() == []


def test_proposal_blocks_when_its_ephemeral_excerpt_is_not_in_exact_source(tmp_path) -> None:
    candidate = regulatory_source_candidates()[0]
    proposal_store, snapshot_store, _review_store, run_store = _stores(tmp_path)
    result = generate_source_fact_proposal(
        candidate_id=candidate.candidate_id,
        client=_Client(
            {
                "source_sufficiency": "sufficient",
                "insufficiency_reason": None,
                "proposed_fact": "Fact nie może przejść bez literalnego śladu w źródle urzędowym.",
                "source_excerpt": "Nieistniejący fragment oficjalnego materiału.",
                "covered_requirement_ids": list(candidate.requirement_ids),
            }
        ),
        proposal_store=proposal_store,
        snapshot_store=snapshot_store,
        run_store=run_store,
        reader=lambda _: ("Oficjalny materiał zawiera inny tekst.".encode(), "text/html"),
    )

    assert result.status == "blocked"
    assert proposal_store.latest(candidate.candidate_id) is None


def test_insufficient_source_is_a_typed_blocker_not_a_weak_proposal(tmp_path) -> None:
    candidate = regulatory_source_candidates()[0]
    proposal_store, snapshot_store, _review_store, run_store = _stores(tmp_path)
    result = generate_source_fact_proposal(
        candidate_id=candidate.candidate_id,
        client=_Client(
            {
                "source_sufficiency": "insufficient",
                "insufficiency_reason": "Źródło nie zawiera pełnego zakresu obowiązku.",
                "proposed_fact": (
                    "Źródło nie daje pełnej podstawy do tworzenia factu regulacyjnego."
                ),
                "source_excerpt": "Źródło nie zawiera pełnego zakresu obowiązku.",
                "covered_requirement_ids": list(candidate.requirement_ids),
            }
        ),
        proposal_store=proposal_store,
        snapshot_store=snapshot_store,
        run_store=run_store,
        reader=lambda _: ("Źródło nie zawiera pełnego zakresu obowiązku.".encode(), "text/html"),
    )

    assert result.status == "blocked"
    assert result.proposal is None
    assert proposal_store.latest(candidate.candidate_id) is None


def test_pdf_source_is_extracted_transiently_before_structured_turn(tmp_path, monkeypatch) -> None:
    candidate = regulatory_source_candidates()[0]
    proposal_store, snapshot_store, _review_store, run_store = _stores(tmp_path)
    client = _Client(
        {
            "source_sufficiency": "sufficient",
            "insufficiency_reason": None,
            "proposed_fact": "Wyekstrahowany tekst urzędowy wymaga nadal decyzji człowieka.",
            "source_excerpt": "Tekst z oficjalnego PDF-a.",
            "covered_requirement_ids": list(candidate.requirement_ids),
        }
    )

    class _PdfResult:
        returncode = 0
        stdout = b"Tekst z oficjalnego PDF-a."

    monkeypatch.setattr(proposals_module.subprocess, "run", lambda *args, **kwargs: _PdfResult())
    result = generate_source_fact_proposal(
        candidate_id=candidate.candidate_id,
        client=client,
        proposal_store=proposal_store,
        snapshot_store=snapshot_store,
        run_store=run_store,
        reader=lambda _: (b"%PDF-raw-official-body", "application/pdf"),
    )

    assert result.status == "ready"
    assert "Tekst z oficjalnego PDF-a." in client.requests[0].untrusted_context
    assert "%PDF-raw-official-body" not in client.requests[0].untrusted_context


def test_html_proposal_context_uses_main_content_not_layout_or_scripts() -> None:
    text = proposals_module._source_text_for_proposal(
        proposals_module.ContentRegulatorySourceSnapshot(
            snapshot_id="snapshot",
            candidate_id="candidate",
            profile_id="profile",
            profile_version="version",
            source_url="https://example.gov.pl/source",
            content_digest="a" * 64,
            content_type="text/html",
            byte_length=180,
            observed_at="2026-08-01T12:00:00Z",
        ),
        (
            "<html><nav>menu layout</nav><main><h1>Obowiązek BDO</h1>"
            "<p>Literalny fakt z materiału urzędowego.</p><script>secret()</script>"
            "</main></html>"
        ).encode(),
    )

    assert "Obowiązek BDO" in text
    assert "Literalny fakt" in text
    assert "menu layout" not in text
    assert "secret" not in text
