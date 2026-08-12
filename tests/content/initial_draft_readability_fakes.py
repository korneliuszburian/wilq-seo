from __future__ import annotations

import json

from wilq.codex.app_server import (
    CodexAppServerStructuredTurnRequest,
    CodexAppServerTurnResult,
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


__all__ = ["BlockedThenPatchClient", "PatchClient", "PatchSequenceClient"]
