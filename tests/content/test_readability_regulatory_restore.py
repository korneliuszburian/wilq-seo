"""A readability repair must not drop an exact regulatory concept.

Live BDO: the deterministic grounding restored ``bdo_paper_records_rule``, then
the readability turn replaced the section body with clean prose and removed the
concept again, so ``assure_readability_and_repair`` returned
``document_scope_mismatch``. The deterministic grounding is pure, so it must be
re-applied after a model repair before the candidate is treated as blocked.
"""

from __future__ import annotations

import json

from wilq.codex.app_server import (
    CodexAppServerStructuredTurnRequest,
    CodexAppServerTurnResult,
)
from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.drafts.draft_alteration import assure_readability_and_repair
from wilq.content.drafts.draft_plan_preparation import PreparedDraftPlan, prepare_draft_plan
from wilq.content.drafts.initial_draft_validation import (
    document_scope_errors_for_planning_input,
)
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftBlocker,
    ContentInitialDraftModelOutput,
    ContentInitialDraftSectionOutput,
)
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.input_sources import ContentPlanningSourceFact
from wilq.content.regulatory.policy import (
    ContentRegulatoryCoverage,
    ContentRegulatoryDocumentAssertion,
    ContentRegulatoryRequirement,
)
from wilq.content.workflow.decisions.planning import (
    ContentPlanningProposal,
    ContentPlanningSection,
)
from wilq.content.workflow.documents.revisions import ContentDraftRevisionPageAssets

_REQUIREMENT_ID = "bdo_exemptions"
_ASSERTION_ID = "bdo_paper_records_rule"
_TERMS = ["nie upoważnia", "papierowych"]
_WORKING_NOTE = "Ta informacja wymaga weryfikacji przez człowieka przed dalszym użyciem."
_CLEAN_WITHOUT_TERM = "Przedsiębiorca porządkuje dokumentację i planuje kolejne działania."


def _requirement() -> ContentRegulatoryRequirement:
    return ContentRegulatoryRequirement(
        id=_REQUIREMENT_ID,
        label="wyłączenia z wpisu lub ewidencji",
        reason="Treść nie może sugerować identycznej ewidencji.",
        document_assertions=[
            ContentRegulatoryDocumentAssertion(
                id=_ASSERTION_ID,
                label="zasady dokumentacji papierowej",
                required_any_of=_TERMS,
            )
        ],
    )


def _official_fact() -> ContentSourceFact:
    return ContentSourceFact.model_construct(
        source_id="regulatory_source_fact_paper_records",
        extracted_fact="Brak Internetu nie upoważnia do papierowych dokumentów ewidencji.",
        review_status="approved",
        official_source=True,
        evidence_ids=["ev_paper_records"],
        source_connectors=["official_regulatory_review"],
        regulatory_requirement_ids=[_REQUIREMENT_ID],
    )


def _planning_input() -> ContentPlanningInput:
    return ContentPlanningInput.model_construct(
        work_item_id="content_work_item_readability_restore",
        planning_input_digest="a" * 64,
        regulatory_coverage=ContentRegulatoryCoverage.model_construct(
            applicability_status="required",
            requirements=[_requirement()],
            source_facts=[_official_fact()],
        ),
        source_facts=[
            ContentPlanningSourceFact(
                fact_id="planning_paper_records",
                summary="Brak Internetu nie upoważnia do papierowych dokumentów ewidencji.",
                source_connector="official_regulatory_review",
                evidence_ids=["ev_paper_records"],
                source_fact_ids=["regulatory_source_fact_paper_records"],
                regulatory_requirement_ids=[_REQUIREMENT_ID],
            )
        ],
    )


def _proposal() -> ContentPlanningProposal:
    return ContentPlanningProposal.model_construct(
        work_item_id="content_work_item_readability_restore",
        proposal_id="content_planning_proposal_readability_restore",
        planning_digest="b" * 64,
        planning_input_digest="a" * 64,
        sections=[
            ContentPlanningSection(
                section_id="section_exemptions",
                heading="Wyłączenia i ewidencja",
                purpose="Wyjaśnij wyłączenia i zasady dokumentacji.",
                evidence_ids=["ev_paper_records"],
                regulatory_requirement_ids=[_REQUIREMENT_ID],
            )
        ],
    )


class _ReplaceClient:
    def __init__(self, body: str) -> None:
        self.body = body
        self.requests: list[CodexAppServerStructuredTurnRequest] = []

    def run_structured_turn(
        self, request: CodexAppServerStructuredTurnRequest
    ) -> CodexAppServerTurnResult:
        self.requests.append(request)
        context = json.loads(request.application_context)
        return CodexAppServerTurnResult(
            status="completed",
            output_text=json.dumps(
                {
                    "sections": [
                        {
                            "section_id": section_id,
                            "mode": "replace",
                            "body_markdown": self.body,
                        }
                        for section_id in context["affected_section_ids"]
                    ],
                    "publish_ready": False,
                },
                ensure_ascii=False,
            ),
            turn_id=f"readability-repair-{len(self.requests)}",
        )


def test_readability_repair_restores_dropped_regulatory_assertion() -> None:
    planning_input = _planning_input()
    proposal = _proposal()
    prepared_plan = prepare_draft_plan(proposal, planning_input)
    assert isinstance(prepared_plan, PreparedDraftPlan)

    output = ContentInitialDraftModelOutput(
        page_assets=ContentDraftRevisionPageAssets(
            wordpress_title="Tytuł",
            meta_title="Meta",
            meta_description="Opis",
            h1="Nagłówek",
            lead="Lead",
        ),
        sections=[
            ContentInitialDraftSectionOutput(
                section_id="section_exemptions",
                heading="Wyłączenia i ewidencja",
                body_markdown=(
                    "Nie upoważnia to do papierowych dokumentów ewidencji. " + _WORKING_NOTE
                ),
            )
        ],
    )

    def output_blocker(
        candidate: ContentInitialDraftModelOutput,
    ) -> ContentInitialDraftBlocker | None:
        errors = document_scope_errors_for_planning_input(
            planning_input, proposal, candidate, prepared_plan=prepared_plan
        )
        if not errors:
            return None
        return ContentInitialDraftBlocker(
            code="document_scope_mismatch",
            label="Dokument nie odpowiada planowi",
            reason="Model zmienił strukturę.",
            next_step="Odrzuć wynik.",
            source_codes=errors,
        )

    repaired, _trace, blocker = assure_readability_and_repair(
        planning_input=planning_input,
        proposal=proposal,
        output=output,
        trace=ContentCodexRuntimeTrace(status="completed", turn_id="initial-turn"),
        client=_ReplaceClient(_CLEAN_WITHOUT_TERM),
        output_blocker=output_blocker,
        prepared_plan=prepared_plan,
    )

    assert blocker is None
    assert "nie upoważnia" in repaired.sections[0].body_markdown
