from __future__ import annotations

import json

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

import apps.api.wilq_api.routers.content_regulatory_source_reviews as regulatory_router
import wilq.content.regulatory.source_fact_proposals as proposals_module
from apps.api.wilq_api.routers.content_regulatory_source_reviews import (
    register_content_regulatory_source_review_routes,
)
from wilq.codex.app_server import CodexAppServerTurnResult
from wilq.content.regulatory.policy import regulatory_source_candidates
from wilq.content.regulatory.source_fact_proposals import (
    ContentRegulatorySourceFactProposalReviewCommand,
    RegulatorySourceFactProposalStore,
    generate_source_fact_proposal,
    read_source_fact_proposal,
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


def _html_source(text: str) -> tuple[bytes, str]:
    return f"<html><main>{text}</main></html>".encode(), "text/html"


def _ready_output(candidate) -> dict[str, object]:
    return {
        "source_sufficiency": "sufficient",
        "insufficiency_reason": None,
        "proposed_fact": (
            "Oficjalne źródło opisuje obowiązek wyłącznie w zakresie wskazanym "
            "dla tego kandydata i wymaga dalszej oceny działalności firmy."
        ),
        "source_terms": ["Oficjalne", "źródło", "obowiązek"],
        "covered_requirement_ids": list(candidate.requirement_ids),
    }


def test_fact_proposal_is_exact_human_gated_and_never_persists_raw_source_body(tmp_path) -> None:
    candidate = regulatory_source_candidates()[0]
    proposal_store, snapshot_store, review_store, run_store = _stores(tmp_path)
    client = _Client(_ready_output(candidate))
    result = generate_source_fact_proposal(
        candidate_id=candidate.candidate_id,
        client=client,
        proposal_store=proposal_store,
        snapshot_store=snapshot_store,
        run_store=run_store,
        reader=lambda _: _html_source("TOP SECRET Oficjalne źródło opisuje obowiązek."),
    )

    assert result.status == "ready"
    assert result.proposal is not None
    proposal = result.proposal
    assert proposal.human_review_required is True
    assert proposal.covered_requirement_ids == sorted(candidate.requirement_ids)
    assert "TOP SECRET Oficjalne" not in proposal_store.path.read_text(errors="ignore")
    assert "TOP SECRET Oficjalne" in client.requests[0].untrusted_context
    application_context = json.loads(client.requests[0].application_context)
    assert application_context["requirements"] == [
        {
            "id": "bdo_definition",
            "label": "definicja systemu BDO",
            "reason": (
                "Treść musi poprawnie nazwać Bazę danych o produktach i opakowaniach oraz "
                "o gospodarce odpadami, Rejestr i moduły systemu."
            ),
            "document_assertions": [
                {
                    "id": "bdo_full_name",
                    "label": "pełna nazwa BDO",
                    "required_any_of": [
                        "Baza danych o produktach i opakowaniach oraz o gospodarce odpadami"
                    ],
                }
            ],
        }
    ]
    assert "TOP SECRET Oficjalne" not in client.requests[0].application_context

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
    restored = read_source_fact_proposal(
        candidate_id=candidate.candidate_id, proposal_store=proposal_store
    )
    assert restored.status == "ready"
    assert restored.proposal == proposal


def test_read_without_persisted_proposal_is_not_generated(tmp_path) -> None:
    proposal_store, _snapshot_store, _review_store, _run_store = _stores(tmp_path)
    result = read_source_fact_proposal(
        candidate_id=regulatory_source_candidates()[0].candidate_id,
        proposal_store=proposal_store,
    )
    assert result.status == "not_generated"
    assert result.proposal is None


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
                "source_terms": ["Oficjalny", "tekst", "źródła"],
                "covered_requirement_ids": ["other_requirement"],
            }
        ),
        proposal_store=proposal_store,
        snapshot_store=snapshot_store,
        run_store=run_store,
            reader=lambda _: _html_source("Oficjalny tekst źródła dla testu."),
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
                "source_terms": ["Oficjalny", "tekst", "źródła"],
                "covered_requirement_ids": list(candidate.requirement_ids),
            }
        ),
        proposal_store=proposal_store,
        snapshot_store=snapshot_store,
        run_store=run_store,
        reader=lambda _: _html_source("Oficjalny tekst źródła dla testu."),
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


def test_proposal_blocks_when_its_ephemeral_source_terms_are_not_in_exact_source(tmp_path) -> None:
    candidate = regulatory_source_candidates()[0]
    proposal_store, snapshot_store, _review_store, run_store = _stores(tmp_path)
    result = generate_source_fact_proposal(
        candidate_id=candidate.candidate_id,
        client=_Client(
            {
                "source_sufficiency": "sufficient",
                "insufficiency_reason": None,
                "proposed_fact": "Fact nie może przejść bez literalnego śladu w źródle urzędowym.",
                "source_terms": ["Nieistniejący", "fragment", "materiału"],
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
                "source_terms": ["Źródło", "pełnego", "zakresu"],
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
            "source_terms": ["Tekst", "oficjalnego", "PDF"],
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


def test_html_source_without_main_or_article_is_blocked_before_a_codex_run(tmp_path) -> None:
    candidate = regulatory_source_candidates()[0]
    proposal_store, snapshot_store, _review_store, run_store = _stores(tmp_path)
    client = _Client(_ready_output(candidate))

    result = generate_source_fact_proposal(
        candidate_id=candidate.candidate_id,
        client=client,
        proposal_store=proposal_store,
        snapshot_store=snapshot_store,
        run_store=run_store,
        reader=lambda _: (
            b"<html><nav>menu layout</nav><script>secret()</script><p>body</p></html>",
            "text/html",
        ),
    )

    assert result.status == "blocked"
    assert client.requests == []
    assert "secret" not in proposal_store.path.read_text(errors="ignore")


def test_same_source_digest_on_two_snapshots_persists_two_exact_proposals(tmp_path) -> None:
    from datetime import UTC, datetime, timedelta

    candidate = regulatory_source_candidates()[0]
    proposal_store, snapshot_store, review_store, run_store = _stores(tmp_path)
    body, content_type = _html_source("Oficjalne źródło opisuje obowiązek.")
    first_snapshot = snapshot_store.capture(
        candidate.candidate_id,
        reader=lambda _: (body, content_type),
        now=datetime(2026, 8, 2, 10, 0, tzinfo=UTC),
    )
    second_snapshot = snapshot_store.capture(
        candidate.candidate_id,
        reader=lambda _: (body, content_type),
        now=datetime(2026, 8, 2, 10, 0, tzinfo=UTC) + timedelta(minutes=1),
    )
    assert first_snapshot.content_digest == second_snapshot.content_digest
    assert first_snapshot.snapshot_id != second_snapshot.snapshot_id

    first = proposals_module._generate_from_snapshot(
        candidate=candidate,
        snapshot=first_snapshot,
        body=body,
        client=_Client(_ready_output(candidate)),
        proposal_store=proposal_store,
        run_store=run_store,
    )
    second = proposals_module._generate_from_snapshot(
        candidate=candidate,
        snapshot=second_snapshot,
        body=body,
        client=_Client(_ready_output(candidate)),
        proposal_store=proposal_store,
        run_store=run_store,
    )

    assert first.proposal is not None and second.proposal is not None
    assert first.proposal.proposal_id != second.proposal.proposal_id
    assert proposal_store.get(second.proposal.proposal_id) == second.proposal
    assert read_source_fact_proposal(
        candidate_id=candidate.candidate_id, proposal_store=proposal_store
    ).proposal == second.proposal
    review = review_source_fact_proposal(
        proposal_id=second.proposal.proposal_id,
        command=ContentRegulatorySourceFactProposalReviewCommand(
            expected_source_snapshot_id=second.proposal.source_snapshot_id,
            expected_source_snapshot_digest=second.proposal.source_snapshot_digest,
            decision="accepted",
            reviewer="Wilku",
        ),
        proposal_store=proposal_store,
        review_store=review_store,
    )
    assert review.source_snapshot_id == second_snapshot.snapshot_id


def test_review_rejects_a_proposal_superseded_by_a_newer_snapshot(tmp_path) -> None:
    from datetime import UTC, datetime, timedelta

    candidate = regulatory_source_candidates()[0]
    proposal_store, snapshot_store, review_store, run_store = _stores(tmp_path)
    first_body, content_type = _html_source("Oficjalne źródło opisuje obowiązek.")
    second_body, _ = _html_source("Oficjalne źródło opisuje nowy obowiązek.")
    first_snapshot = snapshot_store.capture(
        candidate.candidate_id,
        reader=lambda _: (first_body, content_type),
        now=datetime(2026, 8, 2, 10, 0, tzinfo=UTC),
    )
    first = proposals_module._generate_from_snapshot(
        candidate=candidate,
        snapshot=first_snapshot,
        body=first_body,
        client=_Client(_ready_output(candidate)),
        proposal_store=proposal_store,
        run_store=run_store,
    )
    second_snapshot = snapshot_store.capture(
        candidate.candidate_id,
        reader=lambda _: (second_body, content_type),
        now=datetime(2026, 8, 2, 10, 0, tzinfo=UTC) + timedelta(minutes=1),
    )
    proposals_module._generate_from_snapshot(
        candidate=candidate,
        snapshot=second_snapshot,
        body=second_body,
        client=_Client(_ready_output(candidate)),
        proposal_store=proposal_store,
        run_store=run_store,
    )

    assert first.proposal is not None
    with pytest.raises(ValueError, match="proposal is stale"):
        review_source_fact_proposal(
            proposal_id=first.proposal.proposal_id,
            command=ContentRegulatorySourceFactProposalReviewCommand(
                expected_source_snapshot_id=first.proposal.source_snapshot_id,
                expected_source_snapshot_digest=first.proposal.source_snapshot_digest,
                decision="accepted",
                reviewer="Wilku",
            ),
            proposal_store=proposal_store,
            review_store=review_store,
        )
    assert review_store.list_reviews() == []


def test_stale_proposal_review_route_returns_a_typed_conflict_without_a_review(
    tmp_path, monkeypatch
) -> None:
    from datetime import UTC, datetime, timedelta

    candidate = regulatory_source_candidates()[0]
    proposal_store, snapshot_store, review_store, run_store = _stores(tmp_path)
    body, content_type = _html_source("Oficjalne źródło opisuje obowiązek.")
    first_snapshot = snapshot_store.capture(
        candidate.candidate_id,
        reader=lambda _: (body, content_type),
        now=datetime(2026, 8, 2, 10, 0, tzinfo=UTC),
    )
    first = proposals_module._generate_from_snapshot(
        candidate=candidate,
        snapshot=first_snapshot,
        body=body,
        client=_Client(_ready_output(candidate)),
        proposal_store=proposal_store,
        run_store=run_store,
    )
    second_snapshot = snapshot_store.capture(
        candidate.candidate_id,
        reader=lambda _: (body, content_type),
        now=datetime(2026, 8, 2, 10, 0, tzinfo=UTC) + timedelta(minutes=1),
    )
    proposals_module._generate_from_snapshot(
        candidate=candidate,
        snapshot=second_snapshot,
        body=body,
        client=_Client(_ready_output(candidate)),
        proposal_store=proposal_store,
        run_store=run_store,
    )
    assert first.proposal is not None
    monkeypatch.setattr(
        regulatory_router, "regulatory_source_fact_proposal_store", lambda: proposal_store
    )
    monkeypatch.setattr(regulatory_router, "regulatory_source_review_store", lambda: review_store)
    app = FastAPI()
    router = APIRouter()
    register_content_regulatory_source_review_routes(router)
    app.include_router(router)

    response = TestClient(app).post(
        f"/api/content/regulatory-source-fact-proposals/{first.proposal.proposal_id}/review",
        json={
            "expected_source_snapshot_id": first.proposal.source_snapshot_id,
            "expected_source_snapshot_digest": first.proposal.source_snapshot_digest,
            "decision": "accepted",
            "reviewer": "Wilku",
        },
    )

    assert response.status_code == 409
    assert response.json()["code"] == "source_proposal_stale"
    assert review_store.list_reviews() == []


def test_canonical_read_blocks_a_proposal_when_its_candidate_profile_changes(tmp_path) -> None:
    candidate = regulatory_source_candidates()[0]
    proposal_store, snapshot_store, _review_store, run_store = _stores(tmp_path)
    result = generate_source_fact_proposal(
        candidate_id=candidate.candidate_id,
        client=_Client(_ready_output(candidate)),
        proposal_store=proposal_store,
        snapshot_store=snapshot_store,
        run_store=run_store,
        reader=lambda _: _html_source("Oficjalne źródło opisuje obowiązek."),
    )

    assert result.proposal is not None
    changed_candidate = candidate.model_copy(update={"profile_version": "profile-v2"})
    restored = read_source_fact_proposal(
        candidate_id=candidate.candidate_id,
        proposal_store=proposal_store,
        candidates=(changed_candidate,),
    )
    assert restored.status == "blocked"
    assert restored.proposal is None


def test_review_rejects_a_latest_proposal_when_candidate_requirements_expand(tmp_path) -> None:
    candidate = regulatory_source_candidates()[0]
    proposal_store, snapshot_store, review_store, run_store = _stores(tmp_path)
    result = generate_source_fact_proposal(
        candidate_id=candidate.candidate_id,
        client=_Client(_ready_output(candidate)),
        proposal_store=proposal_store,
        snapshot_store=snapshot_store,
        run_store=run_store,
        reader=lambda _: _html_source("Oficjalne źródło opisuje obowiązek."),
    )
    assert result.proposal is not None
    expanded_candidate = candidate.model_copy(
        update={"requirement_ids": [*candidate.requirement_ids, "new_requirement"]}
    )

    with pytest.raises(ValueError, match="proposal is stale"):
        review_source_fact_proposal(
            proposal_id=result.proposal.proposal_id,
            command=ContentRegulatorySourceFactProposalReviewCommand(
                expected_source_snapshot_id=result.proposal.source_snapshot_id,
                expected_source_snapshot_digest=result.proposal.source_snapshot_digest,
                decision="accepted",
                reviewer="Wilku",
            ),
            proposal_store=proposal_store,
            review_store=review_store,
            candidates=(expanded_candidate,),
        )
    assert review_store.list_reviews() == []


def test_canonical_read_blocks_when_a_newer_snapshot_has_no_proposal(tmp_path) -> None:
    from datetime import UTC, datetime, timedelta

    candidate = regulatory_source_candidates()[0]
    proposal_store, snapshot_store, _review_store, run_store = _stores(tmp_path)
    first = generate_source_fact_proposal(
        candidate_id=candidate.candidate_id,
        client=_Client(_ready_output(candidate)),
        proposal_store=proposal_store,
        snapshot_store=snapshot_store,
        run_store=run_store,
        reader=lambda _: _html_source("Oficjalne źródło opisuje obowiązek."),
    )
    assert first.proposal is not None
    snapshot_store.capture(
        candidate.candidate_id,
        reader=lambda _: _html_source("Oficjalne źródło ma nową treść obowiązku."),
        now=datetime.now(UTC) + timedelta(minutes=1),
    )

    restored = read_source_fact_proposal(
        candidate_id=candidate.candidate_id,
        proposal_store=proposal_store,
        snapshot_store=snapshot_store,
    )
    assert restored.status == "blocked"
    assert restored.proposal is None


def test_excerpt_matching_normalizes_pdf_line_break_hyphenation() -> None:
    assert proposals_module._normalize_source_text("sprawozda-\nnie roczne") == (
        proposals_module._normalize_source_text("sprawozdanie roczne")
    )


def test_source_term_coverage_allows_one_nonliteral_term_in_a_five_term_anchor() -> None:
    assert proposals_module._has_sufficient_source_term_coverage(
        ["pierwszy", "drugi", "trzeci", "czwarty", "modelowy"],
        "pierwszy drugi trzeci czwarty termin źródłowy",
    )
    assert not proposals_module._has_sufficient_source_term_coverage(
        ["pierwszy", "drugi", "trzeci", "czwarty", "modelowy"],
        "pierwszy drugi trzeci termin źródłowy",
    )


def test_long_source_context_keeps_candidate_relevant_fragments() -> None:
    candidate = regulatory_source_candidates()[0]
    source = ("szum layoutu " * 8_000) + (
        "Podmioty zobowiązane do rejestracji w BDO prowadzą ewidencję odpadów. " * 20
    )

    selected = proposals_module._relevant_source_text(candidate, source)

    assert "Podmioty zobowiązane do rejestracji" in selected
    assert len(selected) < len(source)


def test_long_source_context_keeps_profile_assertion_terms() -> None:
    candidate = next(
        item
        for item in regulatory_source_candidates()
        if item.candidate_id == "bdo_reporting_recipient_2026_08_02_r3"
    )
    source = (
        "Sprawozdanie o produktach opisuje zakres dokumentu. " * 3_000
        + "15 marca za poprzedni rok właściwemu marszałkowi województwa."
    )

    selected = proposals_module._relevant_source_text(candidate, source)

    assert "15 marca" in selected
    assert "marszałkowi województwa" in selected
    assert len(selected) < len(source)
