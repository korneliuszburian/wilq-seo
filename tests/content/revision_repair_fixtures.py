"""Validated synthetic records and workflow setup for revision repair tests."""

import json
from collections.abc import Callable
from datetime import UTC, datetime
from types import SimpleNamespace

from apps.api.wilq_api.routers import (
    content_independent_review,
    content_revision_repair_action,
    content_semantic_review,
    content_workflow,
)
from tests.content.test_full_draft_generation_v3 import _authorize, _case, _prepare
from wilq.codex.app_server import CodexAppServerTurnResult
from wilq.content.briefs.sales import ContentSalesBrief
from wilq.content.claims.ledger import ContentClaimLedger, content_claim_entry
from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.drafts.structured_generation import build_structured_draft_generation_contract
from wilq.content.inventory.records import ContentInventoryRecord, resolve_content_inventory
from wilq.content.quality import deterministic_revision_gate, independent_review_service
from wilq.content.quality.independent_review_contracts import (
    ROLE_CRITERIA_VERSIONS,
    ContentIndependentReviewFinding,
    ContentIndependentReviewRun,
)
from wilq.content.quality.semantic_review_contracts import CONTENT_SEMANTIC_DIMENSIONS
from wilq.content.workflow.contracts.models import ContentWorkItem


def _synthetic_sales_brief(case, item: ContentWorkItem) -> ContentSalesBrief:
    fact = case.fact
    return ContentSalesBrief(
        id="synthetic-exact-brief",
        work_item_id=item.id,
        topic=item.topic,
        operations_context={
            "enrichment_id": "synthetic-exact-context",
            "intent_label": "Próba syntetyczna",
            "recommended_mode": "refresh",
            "safe_next_step": "Przegląd dokładnej rewizji",
            "source_fact_ids": [fact.source_id],
        },
        draft_allowed=True,
        target_reader="Czytelnik próby syntetycznej",
        buyer_problem="Sprawdzenie zakresu obowiązków",
        buyer_trigger="Przegląd źródła urzędowego",
        search_intent="Sprawdzenie obowiązku",
        service_fit="Ocena zakresu dokumentacji",
        final_canonical_url=case.proposal.final_canonical_url,
        existing_content_plan="Próba syntetyczna odświeżenia istniejącej strony",
        h1_direction=item.topic,
        cta_direction="Sprawdź zakres dokumentacji",
        source_facts=[
            {
                "evidence_id": evidence_id,
                "source_connector": fact.source_connectors[0],
                "summary": fact.extracted_fact,
                "source_fact_ids": [fact.source_id],
            }
            for evidence_id in fact.evidence_ids
        ],
        signal_quality={
            "status": "strong",
            "status_label": "Wyłącznie źródło próby syntetycznej",
            "reason": "Dokładny zatwierdzony fakt fixture; nie jest to ocena rzeczywistego popytu.",
            "evidence_id_count": len(fact.evidence_ids),
            "source_connector_count": len(fact.source_connectors),
            "source_fact_count": 1,
            "missing_evidence_count": 0,
            "knowledge_constraint_count": 0,
            "review_required_knowledge_card_count": 0,
            "measurement_baseline_ready": False,
            "safe_next_step": "Przegląd próby syntetycznej",
        },
        evidence_ids=fact.evidence_ids,
        source_connectors=fact.source_connectors,
        measurement_plan={
            "measurement_window_id": item.measurement_window_id,
            "metrics_to_watch": [],
            "baseline_source_connectors": [],
            "baseline_evidence_ids": [],
            "measurement_readiness_label": "Brak rzeczywistej bazy",
            "measurement_readiness_reason": "Próba syntetyczna; brak pomiaru",
            "earliest_verdict_note": "Nie ma werdyktu rzeczywistego",
            "success_claim_rule": "Nie twierdzić, że osiągnięto wynik",
        },
    )


class OwningSyntheticRepairClient:
    """A schema-shaped test reply, not a real model or human approval."""

    def __init__(self, case):
        self.case = case
        self.request = None
        self.model_count = 0
        self.after_model: Callable[[object], None] | None = None

    def run_structured_turn(self, request):
        case = self.case
        self.request = request
        self.model_count += 1
        case.turns.append(request)
        base = case.workflow_store.load_draft_revision_state(
            case.proposal.work_item_id
        ).latest_revision
        assert base is not None
        section = base.sections[0]
        contract = case.snapshot.structured_generation.structured_generation_result.contract
        output = {
            "draft_kind": "section_draft",
            "language": "pl-PL",
            "title": base.title,
            "h1": base.title,
            "meta_title": base.page_assets.meta_title,
            "meta_description": base.page_assets.meta_description,
            "sections": [
                {
                    "heading": section.heading,
                    "body_markdown": section.body_markdown
                    + " Dodatkowo sprawdź zakres dokumentacji przed kolejnym krokiem.",
                    "evidence_ids": section.evidence_ids,
                    "claims_used": contract.model_input.claims_allowed,
                }
            ],
            "faq": [],
            "cta": "Sprawdź zakres dokumentacji.",
            "internal_links": [],
            "source_facts_used": section.evidence_ids,
            "claims_needing_review": [],
            "forbidden_claims_avoided": contract.model_input.claims_removed_or_blocked,
            "human_review_checklist": contract.model_input.human_review_questions,
            "publish_ready": False,
        }
        result = CodexAppServerTurnResult(status="completed", output_text=json.dumps(output))
        if self.after_model is not None:
            self.after_model(request)
        return result


def _assert_original_gate_passes(*args, **kwargs):
    result = _ORIGINAL_GATE(*args, **kwargs)
    assert result is not None and result.status == "passed"
    return result


def _repair_work_item(case) -> ContentWorkItem:
    fact = case.fact
    item_fields = vars(case.snapshot.preflight.item) | {
        "topic": "Próba syntetyczna dokładnej rewizji",
        "evidence_ids": fact.evidence_ids,
        "source_connectors": fact.source_connectors,
        "duplicate_status": "checked",
        "inventory_status": "resolved",
        "canonical_status": "resolved",
        "preflight_status": "draft_allowed",
        "preserve_first_plan_status": "approved",
        "sales_brief_status": "approved",
        "sales_brief_id": "synthetic-exact-brief",
        "claim_ledger_status": "approved",
        "claim_ledger_id": "synthetic-exact-ledger",
        "draft_package_status": "approved",
        "draft_package_id": "synthetic-exact-package",
        "measurement_window_status": "planned",
        "measurement_window_id": "synthetic-unmeasured-window",
    }
    return ContentWorkItem(**item_fields)


def _synthetic_claim_ledger(case, item: ContentWorkItem) -> ContentClaimLedger:
    fact = case.fact
    return ContentClaimLedger(
        id="synthetic-exact-ledger",
        work_item_id=item.id,
        entries=[
            content_claim_entry(
                claim_id="synthetic-official-claim",
                claim_text=fact.extracted_fact,
                claim_type="legal_requirement_claim",
                evidence_ids=fact.evidence_ids,
                source_connectors=fact.source_connectors,
                human_reviewed=True,
                reviewer_id=fact.reviewer,
            )
        ],
    )


def _synthetic_draft_package(
    case, item: ContentWorkItem, brief: ContentSalesBrief, ledger: ContentClaimLedger
) -> ContentDraftPackage:
    fact = case.fact
    return ContentDraftPackage(
        id="synthetic-exact-package",
        work_item_id=item.id,
        brief_id=brief.id,
        claim_ledger_id=ledger.id,
        title=item.topic,
        claims_used=[fact.extracted_fact],
        human_review_questions=["Czy zakres korekty zgadza się z dokładnym źródłem?"],
        section_to_evidence_map=[
            {"section_heading": section.heading, "evidence_ids": fact.evidence_ids}
            for section in case.proposal.sections
        ],
        sections=[
            {
                "heading": section.heading,
                "purpose": section.purpose,
                "evidence_ids": fact.evidence_ids,
            }
            for section in case.proposal.sections
        ],
    )


def _install_validated_repair_inputs(case, item, brief, ledger, package) -> None:
    fact = case.fact
    case.snapshot.preflight.item = item
    case.snapshot.preflight.inventory_resolution = resolve_content_inventory(
        [
            ContentInventoryRecord(
                id="synthetic-exact-inventory",
                url=case.proposal.final_canonical_url,
                final_canonical_url=case.proposal.final_canonical_url,
                intended_final_url=case.proposal.final_canonical_url,
                content_status="published",
                evidence_ids=fact.evidence_ids,
                source_connectors=fact.source_connectors,
            )
        ],
        duplicate_risk="clear",
    )
    case.snapshot.sales_brief = SimpleNamespace(sales_brief_result=SimpleNamespace(brief=brief))
    case.snapshot.claim_ledger = ledger
    case.snapshot.draft_package = SimpleNamespace(
        draft_package_result=SimpleNamespace(draft_package=package)
    )


def _install_structured_generation(case, item, brief, ledger, package) -> None:
    generation = build_structured_draft_generation_contract(
        item=item,
        sales_brief=brief,
        claim_ledger=ledger,
        draft_package=package,
        planning_proposal=case.proposal,
        planning_input=case.frozen,
    )
    assert generation.contract is not None, generation.blockers
    case.snapshot.structured_generation = SimpleNamespace(structured_generation_result=generation)


def complete_repair_case(tmp_path, monkeypatch):
    """Build the positive case with validated synthetic records and exact source lineage."""
    case = _case(tmp_path, monkeypatch)
    item = _repair_work_item(case)
    brief = _synthetic_sales_brief(case, item)
    ledger = _synthetic_claim_ledger(case, item)
    package = _synthetic_draft_package(case, item, brief, ledger)
    _install_validated_repair_inputs(case, item, brief, ledger, package)
    _install_structured_generation(case, item, brief, ledger, package)
    fact = case.fact
    monkeypatch.setattr(deterministic_revision_gate, "ekologus_source_facts", lambda: (fact,))
    monkeypatch.setattr(
        independent_review_service,
        "deterministic_gate_for_snapshot",
        _assert_original_gate_passes,
    )
    return case


def _root_revision(case):
    action_id = _prepare(case)
    _authorize(case, action_id)
    response = case.http.post(f"/api/content/full-draft-generations-v3/{action_id}/dispatch")
    assert response.status_code == 200, response.text
    return case.http.get(
        f"/api/content/work-items/{case.proposal.work_item_id}/initial-draft"
    ).json()["revision"]


def _repair_review_snapshot_loader(case):
    from wilq.content.workflow.pipeline_steps.snapshot_assembly import (
        build_content_draft_revision_workspace,
    )

    def load(work_item_id: str):
        state = case.workflow_store.load_draft_revision_state(work_item_id)
        snapshot = SimpleNamespace(**vars(case.snapshot))
        snapshot.revision_workspace = build_content_draft_revision_workspace(
            item=snapshot.preflight.item,
            draft_package=snapshot.draft_package.draft_package_result.draft_package,
            state=state,
            structured_contract_present=bool(
                snapshot.structured_generation.structured_generation_result.contract
            ),
            planning_digest=case.proposal.planning_digest,
            planning_input_digest=case.frozen.planning_input_digest,
            service_card_id=case.proposal.service_card_id,
        )
        return snapshot

    return load


def _patch_review_stores(case, monkeypatch, loader):
    from wilq.content.quality.independent_review_store import ContentIndependentReviewStore
    from wilq.content.quality.semantic_review_store import ContentSemanticReviewStore

    semantic_store = ContentSemanticReviewStore(case.workflow_store.path)
    independent_store = ContentIndependentReviewStore(case.workflow_store.path)
    monkeypatch.setattr(content_workflow, "semantic_review_snapshot_for_work_item_or_404", loader)
    monkeypatch.setattr(content_workflow, "content_workflow_store", lambda: case.workflow_store)
    monkeypatch.setattr(
        content_semantic_review, "content_semantic_review_store", lambda: semantic_store
    )
    monkeypatch.setattr(
        content_independent_review,
        "content_independent_review_store",
        lambda: independent_store,
    )
    monkeypatch.setattr(
        content_revision_repair_action,
        "content_semantic_review_store",
        lambda: semantic_store,
    )
    monkeypatch.setattr(
        content_revision_repair_action,
        "content_independent_review_store",
        lambda: independent_store,
    )
    monkeypatch.setattr(
        independent_review_service, "content_workflow_store", lambda: case.workflow_store
    )
    monkeypatch.setattr(
        independent_review_service,
        "build_content_planning_input",
        lambda *_args, **_kwargs: SimpleNamespace(
            planning_input=case.current["input"], blockers=[]
        ),
    )
    return semantic_store, independent_store


class SyntheticSemanticReviewClient:
    """Return a schema-shaped semantic review result without invoking a model."""

    def run_structured_turn(self, _request):
        output = {
            "language": "pl-PL",
            "dimensions": [
                {
                    "dimension": dimension,
                    "status": "strong",
                    "reason": "Dokładny fixture review.",
                    "affected_targets": ["whole_document"],
                }
                for dimension in CONTENT_SEMANTIC_DIMENSIONS
            ],
            "findings": [],
            "publish_ready": False,
            "human_review_required": True,
        }
        return CodexAppServerTurnResult(status="completed", output_text=json.dumps(output))


def _register_review_routes(case, monkeypatch, loader, repair_client):
    from fastapi import APIRouter

    from wilq.content.workflow.store.store import ContentWorkflowStore

    monkeypatch.setattr(
        content_semantic_review,
        "content_codex_app_server_client",
        SyntheticSemanticReviewClient,
    )
    local_router = APIRouter()
    content_semantic_review.register_content_semantic_review_routes(
        local_router, snapshot_loader=loader
    )
    content_independent_review.register_content_independent_review_routes(
        local_router, snapshot_loader=loader
    )
    content_revision_repair_action.register_content_revision_repair_action_routes(
        local_router,
        snapshot_loader=loader,
        workflow_store_factory=lambda: ContentWorkflowStore(case.workflow_store.path),
        run_store_factory=lambda: case.audit_store,
        client_factory=lambda: repair_client,
    )
    case.app.include_router(local_router)
    case.app.include_router(content_workflow.router)


def _submit_semantic_review(case, root):
    path = (
        f"/api/content/work-items/{case.proposal.work_item_id}/draft-revisions/"
        f"{root['revision_id']}/semantic-review"
    )
    response = case.http.post(
        path,
        json={
            "expected_revision_digest": root["content_digest"],
            "requested_by": "synthetic-reviewer",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["review"]["revision_digest"] == root["content_digest"]


def _independent_review_run(case, root, role, evidence_ids, source_connectors):
    return ContentIndependentReviewRun(
        run_id=f"repair_review_{role}",
        work_item_id=case.proposal.work_item_id,
        revision_id=root["revision_id"],
        revision_digest=root["content_digest"],
        research_packet_id=root["research_packet_id"],
        research_packet_digest=root["research_packet_digest"],
        role=role,
        # Legacy model fields below are synthetic metadata; no model runner is invoked.
        model_provider="opencode-go",
        model_id="deepseek-v4.1-flash",
        model_variant="max",
        criteria_version=ROLE_CRITERIA_VERSIONS[role],
        findings=[
            ContentIndependentReviewFinding(
                finding_id=f"finding_{role}",
                code="reviewed_component",
                severity="minor",
                label="Sprawdź wybrany komponent",
                reason="Fixture review dotyczy dokładnej rewizji.",
                instruction="Zachowaj zakres i źródła.",
                affected_targets=[root["sections"][0]["section_id"]],
                evidence_ids=evidence_ids,
            )
        ],
        evidence_ids=evidence_ids,
        source_connectors=source_connectors,
        requested_by=f"synthetic-{role}",
        created_at=datetime.now(UTC),
    )


def _reject_foreign_packet_review(case, path, run, store, evidence_digest):
    foreign_run = ContentIndependentReviewRun(
        **{
            **run.model_dump(mode="python"),
            "run_id": "foreign_packet_review_content_ux",
            "research_packet_id": "synthetic-foreign-packet",
            "research_packet_digest": "0" * 64,
        }
    )
    stored_before = store.for_revision(case.proposal.work_item_id, run.revision_id, evidence_digest)
    turns_before = len(case.turns)
    response = case.http.post(
        path,
        json={
            "expected_revision_digest": evidence_digest,
            "run": foreign_run.model_dump(mode="json"),
        },
    )
    assert response.status_code == 409, response.text
    assert response.json()["status"] == "conflict"
    assert (
        store.for_revision(case.proposal.work_item_id, run.revision_id, evidence_digest)
        == stored_before
        == []
    )
    assert len(case.turns) == turns_before


def _submit_independent_reviews(case, root, store):
    evidence_ids = sorted(
        {evidence_id for section in root["sections"] for evidence_id in section["evidence_ids"]}
    )
    path = (
        f"/api/content/work-items/{case.proposal.work_item_id}/draft-revisions/"
        f"{root['revision_id']}/independent-reviews"
    )
    for role in ("content_ux", "seo", "factual_regulatory"):
        run = _independent_review_run(case, root, role, evidence_ids, case.fact.source_connectors)
        if role == "content_ux":
            _reject_foreign_packet_review(case, path, run, store, root["content_digest"])
        response = case.http.post(
            path,
            json={
                "expected_revision_digest": root["content_digest"],
                "run": run.model_dump(mode="json"),
            },
        )
        assert response.status_code == 200, response.text
        finding_id = run.findings[0].finding_id
        disposition = case.http.post(
            f"{path}/{run.run_id}/findings/{finding_id}/disposition",
            json={
                "expected_revision_digest": root["content_digest"],
                "disposition": "deferred",
                "reason": "Zachowano jako advisory; human needs_changes wskazuje komponent.",
                "disposed_by": "synthetic-reviewer",
                "evidence_ids": evidence_ids,
            },
        )
        assert disposition.status_code == 200, disposition.text
    return evidence_ids


def _submit_human_needs_changes(case, root, evidence_ids):
    path = (
        f"/api/content/work-items/{case.proposal.work_item_id}/draft-revisions/"
        f"{root['revision_id']}/review"
    )
    response = case.http.post(
        path,
        json={
            "expected_revision_digest": root["content_digest"],
            "reviewed_by": "synthetic-wilku",
            "decision": "needs_changes",
            "notes": "Popraw wskazany fragment i zachowaj exact source lineage.",
            "checked_items": ["semantic_review", "three_independent_roles"],
            "evidence_ids": evidence_ids,
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["review"]["decision"] == "needs_changes"


def _preview_and_audit_repair_action(case, root):
    path = (
        f"/api/content/work-items/{case.proposal.work_item_id}/draft-revisions/"
        f"{root['revision_id']}/repair-action/preview"
    )
    preview = case.http.post(
        path,
        json={
            "expected_base_digest": root["content_digest"],
            "selected_section_ids": [root["sections"][0]["section_id"]],
            "requested_by": "synthetic-operator",
        },
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["generation_performed"] is False
    action_id = preview.json()["action_id"]
    action_path = f"/api/actions/{action_id}"
    operations = [
        ("validate", None),
        ("preview", {}),
        (
            "review",
            {
                "outcome": "approved_for_prepare",
                "reviewed_by": "synthetic-reviewer",
                "notes": "Exact revision repair.",
                "checked_items": ["reviewed_exact_content_revision_repair"],
            },
        ),
        (
            "confirm",
            {
                "confirmed_by": "synthetic-reviewer",
                "preview_acknowledged": True,
                "notes": "Syntetyczna próba exact korekty; bez zapisu u dostawcy.",
            },
        ),
        ("impact-check", {"checked_by": "synthetic-reviewer", "notes": "Local child only."}),
    ]
    for operation, body in operations:
        result = case.http.post(f"{action_path}/{operation}", json=body)
        assert result.status_code == 200, result.text
    turns_before_apply = len(case.turns)
    applied = case.http.post(
        f"{action_path}/apply",
        json={"confirm": True, "confirmed_by": "synthetic-reviewer"},
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["applied"] is True
    assert len(case.turns) == turns_before_apply
    return action_id


def prepare_reviewed_repair_action(tmp_path, monkeypatch):
    """Prepare a reviewed base, repair preview, and audited local authorization."""
    case = complete_repair_case(tmp_path, monkeypatch)
    root = _root_revision(case)
    loader = _repair_review_snapshot_loader(case)
    _, independent_store = _patch_review_stores(case, monkeypatch, loader)
    repair_client = OwningSyntheticRepairClient(case)
    _register_review_routes(case, monkeypatch, loader, repair_client)
    _submit_semantic_review(case, root)
    evidence_ids = _submit_independent_reviews(case, root, independent_store)
    _submit_human_needs_changes(case, root, evidence_ids)
    action_id = _preview_and_audit_repair_action(case, root)
    return case, root, action_id, repair_client


_ORIGINAL_GATE = independent_review_service.deterministic_gate_for_snapshot
