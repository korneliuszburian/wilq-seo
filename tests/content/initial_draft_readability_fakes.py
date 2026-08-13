from __future__ import annotations

import json

from wilq.codex.app_server import (
    CodexAppServerStructuredTurnRequest,
    CodexAppServerTurnResult,
)
from wilq.content.drafts import initial_full_draft
from wilq.content.drafts.structured_generation import (
    StructuredDraftGenerationContract,
    StructuredDraftGenerationInput,
)
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.regulatory.policy import ContentRegulatoryCoverage
from wilq.content.workflow.decisions.planning import (
    ContentPlanningProposal,
    ContentPlanningSection,
)


class PatchClient:
    def __init__(self, replacements: dict[str, str] | None = None) -> None:
        self.replacements = replacements or {}
        self.requests: list[CodexAppServerStructuredTurnRequest] = []

    def run_structured_turn(
        self,
        request: CodexAppServerStructuredTurnRequest,
    ) -> CodexAppServerTurnResult:
        self.requests.append(request)
        application_context = json.loads(request.application_context)
        candidate = json.loads(request.untrusted_context)["candidate_document"]
        bodies = {
            section["section_id"]: section["body_markdown"] for section in candidate["sections"]
        }
        bodies.update(
            {
                f"faq:{index}": item["answer_markdown"]
                for index, item in enumerate(candidate["faq"], start=1)
            }
        )
        bodies.update(
            {
                f"cta:{index}": item["body_markdown"]
                for index, item in enumerate(candidate["cta_blocks"], start=1)
            }
        )
        bodies.update(
            {f"page_assets:{field}": value for field, value in candidate["page_assets"].items()}
        )
        bodies.update(
            {
                f"link:{index}": item["anchor_text"]
                for index, item in enumerate(candidate["internal_links"], start=1)
            }
        )
        return CodexAppServerTurnResult(
            status="completed",
            output_text=json.dumps(
                {
                    "sections": [
                        {
                            "section_id": section_id,
                            "mode": "replace",
                            "body_markdown": self.replacements.get(
                                section_id,
                                bodies[section_id],
                            ),
                        }
                        for section_id in application_context["affected_section_ids"]
                    ],
                    "publish_ready": False,
                },
                ensure_ascii=False,
            ),
            turn_id=f"readability-repair-{len(self.requests)}",
        )


class BlockedThenPatchClient(PatchClient):
    def run_structured_turn(
        self,
        request: CodexAppServerStructuredTurnRequest,
    ) -> CodexAppServerTurnResult:
        if not self.requests:
            self.requests.append(request)
            return CodexAppServerTurnResult(
                status="blocked",
                turn_id="readability-repair-blocked",
                external_call_attempted=True,
            )
        return super().run_structured_turn(request)


class PatchSequenceClient(PatchClient):
    def __init__(self, replacements_by_turn: list[dict[str, str]]) -> None:
        super().__init__()
        self.replacements_by_turn = replacements_by_turn

    def run_structured_turn(
        self,
        request: CodexAppServerStructuredTurnRequest,
    ) -> CodexAppServerTurnResult:
        self.replacements = self.replacements_by_turn[len(self.requests)]
        return super().run_structured_turn(request)


def planning_input() -> ContentPlanningInput:
    return ContentPlanningInput.model_construct(
        work_item_id="content_work_item_readability_gate",
        planning_input_digest="a" * 64,
        regulatory_coverage=ContentRegulatoryCoverage(),
        claim_ledger=[],
        evidence_ids=["ev_readability_gate"],
    )


def proposal() -> ContentPlanningProposal:
    return ContentPlanningProposal.model_construct(
        work_item_id="content_work_item_readability_gate",
        proposal_id="content_planning_proposal_readability_gate",
        planning_digest="b" * 64,
        planning_input_digest="a" * 64,
        sections=[
            ContentPlanningSection(
                section_id="section_01",
                heading="Pierwszy krok",
                purpose="Wyjaśnij pierwszy krok.",
                evidence_ids=["ev_readability_gate"],
            ),
            ContentPlanningSection(
                section_id="section_02",
                heading="Drugi krok",
                purpose="Wyjaśnij drugi krok.",
                evidence_ids=["ev_readability_gate"],
            ),
        ],
        faq=[],
        cta_blocks=[],
        internal_links=[],
        evidence_ids=["ev_readability_gate"],
    )


def generation_contract() -> StructuredDraftGenerationContract:
    return StructuredDraftGenerationContract.model_construct(
        model_input=StructuredDraftGenerationInput.model_construct(
            claims_removed_or_blocked=[],
            removed_or_blocked_claim_markers=[],
            human_review_questions=[],
        )
    )


def prepared_inputs() -> initial_full_draft._InitialDraftInputs:
    return initial_full_draft._InitialDraftInputs(
        planning_input=planning_input(),
        proposal=proposal(),
        generation_contract=generation_contract(),
    )


__all__ = [
    "BlockedThenPatchClient",
    "PatchClient",
    "PatchSequenceClient",
    "generation_contract",
    "planning_input",
    "prepared_inputs",
    "proposal",
]
