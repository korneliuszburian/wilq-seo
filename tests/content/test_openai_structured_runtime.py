from __future__ import annotations

import json
from typing import Any

from wilq.content.drafts.openai_runtime import (
    build_openai_structured_draft_request,
    execute_openai_structured_draft_generation,
)
from wilq.content.drafts.structured_generation import (
    StructuredDraftGenerationContract,
    StructuredDraftGenerationInput,
    StructuredDraftOutput,
    StructuredDraftSectionInput,
    StructuredDraftSourceFact,
    structured_draft_output_schema,
)


class _FakeResponses:
    def __init__(self, output: dict[str, object] | str) -> None:
        self.output = output
        self.calls: list[dict[str, object]] = []

    def create(self, **payload: object) -> dict[str, object]:
        self.calls.append(payload)
        if isinstance(self.output, str):
            return {"output_text": self.output}
        return {"output_parsed": self.output}


class _FakeClient:
    def __init__(self, output: dict[str, object] | str) -> None:
        self.responses = _FakeResponses(output)


def _contract() -> StructuredDraftGenerationContract:
    model_input = StructuredDraftGenerationInput(
        work_item_id="content_work_item_bdo",
        draft_kind="section_draft",
        title="BDO dla firm",
        final_canonical_url="https://ekologus.pl/bdo/",
        source_public_url="https://ekologus.pl/bdo/",
        preview_url="https://ekologus.dev.proudsite.pl/bdo/",
        target_reader="Osoba odpowiedzialna za środowisko w firmie",
        buyer_problem="Nie wie, czy obowiązki BDO dotyczą jego firmy.",
        buyer_trigger="Kontrola albo porządkowanie dokumentów.",
        search_intent="Informacyjno-usługowy.",
        service_fit="Konsultacja i obsługa obowiązków środowiskowych.",
        cta_direction="Zaproponuj konsultację bez obietnicy wyniku.",
        sections=[
            StructuredDraftSectionInput(
                heading="Kogo dotyczy BDO",
                purpose="Wyjaśnić zakres bez obietnic prawnych.",
                evidence_ids=["ev_gsc_bdo", "ev_wp_bdo"],
                draft_notes=["Zachowaj ostrożny język."],
            )
        ],
        source_facts=[
            StructuredDraftSourceFact(
                evidence_id="ev_gsc_bdo",
                source_connector="google_search_console",
                summary="GSC potwierdza popyt na temat.",
            )
        ],
        claims_allowed=[
            "Ekologus pomaga firmom w obowiązkach związanych z BDO."
        ],
        claims_removed_or_blocked=["Ta treść zwiększy liczbę leadów."],
        human_review_questions=["Czy to brzmi jak Ekologus?"],
    )
    return StructuredDraftGenerationContract(
        model_input=model_input,
        output_schema=structured_draft_output_schema(),
        system_instruction="Pisz tylko z dowodów.",
        user_instruction="Przygotuj szkic z identyfikatorami dowodów.",
    )


def _draft_output(**overrides: Any) -> dict[str, object]:
    output: dict[str, object] = {
        "draft_kind": "section_draft",
        "language": "pl-PL",
        "title": "BDO dla firm",
        "meta_title": "BDO dla firm",
        "meta_description": "Sprawdź, kiedy warto skonsultować obowiązki BDO.",
        "h1": "BDO dla firm",
        "sections": [
            {
                "heading": "Kogo dotyczy BDO",
                "body_markdown": "BDO warto sprawdzić na podstawie sytuacji firmy.",
                "evidence_ids": ["ev_gsc_bdo", "ev_wp_bdo"],
                "claims_used": [
                    "Ekologus pomaga firmom w obowiązkach związanych z BDO."
                ],
            }
        ],
        "faq": ["Czy każda firma musi mieć BDO?"],
        "cta": "Skontaktuj się z Ekologus, żeby omówić sytuację firmy.",
        "internal_links": ["https://ekologus.pl/kontakt/"],
        "source_facts_used": ["ev_gsc_bdo", "ev_wp_bdo"],
        "claims_needing_review": [],
        "forbidden_claims_avoided": ["Ta treść zwiększy liczbę leadów."],
        "human_review_checklist": ["Czy to brzmi jak Ekologus?"],
        "publish_ready": False,
    }
    output.update(overrides)
    return output


def test_runtime_builds_strict_openai_structured_output_payload() -> None:
    request = build_openai_structured_draft_request(
        contract=_contract(),
        model="gpt-5",
    )

    payload = request.model_dump(by_alias=True, mode="json")
    assert payload["model"] == "gpt-5"
    assert payload["input"][0]["role"] == "system"
    assert payload["input"][1]["role"] == "user"
    assert payload["text"]["format"]["type"] == "json_schema"
    assert payload["text"]["format"]["name"] == "wilq_content_structured_draft_v1"
    assert payload["text"]["format"]["strict"] is True
    assert payload["text"]["format"]["schema"]["additionalProperties"] is False


def test_runtime_dry_run_does_not_call_external_model() -> None:
    fake_client = _FakeClient(_draft_output())

    result = execute_openai_structured_draft_generation(
        contract=_contract(),
        model="gpt-5",
        client=fake_client,
    )

    assert result.status == "dry_run_ready"
    assert result.request_payload is not None
    assert result.external_call_attempted is False
    assert result.output is None
    assert fake_client.responses.calls == []


def test_runtime_blocks_live_generation_without_explicit_enablement() -> None:
    fake_client = _FakeClient(_draft_output())

    result = execute_openai_structured_draft_generation(
        contract=_contract(),
        model="gpt-5",
        mode="live",
        client=fake_client,
    )

    assert result.status == "blocked"
    assert result.external_call_attempted is False
    assert "live_generation_disabled" in {blocker.code for blocker in result.blockers}
    assert fake_client.responses.calls == []


def test_runtime_parses_fake_structured_output_when_live_is_enabled() -> None:
    fake_client = _FakeClient(_draft_output())

    result = execute_openai_structured_draft_generation(
        contract=_contract(),
        model="gpt-5",
        mode="live",
        client=fake_client,
        live_generation_enabled=True,
    )

    assert result.status == "generated"
    assert result.external_call_attempted is True
    assert result.output is not None
    assert isinstance(result.output, StructuredDraftOutput)
    assert result.output.publish_ready is False
    assert fake_client.responses.calls[0]["text"]["format"]["strict"] is True


def test_runtime_blocks_invalid_structured_output() -> None:
    fake_client = _FakeClient(json.dumps(_draft_output(publish_ready=True)))

    result = execute_openai_structured_draft_generation(
        contract=_contract(),
        model="gpt-5",
        mode="live",
        client=fake_client,
        live_generation_enabled=True,
    )

    assert result.status == "blocked"
    assert result.external_call_attempted is True
    assert "invalid_structured_output" in {blocker.code for blocker in result.blockers}
