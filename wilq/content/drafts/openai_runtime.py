from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Literal, Protocol, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from wilq.content.drafts.structured_generation import (
    StructuredDraftGenerationContract,
    StructuredDraftOutput,
)

OpenAIStructuredDraftRuntimeMode = Literal["dry_run", "live"]
OpenAIStructuredDraftRuntimeStatus = Literal["dry_run_ready", "generated", "blocked"]
OpenAIStructuredDraftRuntimeBlockerCode = Literal[
    "missing_contract",
    "missing_model",
    "live_generation_disabled",
    "missing_client",
    "openai_call_failed",
    "missing_structured_output",
    "invalid_structured_output",
]


class OpenAIResponsesProtocol(Protocol):
    def create(self, **payload: object) -> object: ...


class OpenAIClientProtocol(Protocol):
    responses: OpenAIResponsesProtocol


class OpenAIInputMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["system", "user"]
    content: str


class OpenAIJsonSchemaFormat(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["json_schema"] = "json_schema"
    name: str
    strict: Literal[True] = True
    schema_: dict[str, object] = Field(alias="schema")


class OpenAITextFormat(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: OpenAIJsonSchemaFormat


class OpenAIStructuredDraftRequestPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    model: str
    input: list[OpenAIInputMessage]
    text: OpenAITextFormat
    temperature: float = 0.2
    max_output_tokens: int = 4000


class OpenAIStructuredDraftRuntimeBlocker(BaseModel):
    code: OpenAIStructuredDraftRuntimeBlockerCode
    label: str
    reason: str
    next_step: str


class OpenAIStructuredDraftRuntimeResult(BaseModel):
    status: OpenAIStructuredDraftRuntimeStatus
    request_payload: OpenAIStructuredDraftRequestPayload | None = None
    output: StructuredDraftOutput | None = None
    external_call_attempted: bool = False
    blockers: list[OpenAIStructuredDraftRuntimeBlocker] = Field(default_factory=list)


def build_openai_structured_draft_request(
    *,
    contract: StructuredDraftGenerationContract,
    model: str,
) -> OpenAIStructuredDraftRequestPayload:
    return OpenAIStructuredDraftRequestPayload(
        model=model,
        input=[
            OpenAIInputMessage(role="system", content=contract.system_instruction),
            OpenAIInputMessage(role="user", content=contract.user_instruction),
        ],
        text=OpenAITextFormat(
            format=OpenAIJsonSchemaFormat(
                name=contract.schema_name,
                schema=contract.output_schema,
            )
        ),
    )


def execute_openai_structured_draft_generation(
    *,
    contract: StructuredDraftGenerationContract | None,
    model: str | None,
    mode: OpenAIStructuredDraftRuntimeMode = "dry_run",
    client: OpenAIClientProtocol | None = None,
    live_generation_enabled: bool = False,
) -> OpenAIStructuredDraftRuntimeResult:
    blockers = _runtime_blockers(
        contract=contract,
        model=model,
        mode=mode,
        client=client,
        live_generation_enabled=live_generation_enabled,
    )
    if blockers:
        return OpenAIStructuredDraftRuntimeResult(status="blocked", blockers=blockers)

    assert contract is not None
    assert model is not None
    request_payload = build_openai_structured_draft_request(
        contract=contract,
        model=model,
    )
    if mode == "dry_run":
        return OpenAIStructuredDraftRuntimeResult(
            status="dry_run_ready",
            request_payload=request_payload,
        )

    assert client is not None
    try:
        response = client.responses.create(
            **request_payload.model_dump(by_alias=True, mode="json")
        )
    except Exception as exc:
        return OpenAIStructuredDraftRuntimeResult(
            status="blocked",
            request_payload=request_payload,
            external_call_attempted=True,
            blockers=[
                _blocker(
                    "openai_call_failed",
                    "Nie udało się wygenerować szkicu",
                    "Runtime Structured Outputs zwrócił błąd podczas wywołania.",
                    f"Sprawdź konfigurację runtime i ponów próbę. Szczegół: {type(exc).__name__}.",
                )
            ],
        )

    output_text = _structured_output_text(response)
    if output_text is None:
        return OpenAIStructuredDraftRuntimeResult(
            status="blocked",
            request_payload=request_payload,
            external_call_attempted=True,
            blockers=[
                _blocker(
                    "missing_structured_output",
                    "Brakuje ustrukturyzowanego wyniku",
                    "Runtime nie zwrócił treści zgodnej z oczekiwanym kanałem JSON.",
                    "Powtórz generowanie albo sprawdź adapter OpenAI SDK.",
                )
            ],
        )

    try:
        output = StructuredDraftOutput.model_validate_json(output_text)
    except ValidationError:
        return OpenAIStructuredDraftRuntimeResult(
            status="blocked",
            request_payload=request_payload,
            external_call_attempted=True,
            blockers=[
                _blocker(
                    "invalid_structured_output",
                    "Szkic nie spełnia schematu",
                    "Runtime zwrócił JSON, ale nie przeszedł ścisłego kontraktu WILQ.",
                    "Nie przekazuj szkicu dalej; napraw kontrakt lub ponów generowanie.",
                )
            ],
        )

    return OpenAIStructuredDraftRuntimeResult(
        status="generated",
        request_payload=request_payload,
        output=output,
        external_call_attempted=True,
    )


def _runtime_blockers(
    *,
    contract: StructuredDraftGenerationContract | None,
    model: str | None,
    mode: OpenAIStructuredDraftRuntimeMode,
    client: OpenAIClientProtocol | None,
    live_generation_enabled: bool,
) -> list[OpenAIStructuredDraftRuntimeBlocker]:
    blockers: list[OpenAIStructuredDraftRuntimeBlocker] = []
    if contract is None:
        blockers.append(
            _blocker(
                "missing_contract",
                "Brakuje kontraktu generowania",
                "Runtime może działać tylko na kontrakcie z WILQ API.",
                "Najpierw zbuduj kontrakt generowania szkicu.",
            )
        )
    if not model:
        blockers.append(
            _blocker(
                "missing_model",
                "Brakuje modelu",
                "Runtime wymaga jawnie wskazanego modelu OpenAI.",
                "Podaj model dla runtime Structured Outputs.",
            )
        )
    if mode == "live" and not live_generation_enabled:
        blockers.append(
            _blocker(
                "live_generation_disabled",
                "Generowanie live jest wyłączone",
                "Ten endpoint nie może przypadkowo wywołać zewnętrznego modelu.",
                "Włącz live runtime tylko w osobnym, audytowanym adapterze.",
            )
        )
    if mode == "live" and live_generation_enabled and client is None:
        blockers.append(
            _blocker(
                "missing_client",
                "Brakuje klienta OpenAI",
                "Live runtime wymaga jawnie przekazanego klienta SDK.",
                "Podaj klienta SDK w audytowanym adapterze runtime.",
            )
        )
    return blockers


def _structured_output_text(response: object) -> str | None:
    parsed = _field(response, "output_parsed")
    if parsed is not None:
        if isinstance(parsed, str):
            return parsed
        if isinstance(parsed, Mapping):
            return json.dumps(parsed)
        if isinstance(parsed, StructuredDraftOutput):
            return parsed.model_dump_json()

    text = _field(response, "output_text")
    if isinstance(text, str):
        return text
    return None


def _field(response: object, name: str) -> object | None:
    if isinstance(response, Mapping):
        return response.get(name)
    return cast(object | None, getattr(response, name, None))


def _blocker(
    code: OpenAIStructuredDraftRuntimeBlockerCode,
    label: str,
    reason: str,
    next_step: str,
) -> OpenAIStructuredDraftRuntimeBlocker:
    return OpenAIStructuredDraftRuntimeBlocker(
        code=code,
        label=label,
        reason=reason,
        next_step=next_step,
    )
