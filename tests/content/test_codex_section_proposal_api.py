from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers import content_codex_proposal
from tests.content.test_content_revision_workspace_api import (
    _review_path,
    _review_payload,
    _revision_ready_snapshot,
    _save_path,
    _save_payload,
    _selected_snapshot,
    _structured_generation_from_snapshot,
    _structured_output_from_contract,
)
from wilq.codex.app_server import (
    CodexAppServerStructuredTurnRequest,
    CodexAppServerTurnResult,
)
from wilq.content.drafts.codex_section_proposal_schema import proposal_output_schema
from wilq.storage.local_state import local_state_store


@dataclass(frozen=True)
class _ProposalCase:
    client: TestClient
    work_item_id: str
    base_revision: dict[str, Any]
    contract: dict[str, Any]
    selected_heading: str
    valid_output: dict[str, Any]
    proposal_path: str
    proposal_payload: dict[str, Any]
    codex_client: _FakeCodexAppServerClient


class _FakeCodexAppServerClient:
    def __init__(self, outputs: list[dict[str, Any]]) -> None:
        self.outputs = list(outputs)
        self.requests: list[CodexAppServerStructuredTurnRequest] = []

    def run_structured_turn(
        self,
        request: CodexAppServerStructuredTurnRequest,
    ) -> CodexAppServerTurnResult:
        self.requests.append(request)
        return CodexAppServerTurnResult(
            status="completed",
            output_text=json.dumps(self.outputs.pop(0), ensure_ascii=False),
            thread_id=f"thread_{len(self.requests)}",
            turn_id=f"turn_{len(self.requests)}",
            event_methods=("turn/completed",),
            item_types=("agentMessage",),
        )


def test_section_proposal_schema_bounds_selected_section_count() -> None:
    contract = SimpleNamespace(
        output_schema={
            "type": "object",
            "properties": {
                "title": {},
                "h1": {},
                "sections": {"type": "array"},
                "source_facts_used": {},
                "claims_needing_review": {},
                "forbidden_claims_avoided": {},
            },
            "$defs": {
                "StructuredDraftOutputSection": {
                    "properties": {
                        "heading": {},
                        "evidence_ids": {},
                        "claims_used": {},
                    }
                }
            },
        },
        model_input=SimpleNamespace(
            claims_allowed=[],
            claims_removed_or_blocked=[],
        ),
    )
    base_revision = SimpleNamespace(
        title="Bazowy tytuł",
        sections=[SimpleNamespace(heading="Sekcja A", evidence_ids=["ev_a"])],
    )

    schema = proposal_output_schema(
        contract,
        base_revision=base_revision,
        selected_headings=["Sekcja A"],
    )

    assert schema["properties"]["sections"]["minItems"] == 1
    assert schema["properties"]["sections"]["maxItems"] == 1
    evidence_schema = schema["$defs"]["StructuredDraftOutputSection"]["properties"][
        "evidence_ids"
    ]
    assert evidence_schema["minItems"] == 1
    assert evidence_schema["maxItems"] == 1
    assert evidence_schema["uniqueItems"] is True


def test_codex_section_proposal_is_grounded_and_remains_unreviewed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    case = _proposal_case(monkeypatch, tmp_path)

    unknown = case.client.post(case.proposal_path, json=case.proposal_payload)
    _assert_claim_contract_blocked(
        case,
        unknown.json(),
        source_code="unknown_claim_reference",
    )
    _assert_api_owned_turn(case, case.codex_client.requests[0])

    blocked = case.client.post(case.proposal_path, json=case.proposal_payload)
    _assert_claim_contract_blocked(
        case,
        blocked.json(),
        source_code="known_blocked_claim_text_present",
    )

    high_risk = case.client.post(case.proposal_path, json=case.proposal_payload)
    _assert_claim_contract_blocked(
        case,
        high_risk.json(),
        source_code="undeclared_high_risk_claim_language",
    )

    created = case.client.post(case.proposal_path, json=case.proposal_payload)
    assert created.status_code == 200
    _assert_exact_unreviewed_child(case, created.json())


def _proposal_case(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> _ProposalCase:
    client, work_item_id, snapshot = _revision_ready_snapshot(monkeypatch, tmp_path)
    base_revision = client.post(_save_path(work_item_id), json=_save_payload(snapshot)).json()[
        "revision"
    ]
    reviewed = client.post(
        _review_path(work_item_id, base_revision["revision_id"]),
        json=_review_payload(base_revision, "needs_changes"),
    )
    assert reviewed.status_code == 200
    contract = _structured_generation_from_snapshot(
        client,
        _selected_snapshot(client, work_item_id),
    )["contract"]
    selected_heading = base_revision["sections"][0]["heading"]
    valid_output = _structured_output_from_contract(contract)
    assert valid_output["sections"][0]["heading"] == selected_heading
    unknown_reference_output = deepcopy(valid_output)
    unknown_reference_output["sections"][0]["claims_used"].append(
        "Nieznane twierdzenie spoza Claim Ledger"
    )
    blocked_output = deepcopy(valid_output)
    blocked_output["sections"][0]["body_markdown"] += (
        " " + contract["model_input"]["claims_removed_or_blocked"][0]
    )
    high_risk_output = deepcopy(valid_output)
    high_risk_output["sections"][0]["body_markdown"] += (
        " Ekologus gwarantuje stuprocentową skuteczność i pełną zgodność prawną."
    )
    codex_client = _FakeCodexAppServerClient(
        [unknown_reference_output, blocked_output, high_risk_output, valid_output]
    )
    monkeypatch.setattr(
        content_codex_proposal,
        "content_codex_app_server_client",
        lambda: codex_client,
    )
    return _ProposalCase(
        client=client,
        work_item_id=work_item_id,
        base_revision=base_revision,
        contract=contract,
        selected_heading=selected_heading,
        valid_output=valid_output,
        proposal_path=_proposal_path(work_item_id, base_revision["revision_id"]),
        proposal_payload={
            "expected_base_digest": base_revision["content_digest"],
            "selected_section_headings": [selected_heading],
            "requested_by": "wilku",
        },
        codex_client=codex_client,
    )


def _assert_claim_contract_blocked(
    case: _ProposalCase,
    body: dict[str, Any],
    *,
    source_code: str,
) -> None:
    assert body["status"] == "blocked"
    assert body["revision"] is None
    assert body["blockers"][0]["code"] == "proposal_contract_blocked"
    assert source_code in body["blockers"][0]["source_codes"]
    assert body["semantic_review_required"] is True
    assert body["publish_ready"] is False
    workspace = _selected_snapshot(case.client, case.work_item_id)["revision_workspace"]
    assert workspace["revision_count"] == 1
    assert workspace["latest_revision"]["revision_id"] == case.base_revision["revision_id"]


def _assert_api_owned_turn(
    case: _ProposalCase,
    request: CodexAppServerStructuredTurnRequest,
) -> None:
    application_context = json.loads(request.application_context)
    untrusted_context = json.loads(request.untrusted_context)
    generation_input = untrusted_context["generation_input"]
    assert application_context["base_revision_id"] == case.base_revision["revision_id"]
    assert "selected_section_headings" not in application_context
    assert case.selected_heading not in request.application_context
    assert untrusted_context["editable_section_headings"] == [case.selected_heading]
    assert untrusted_context["base_revision"]["sections"] == case.base_revision["sections"]
    assert untrusted_context["latest_review"]["decision"] == "needs_changes"
    assert generation_input == case.contract["model_input"]
    for field in (
        generation_input["title"],
        generation_input["target_reader"],
        generation_input["buyer_problem"],
        generation_input["sales_brief_signal_quality"]["status_label"],
        case.selected_heading,
    ):
        assert field not in request.instruction
    assert case.contract["user_instruction"] not in request.instruction
    assert {
        "source_facts",
        "knowledge_constraints",
        "sales_brief_signal_quality",
        "claim_markers",
        "removed_or_blocked_claim_markers",
    } <= generation_input.keys()
    _assert_literal_schema(case, cast(dict[str, Any], request.output_schema))


def _assert_literal_schema(
    case: _ProposalCase,
    output_schema: dict[str, Any],
) -> None:
    properties = output_schema["properties"]
    section_properties = output_schema["$defs"]["StructuredDraftOutputSection"]["properties"]
    assert properties["sections"]["minItems"] == 1
    assert properties["sections"]["maxItems"] == 1
    assert properties["title"]["const"] == case.base_revision["title"]
    assert properties["claims_needing_review"]["items"]["enum"] == ["__WILQ_EMPTY_ARRAY_ONLY__"]
    assert section_properties["heading"]["enum"] == [case.selected_heading]
    assert section_properties["evidence_ids"]["minItems"] == len(
        case.base_revision["sections"][0]["evidence_ids"]
    )
    assert section_properties["evidence_ids"]["maxItems"] == len(
        case.base_revision["sections"][0]["evidence_ids"]
    )
    assert (
        section_properties["evidence_ids"]["items"]["enum"]
        == (case.base_revision["sections"][0]["evidence_ids"])
    )
    assert (
        section_properties["claims_used"].get("items", {}).get("enum", [])
        == (case.contract["model_input"]["claims_allowed"])
    )


def _assert_exact_unreviewed_child(
    case: _ProposalCase,
    body: dict[str, Any],
) -> None:
    assert body["status"] == "created", body["blockers"]
    assert body["runtime"]["external_call_attempted"] is False
    assert body["quality_review"]["verdict"] != "blocked"
    assert body["quality_review_scope"] == ("persisted_selected_sections_and_declared_lineage")
    finding_codes = {finding["code"] for finding in body["quality_review"]["findings"]}
    assert {"weak_cta", "missing_internal_links"} <= finding_codes
    revision = body["revision"]
    assert revision["revision_number"] == 2
    assert revision["base_revision_id"] == case.base_revision["revision_id"]
    assert revision["title"] == case.base_revision["title"]
    assert (
        revision["sections"][0]["body_markdown"]
        == case.valid_output["sections"][0]["body_markdown"]
    )
    assert (
        revision["sections"][0]["evidence_ids"] == case.base_revision["sections"][0]["evidence_ids"]
    )
    assert revision["sections"][1:] == case.base_revision["sections"][1:]
    assert revision["publish_ready"] is False
    metadata = revision["proposal_metadata"]
    assert metadata["codex_run_id"] == body["run_id"]
    assert metadata["selected_section_headings"] == [case.selected_heading]
    assert (
        metadata["section_lineage"][0]["evidence_ids"]
        == case.base_revision["sections"][0]["evidence_ids"]
    )
    assert metadata["semantic_review_required"] is True
    workspace = _selected_snapshot(case.client, case.work_item_id)["revision_workspace"]
    assert workspace["status"] == "unreviewed"
    assert workspace["latest_review"] is None
    assert workspace["latest_revision"]["proposal_metadata"] == metadata
    assert {run.status for run in local_state_store().list_codex_runs()} == {
        "blocked",
        "completed",
    }
    assert local_state_store().list_action_mutation_audits() == []
    assert "action_id" not in body


def _proposal_path(work_item_id: str, base_revision_id: str) -> str:
    return (
        f"/api/content/work-items/{work_item_id}/draft-revisions/{base_revision_id}/codex-proposal"
    )
