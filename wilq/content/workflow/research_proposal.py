"""Server-owned, review-only research proposals from exact page observations."""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Literal, Protocol, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.codex.app_server import (
    CodexAppServerClientProtocol,
    CodexAppServerStructuredTurnRequest,
    CodexAppServerTurnResult,
    StdioCodexAppServerClient,
)
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.evidence_acquisition_contracts import (
    EvidenceAcquisitionCurrentProjection,
    EvidenceAcquisitionRun,
    EvidenceObservationReceipt,
    OfficialGuidanceObservationReceipt,
)
from wilq.content.workflow.evidence_acquisition_snapshot import current_page_receipt_is_fresh
from wilq.content.workflow.official_guidance import (
    OfficialGuidanceCandidate,
    official_guidance_receipt_is_fresh,
    resolve_official_guidance_candidate,
)
from wilq.security.redaction import SECRET_VALUE_RE

_HEX64 = r"^[0-9a-f]{64}$"
_SAFE_IDENTIFIER = r"^[a-z][a-z0-9_-]{0,239}$"
_SECRET_FIELD_RE = re.compile(
    r"(?i)(?:token|secret|password|credential|api[_-]?key)\s*[:=]\s*\S+"
)
_SECRET_VARIANT_RE = re.compile(
    r"(?i)(?:s\s*k\s*-\s*[a-z0-9_-]{8,}|"
    r"(?:token|secret|password|credential|api\s*key)\s*[:=]\s*\S+)"
)
_LEGAL_CLAIM_RE = re.compile(
    r"\b(?:musi|nalezy|wymaga|wymagany|powinien|obowiazek|obowiazkowy|"
    r"zobowiazany|termin ustawowy|kara|sankcja|zgodn\w*\s+z|praw\w*|"
    r"ustaw\w*|rozporzadzen\w*|must|shall|required|obligation|compliance|penalty|"
    r"regulation|law)\b"
)
_MODEL_ID = "codex_app_server_structured_research"


class ResearcherStructuredOutput(BaseModel):
    """Only the model-authored proposal fields; lineage is server-owned."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    proposed_claim: str | None = Field(default=None, max_length=1200)
    scope: str | None = Field(default=None, max_length=600)
    observation_ids: tuple[str, ...] = Field(default=(), max_length=8)
    contradictions: tuple[str, ...] = Field(default=(), max_length=16)
    unknowns: tuple[str, ...] = Field(default=(), max_length=16)


class ResearchProposalBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    safe_next_step: str = Field(min_length=1)


class ContentResearchProposalAttempt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    response_type: Literal["content_research_proposal_attempt"] = (
        "content_research_proposal_attempt"
    )
    contract_version: Literal["content_research_proposal_attempt_v2"] = (
        "content_research_proposal_attempt_v2"
    )
    proposal_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    proposal_digest: str = Field(pattern=_HEX64)
    attempt_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    subject_kind: Literal["identity_binding", "authoring_inventory_receipt"] = (
        "identity_binding"
    )
    authoring_inventory_receipt_id: str | None = None
    authoring_inventory_receipt_digest: str | None = Field(default=None, pattern=_HEX64)
    acquisition_run_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    acquisition_run_digest: str | None = Field(default=None, pattern=_HEX64)
    status: Literal["ready_for_review", "blocked"]
    approved: Literal[False] = False
    review_required: Literal[True] = True
    research_question_safe: str | None = Field(default=None, max_length=1000)
    model_id: str = Field(min_length=1, max_length=160)
    researcher_run_id: str | None = Field(default=None, max_length=240)
    input_digest: str = Field(pattern=_HEX64)
    prompt_digest: str = Field(pattern=_HEX64)
    schema_digest: str = Field(pattern=_HEX64)
    output_digest: str | None = Field(default=None, pattern=_HEX64)
    observation_id: str | None = Field(default=None, max_length=240)
    evidence_ids: tuple[str, ...] = Field(default=(), max_length=64)
    source_url: str | None = Field(default=None, max_length=2048)
    source_connectors: tuple[str, ...] = Field(default=(), max_length=16)
    proposed_claim: str | None = Field(default=None, max_length=1200)
    scope: str | None = Field(default=None, max_length=600)
    contradictions: tuple[str, ...] = Field(default=(), max_length=16)
    unknowns: tuple[str, ...] = Field(default=(), max_length=16)
    blockers: tuple[ResearchProposalBlocker, ...] = ()
    safe_next_step: str = Field(min_length=1)
    recorded_at: datetime

    @model_validator(mode="after")
    def require_safe_state(self) -> Self:
        if self.subject_kind == "authoring_inventory_receipt" and not (
            self.authoring_inventory_receipt_id and self.authoring_inventory_receipt_digest
        ):
            raise ValueError("Observation research proposal requires inventory receipt lineage.")
        if self.status == "blocked" and not self.blockers:
            raise ValueError("Blocked research proposal requires typed blockers.")
        if self.status == "ready_for_review":
            if self.blockers or self.observation_id is None or not self.evidence_ids:
                raise ValueError("Ready research proposal requires exact observation lineage.")
            if self.researcher_run_id is None or self.output_digest is None:
                raise ValueError("Ready research proposal requires researcher readback identity.")
        payload = self.model_dump(mode="json")
        proposal_id = payload.pop("proposal_id")
        proposal_digest = payload.pop("proposal_digest")
        attempt_id = payload.pop("attempt_id")
        payload.pop("recorded_at")
        expected_digest = canonical_json_digest(payload)
        if proposal_digest != expected_digest:
            raise ValueError("Research proposal digest does not match its payload.")
        if proposal_id != f"content_research_proposal_{expected_digest[:24]}":
            raise ValueError("Research proposal ID does not match its payload.")
        if attempt_id != f"content_research_attempt_{expected_digest[:24]}":
            raise ValueError("Research attempt ID does not match its payload.")
        return self


class ResearchProposalReadDiagnostic(BaseModel):
    """Sanitized metadata for a stored proposal that fails the current contract."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: Literal["research_proposal_legacy_unreadable"] = (
        "research_proposal_legacy_unreadable"
    )
    proposal_id: str | None = None
    acquisition_run_id: str | None = None
    stored_contract_version: Literal["content_research_proposal_attempt_v1"] | None = None
    source_url: str | None = None
    reason: str = Field(min_length=1)
    safe_next_step: str = Field(min_length=1)


class ResearchProposalReadResult(BaseModel):
    """One valid proposal or one sanitized legacy-read diagnostic."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    proposal: ContentResearchProposalAttempt | None = None
    diagnostic: ResearchProposalReadDiagnostic | None = None

    @model_validator(mode="after")
    def require_one_result(self) -> Self:
        if (self.proposal is None) == (self.diagnostic is None):
            raise ValueError("Proposal read result requires exactly one outcome.")
        return self


class ResearchProposalLegacyUnreadable(ValueError):
    """A stored legacy proposal is readable only as a typed blocker."""

    def __init__(self, diagnostic: ResearchProposalReadDiagnostic) -> None:
        super().__init__(diagnostic.reason)
        self.diagnostic = diagnostic


class ContentResearchProposalCurrentProjection(BaseModel):
    """Current server assessment over one immutable research proposal attempt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    response_type: Literal["content_research_proposal_current_projection"] = (
        "content_research_proposal_current_projection"
    )
    contract_version: Literal["content_research_proposal_current_projection_v1"] = (
        "content_research_proposal_current_projection_v1"
    )
    recorded_proposal: ContentResearchProposalAttempt
    proposal_id: str
    proposal_digest: str
    acquisition_run_id: str
    recorded_status: Literal["ready_for_review", "blocked"]
    assessed_at: datetime
    current_status: Literal["ready_for_review", "blocked"]
    current_blockers: tuple[ResearchProposalBlocker, ...] = ()
    current_safe_next_step: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_recorded_identity(self) -> Self:
        if (
            self.proposal_id != self.recorded_proposal.proposal_id
            or self.proposal_digest != self.recorded_proposal.proposal_digest
            or self.acquisition_run_id != self.recorded_proposal.acquisition_run_id
            or self.recorded_status != self.recorded_proposal.status
        ):
            raise ValueError("Research projection identity must match recorded proposal.")
        if self.assessed_at.tzinfo is None or self.assessed_at.utcoffset() is None:
            raise ValueError("Research projection assessment time must be timezone-aware.")
        if self.current_status == "blocked" and not self.current_blockers:
            raise ValueError("Blocked research projection requires typed blockers.")
        return self

    @property
    def status(self) -> Literal["ready_for_review", "blocked"]:
        return self.current_status

    @property
    def blockers(self) -> tuple[ResearchProposalBlocker, ...]:
        return self.current_blockers

    @property
    def safe_next_step(self) -> str:
        return self.current_safe_next_step

    def __getattr__(self, name: str) -> Any:
        recorded = self.__dict__.get("recorded_proposal")
        if recorded is not None:
            try:
                return getattr(recorded, name)
            except AttributeError:
                pass
        raise AttributeError(name)


class ResearcherPort(Protocol):
    def run_structured_turn(
        self, request: CodexAppServerStructuredTurnRequest
    ) -> CodexAppServerTurnResult: ...


class CodexAppServerResearcherAdapter:
    """Production port adapter; the caller still controls whether it is invoked."""

    def __init__(self, client: CodexAppServerClientProtocol | None = None) -> None:
        self._client = client or StdioCodexAppServerClient()

    def run_structured_turn(
        self, request: CodexAppServerStructuredTurnRequest
    ) -> CodexAppServerTurnResult:
        return self._client.run_structured_turn(request)


class ResearchProposalStore(Protocol):
    def get_research_proposal_by_input_digest(
        self, input_digest: str
    ) -> ContentResearchProposalAttempt | None: ...

    def save_research_proposal(
        self, proposal: ContentResearchProposalAttempt
    ) -> ContentResearchProposalAttempt: ...

    def get_research_proposal(
        self, proposal_id: str
    ) -> ContentResearchProposalAttempt | None: ...


ProjectionReader = Callable[[str], EvidenceAcquisitionCurrentProjection | None]
Clock = Callable[[], datetime]


class EvidenceResearchCoordinator:
    """Reload exact acquisition state, invoke only the structured researcher port."""

    def __init__(
        self,
        *,
        acquisition_reader: ProjectionReader,
        proposal_store: ResearchProposalStore,
        researcher: ResearcherPort,
        clock: Clock | None = None,
    ) -> None:
        self._acquisition_reader = acquisition_reader
        self._proposal_store = proposal_store
        self._researcher = researcher
        self._clock = clock or (lambda: datetime.now(UTC))

    def start(self, acquisition_run_id: str) -> ContentResearchProposalCurrentProjection:
        projection = self._acquisition_reader(acquisition_run_id)
        if projection is None:
            return self._persist_blocked(
                acquisition_run_id=acquisition_run_id,
                acquisition_run=None,
                blocker=ResearchProposalBlocker(
                    code="acquisition_run_missing",
                    reason="Exact acquisition run was not found.",
                    safe_next_step="Uruchom exact current-page acquisition ponownie.",
                ),
            )
        run = projection.recorded_run
        input_digest = _input_digest(run)
        existing = self._proposal_store.get_research_proposal_by_input_digest(input_digest)
        if existing is not None:
            return self._project_proposal(existing)
        if run.observation is not None and not _observation_is_fresh(
            run.observation, now=self._clock()
        ):
            return self._persist_blocked(
                acquisition_run_id=acquisition_run_id,
                acquisition_run=run,
                input_digest=input_digest,
                blocker=ResearchProposalBlocker(
                    code="current_page_snapshot_stale",
                    reason="The acquisition observation is stale at researcher consumption time.",
                    safe_next_step="Zwiększ attempt i wykonaj nowy exact current-page read.",
                ),
            )
        if projection.current_status != "ready_for_researcher" or run.observation is None:
            blocker = _acquisition_blocker(projection)
            return self._persist_blocked(
                acquisition_run_id=acquisition_run_id,
                acquisition_run=run,
                input_digest=input_digest,
                blocker=blocker,
            )
        request, prompt_digest, schema_digest = _research_request(run, run.observation)
        result = self._researcher.run_structured_turn(request)
        if result.status != "completed" or not result.output_text or result.external_call_attempted:
            return self._persist_blocked(
                acquisition_run_id=acquisition_run_id,
                acquisition_run=run,
                input_digest=input_digest,
                prompt_digest=prompt_digest,
                schema_digest=schema_digest,
                result=result,
                blocker=ResearchProposalBlocker(
                    code=(
                        "researcher_external_call_blocked"
                        if result.external_call_attempted
                        else "researcher_executor_failed"
                    ),
                    reason="Structured researcher did not return a safe completed result.",
                    safe_next_step="Sprawdź lokalny researcher runtime i uruchom nowy attempt.",
                ),
            )
        try:
            output = ResearcherStructuredOutput.model_validate_json(
                result.output_text, strict=True
            )
        except ValueError:
            return self._persist_blocked(
                acquisition_run_id=acquisition_run_id,
                acquisition_run=run,
                    input_digest=input_digest,
                    prompt_digest=prompt_digest,
                    schema_digest=schema_digest,
                    result=result,
                    output_digest=sha256(result.output_text.encode("utf-8")).hexdigest(),
                blocker=ResearchProposalBlocker(
                    code="research_output_invalid",
                    reason="Researcher output did not match the proposal-only schema.",
                    safe_next_step="Uruchom nowy researcher attempt po sprawdzeniu schematu.",
                ),
            )
        output = _normalize_research_output(output)
        output_digest = canonical_json_digest(output.model_dump(mode="json"))
        output_blocker = _output_blocker(
            output,
            run.observation,
            candidate=(
                resolve_official_guidance_candidate(run.official_guidance_candidate_id)
                if run.source_intent == "official_primary"
                and run.official_guidance_candidate_id is not None
                else None
            ),
        )
        if output_blocker is not None:
            return self._persist_blocked(
                acquisition_run_id=acquisition_run_id,
                acquisition_run=run,
                input_digest=input_digest,
                prompt_digest=prompt_digest,
                schema_digest=schema_digest,
                result=result,
                output_digest=output_digest,
                blocker=output_blocker,
            )
        if result.turn_id is None:
            return self._persist_blocked(
                acquisition_run_id=acquisition_run_id,
                acquisition_run=run,
                input_digest=input_digest,
                prompt_digest=prompt_digest,
                schema_digest=schema_digest,
                result=result,
                output_digest=output_digest,
                blocker=ResearchProposalBlocker(
                    code="researcher_identity_missing",
                    reason="Structured researcher returned no server run identity.",
                    safe_next_step="Uruchom nowy researcher attempt z pełnym turn identity.",
                ),
            )
        proposal = _ready_proposal(
            run,
            run.observation,
            output,
            input_digest=input_digest,
            prompt_digest=prompt_digest,
            schema_digest=schema_digest,
            output_digest=output_digest,
            researcher_run_id=result.turn_id,
            recorded_at=self._clock(),
        )
        return self._project_proposal(self._proposal_store.save_research_proposal(proposal))

    def read(self, proposal_id: str) -> ContentResearchProposalCurrentProjection | None:
        proposal = self._proposal_store.get_research_proposal(proposal_id)
        return None if proposal is None else self._project_proposal(proposal)

    def _project_proposal(
        self, proposal: ContentResearchProposalAttempt
    ) -> ContentResearchProposalCurrentProjection:
        assessed_at = self._clock()
        current_status: Literal["ready_for_review", "blocked"] = proposal.status
        current_blockers = proposal.blockers
        current_safe_next_step = proposal.safe_next_step
        projection = self._acquisition_reader(proposal.acquisition_run_id)
        if proposal.status == "ready_for_review":
            if projection is None:
                current_status = "blocked"
                missing = ResearchProposalBlocker(
                    code="acquisition_run_missing",
                    reason="The acquisition run for this proposal is no longer available.",
                    safe_next_step="Uzyskaj nowy exact current-page acquisition.",
                )
                current_blockers = (missing,)
                current_safe_next_step = missing.safe_next_step
            elif (
                projection.recorded_run.observation is None
                or not _observation_is_fresh(
                    projection.recorded_run.observation, now=assessed_at
                )
                or projection.current_status != "ready_for_researcher"
            ):
                current_status = "blocked"
                stale = ResearchProposalBlocker(
                    code="current_page_snapshot_stale",
                    reason="The acquisition observation is not current for this proposal.",
                    safe_next_step="Zwiększ attempt i przygotuj nową propozycję.",
                )
                if projection.current_blockers and projection.freshness != "stale":
                    stale = ResearchProposalBlocker(
                        code=projection.current_blockers[0].code,
                        reason=projection.current_blockers[0].reason,
                        safe_next_step=projection.current_blockers[0].safe_next_step,
                    )
                current_blockers = (stale,)
                current_safe_next_step = stale.safe_next_step
        return ContentResearchProposalCurrentProjection(
            recorded_proposal=proposal,
            proposal_id=proposal.proposal_id,
            proposal_digest=proposal.proposal_digest,
            acquisition_run_id=proposal.acquisition_run_id,
            recorded_status=proposal.status,
            assessed_at=assessed_at,
            current_status=current_status,
            current_blockers=current_blockers,
            current_safe_next_step=current_safe_next_step,
        )

    def _persist_blocked(
        self,
        *,
        acquisition_run_id: str,
        acquisition_run: EvidenceAcquisitionRun | None,
        blocker: ResearchProposalBlocker,
        input_digest: str | None = None,
        prompt_digest: str | None = None,
        schema_digest: str | None = None,
        result: CodexAppServerTurnResult | None = None,
        output_digest: str | None = None,
    ) -> ContentResearchProposalCurrentProjection:
        input_digest = input_digest or canonical_json_digest(
            {"acquisition_run_id": acquisition_run_id, "state": "missing"}
        )
        prompt_digest = prompt_digest or _empty_digest("prompt")
        schema_digest = schema_digest or _empty_digest("schema")
        proposal = _blocked_proposal(
            acquisition_run_id=acquisition_run_id,
            acquisition_run=acquisition_run,
            input_digest=input_digest,
            prompt_digest=prompt_digest,
            schema_digest=schema_digest,
            output_digest=output_digest,
            researcher_run_id=None if result is None else result.turn_id,
            blocker=blocker,
            recorded_at=self._clock(),
        )
        return self._project_proposal(self._proposal_store.save_research_proposal(proposal))


def research_output_schema(
    *,
    allowed_claims: Sequence[str] | None = None,
    blocked_claims: Sequence[str] | None = None,
    scope_label: str | None = None,
) -> dict[str, object]:
    proposed_claim: dict[str, object] = {
        "type": ["string", "null"],
        "maxLength": 1200,
    }
    if allowed_claims is not None:
        proposed_claim["enum"] = [None, *allowed_claims]
    scope: dict[str, object] = {"type": ["string", "null"], "maxLength": 600}
    if scope_label is not None:
        scope["enum"] = [scope_label]
    schema: dict[str, object] = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "proposed_claim": proposed_claim,
            "scope": scope,
            "observation_ids": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
            "contradictions": {"type": "array", "items": {"type": "string"}, "maxItems": 16},
            "unknowns": {"type": "array", "items": {"type": "string"}, "maxItems": 16},
        },
        "required": [
            "proposed_claim",
            "scope",
            "observation_ids",
            "contradictions",
            "unknowns",
        ],
    }
    if blocked_claims is not None:
        schema["x_blocked_claims"] = list(blocked_claims)
    return schema


def _observation_is_fresh(
    observation: EvidenceObservationReceipt | OfficialGuidanceObservationReceipt,
    *,
    now: datetime,
) -> bool:
    if isinstance(observation, OfficialGuidanceObservationReceipt):
        return official_guidance_receipt_is_fresh(observation, now=now)
    return current_page_receipt_is_fresh(observation, now=now)


def _research_request(
    run: EvidenceAcquisitionRun,
    observation: EvidenceObservationReceipt | OfficialGuidanceObservationReceipt,
) -> tuple[CodexAppServerStructuredTurnRequest, str, str]:
    candidate = (
        resolve_official_guidance_candidate(run.official_guidance_candidate_id)
        if run.source_intent == "official_primary"
        and run.official_guidance_candidate_id is not None
        else None
    )
    schema = research_output_schema(
        allowed_claims=None if candidate is None else candidate.allowed_claim_scope,
        blocked_claims=None if candidate is None else candidate.blocked_claims,
        scope_label=None if candidate is None else candidate.title,
    )
    context_payload: dict[str, object] = {
        "operation": "propose_evidence_bound_research_claim",
        "research_question": run.research_question_safe,
        "allowed_observation_ids": [observation.observation_id],
        "invariants": {
            "do_not_invent_facts": True,
            "do_not_return_evidence_ids": True,
            "do_not_return_source_urls": True,
            "do_not_make_legal_claims_from_current_page": True,
            "proposal_only": True,
            "human_review_required": True,
        },
    }
    if candidate is not None:
        context_payload["official_guidance_candidate"] = {
            "candidate_id": candidate.candidate_id,
            "canonical_path": candidate.canonical_path,
            "source_url": candidate.source_url,
            "scope_label": candidate.title,
            "allowed_claim_scope": candidate.allowed_claim_scope,
            "blocked_claims": candidate.blocked_claims,
        }
    application_context = json.dumps(
        context_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    untrusted_context = json.dumps(
        {"sanitized_excerpt": observation.sanitized_excerpt},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    instruction = (
        "Przygotuj wyłącznie propozycję do review na podstawie przekazanego, "
        "niezaufanego excerptu. Zwróć tylko schema JSON. Nie dopisuj faktów, "
        "dowodów, URL-i, connectorów, digestów ani aprobaty. Każdy claim musi "
        "wskazywać observation_id z trusted context; jeśli materiał nie wystarcza, "
        "zwróć claim null i opisz unknowns. Nie formułuj twierdzeń prawnych."
    )
    if candidate is not None:
        instruction += (
            " Dla official guidance pole proposed_claim może być wyłącznie jednym "
            "z dokładnych stringów allowed_claim_scope albo null. Dokładny zakres "
            "allowed_claim_scope to "
            f"{json.dumps(candidate.allowed_claim_scope, ensure_ascii=False)}. "
            "Pole scope może być wyłącznie exact server-owned scope_label: "
            f"{candidate.title!r}. "
            "Zablokowane są następujące zakresy: "
            f"{json.dumps(candidate.blocked_claims, ensure_ascii=False)}. Nie używaj "
            "certyfikacji, gwarancji zgodności z prawem, gwarancji zgodności "
            "środowiskowej ani treści zakupionej normy."
        )
    request = CodexAppServerStructuredTurnRequest(
        instruction=instruction,
        application_context=application_context,
        untrusted_context=untrusted_context,
        output_schema=schema,
    )
    prompt_digest = canonical_json_digest(
        {
            "instruction": instruction,
            "application_context": application_context,
            "untrusted_context": untrusted_context,
        }
    )
    schema_digest = canonical_json_digest(schema)
    return request, prompt_digest, schema_digest


def _input_digest(run: EvidenceAcquisitionRun) -> str:
    observation = run.observation
    return canonical_json_digest(
        {
            "acquisition_run_digest": run.run_digest,
            "acquisition_run_id": run.run_id,
            "subject_kind": run.subject_kind,
            "authoring_inventory_receipt_id": run.authoring_inventory_receipt_id,
            "authoring_inventory_receipt_digest": run.authoring_inventory_receipt_digest,
            "observation_id": None if observation is None else observation.observation_id,
            "observation_digest": (
                None if observation is None else observation.source_snapshot_digest
            ),
            "question_digest": run.question_digest,
        }
    )


def _acquisition_blocker(
    projection: EvidenceAcquisitionCurrentProjection,
) -> ResearchProposalBlocker:
    if projection.current_blockers:
        blocker = projection.current_blockers[0]
        return ResearchProposalBlocker(
            code=blocker.code,
            reason=blocker.reason,
            safe_next_step=blocker.safe_next_step,
        )
    return ResearchProposalBlocker(
        code="acquisition_not_ready",
        reason="Current acquisition run is not ready for researcher use.",
        safe_next_step="Uzyskaj świeży exact current-page observation.",
    )


def _normalize_research_output(output: ResearcherStructuredOutput) -> ResearcherStructuredOutput:
    return ResearcherStructuredOutput(
        proposed_claim=_normalize_output_text(output.proposed_claim),
        scope=_normalize_output_text(output.scope),
        observation_ids=_normalize_output_tuple(output.observation_ids),
        contradictions=_normalize_output_tuple(output.contradictions),
        unknowns=_normalize_output_tuple(output.unknowns),
    )


def _normalize_output_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = unicodedata.normalize("NFKC", value)
    normalized = " ".join(normalized.split())
    return normalized or None


def _normalize_output_tuple(values: Sequence[str]) -> tuple[str, ...]:
    normalized = [_normalize_output_text(value) for value in values]
    return tuple(value for value in normalized if value)


def _comparison_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    folded = without_marks.casefold()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", folded).split())


def _contains_secret(value: str) -> bool:
    return bool(
        _SECRET_FIELD_RE.search(value)
        or _SECRET_VARIANT_RE.search(value)
        or SECRET_VALUE_RE.search(value)
    )


def _output_blocker(
    output: ResearcherStructuredOutput,
    observation: EvidenceObservationReceipt | OfficialGuidanceObservationReceipt,
    *,
    candidate: OfficialGuidanceCandidate | None = None,
) -> ResearchProposalBlocker | None:
    values = [
        value
        for value in (
            output.proposed_claim,
            output.scope,
            *output.contradictions,
            *output.unknowns,
        )
        if value
    ]
    if any(_contains_secret(value) for value in values):
        return ResearchProposalBlocker(
            code="researcher_unsafe_output",
            reason="Researcher output contains secret-like text and was discarded.",
            safe_next_step="Uruchom researcher ponownie z bezpiecznym, krótkim excerptem.",
        )
    normalized_excerpt = _comparison_text(observation.sanitized_excerpt)
    if normalized_excerpt and any(
        normalized_excerpt in _comparison_text(value) for value in values
    ):
        return ResearchProposalBlocker(
            code="researcher_excerpt_reproduction",
            reason="Researcher output repeated the full supplied excerpt.",
            safe_next_step="Uruchom researcher ponownie bez powtarzania materiału źródłowego.",
        )
    if output.proposed_claim and not output.observation_ids:
        return ResearchProposalBlocker(
            code="research_model_only_claim",
            reason="A proposed claim has no referenced persisted observation.",
            safe_next_step="Zwróć claim wyłącznie z exact observation_id albo pozostaw claim null.",
        )
    if any(value not in {observation.observation_id} for value in output.observation_ids):
        return ResearchProposalBlocker(
            code="research_observation_unknown",
            reason="Researcher referenced an observation outside the acquisition run.",
            safe_next_step="Użyj wyłącznie observation_id z bieżącego acquisition run.",
        )
    if candidate is not None:
        normalized_claim = _normalize_output_text(output.proposed_claim)
        allowed_claims = tuple(
            _normalize_output_text(item) for item in candidate.allowed_claim_scope
        )
        if normalized_claim is not None and normalized_claim not in allowed_claims:
            return ResearchProposalBlocker(
                code="official_guidance_scope_exceeded",
                reason=(
                    "Official-guidance proposed_claim must exactly match one "
                    "server-owned allowed_claim_scope string."
                ),
                safe_next_step=(
                    "Wybierz jeden exact allowed_claim_scope string albo pozostaw "
                    "proposed_claim null."
                ),
            )
        normalized_scope = _normalize_output_text(output.scope)
        if normalized_scope != _normalize_output_text(candidate.title):
            return ResearchProposalBlocker(
                code="official_guidance_scope_exceeded",
                reason=(
                    "Official-guidance scope must exactly match the candidate "
                    "server-owned scope label."
                ),
                safe_next_step=(
                    "Użyj exact scope labelu kandydata."
                ),
            )
    legal_text = " ".join(
        value for value in (output.proposed_claim, output.scope) if value
    )
    if candidate is None and _LEGAL_CLAIM_RE.search(_comparison_text(legal_text)):
        return ResearchProposalBlocker(
            code="legal_claim_requires_official_source",
            reason="Current-page observation cannot authorize a legal claim.",
            safe_next_step="Pozyskaj official primary source przed legal review.",
        )
    return None


def _ready_proposal(
    run: EvidenceAcquisitionRun,
    observation: EvidenceObservationReceipt | OfficialGuidanceObservationReceipt,
    output: ResearcherStructuredOutput,
    *,
    input_digest: str,
    prompt_digest: str,
    schema_digest: str,
    output_digest: str,
    researcher_run_id: str | None,
    recorded_at: datetime,
) -> ContentResearchProposalAttempt:
    payload: dict[str, Any] = {
        "subject_kind": run.subject_kind,
        "authoring_inventory_receipt_id": run.authoring_inventory_receipt_id,
        "authoring_inventory_receipt_digest": run.authoring_inventory_receipt_digest,
        "acquisition_run_id": run.run_id,
        "acquisition_run_digest": run.run_digest,
        "status": "ready_for_review",
        "approved": False,
        "review_required": True,
        "research_question_safe": run.research_question_safe,
        "model_id": _MODEL_ID,
        "researcher_run_id": researcher_run_id,
        "input_digest": input_digest,
        "prompt_digest": prompt_digest,
        "schema_digest": schema_digest,
        "output_digest": output_digest,
        "observation_id": observation.observation_id,
        "evidence_ids": observation.evidence_ids,
        "source_url": observation.source_url,
        "source_connectors": observation.source_connectors,
        "proposed_claim": _safe_value(output.proposed_claim),
        "scope": _safe_value(output.scope),
        "contradictions": _safe_values(output.contradictions),
        "unknowns": _safe_values(output.unknowns),
        "blockers": (),
        "safe_next_step": "Przekaż propozycję do osobnego human review; approval pozostaje false.",
        "recorded_at": recorded_at,
    }
    return _finalize_proposal(payload)


def _blocked_proposal(
    *,
    acquisition_run_id: str,
    acquisition_run: EvidenceAcquisitionRun | None,
    input_digest: str,
    prompt_digest: str,
    schema_digest: str,
    output_digest: str | None,
    researcher_run_id: str | None,
    blocker: ResearchProposalBlocker,
    recorded_at: datetime,
) -> ContentResearchProposalAttempt:
    payload: dict[str, Any] = {
        "subject_kind": (
            "identity_binding" if acquisition_run is None else acquisition_run.subject_kind
        ),
        "authoring_inventory_receipt_id": (
            None
            if acquisition_run is None
            else acquisition_run.authoring_inventory_receipt_id
        ),
        "authoring_inventory_receipt_digest": (
            None
            if acquisition_run is None
            else acquisition_run.authoring_inventory_receipt_digest
        ),
        "acquisition_run_id": acquisition_run_id,
        "acquisition_run_digest": None if acquisition_run is None else acquisition_run.run_digest,
        "status": "blocked",
        "approved": False,
        "review_required": True,
        "research_question_safe": (
            None if acquisition_run is None else acquisition_run.research_question_safe
        ),
        "model_id": _MODEL_ID,
        "researcher_run_id": researcher_run_id,
        "input_digest": input_digest,
        "prompt_digest": prompt_digest,
        "schema_digest": schema_digest,
        "output_digest": output_digest,
        "observation_id": None,
        "evidence_ids": (),
        "source_url": None,
        "source_connectors": (),
        "proposed_claim": None,
        "scope": None,
        "contradictions": (),
        "unknowns": (),
        "blockers": (blocker,),
        "safe_next_step": blocker.safe_next_step,
        "recorded_at": recorded_at,
    }
    return _finalize_proposal(payload)


def _finalize_proposal(payload: dict[str, Any]) -> ContentResearchProposalAttempt:
    full_payload = {
        "response_type": "content_research_proposal_attempt",
        "contract_version": "content_research_proposal_attempt_v2",
        **payload,
    }
    digest_payload = _json_value(full_payload)
    digest_payload.pop("recorded_at", None)
    digest = canonical_json_digest(digest_payload)
    return ContentResearchProposalAttempt.model_validate(
        full_payload
        | {
            "proposal_id": f"content_research_proposal_{digest[:24]}",
            "proposal_digest": digest,
            "attempt_id": f"content_research_attempt_{digest[:24]}",
        }
    )


def _json_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    return value


def _safe_value(value: str | None) -> str | None:
    if value is None:
        return None
    return _safe_text(value, limit=1200)


def _safe_values(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(_safe_text(value, limit=1200) for value in values)


def _safe_text(value: str, *, limit: int) -> str:
    return " ".join(value.strip().split())[:limit]


def _empty_digest(kind: str) -> str:
    return canonical_json_digest({"kind": kind, "version": 1})


def build_default_evidence_research_coordinator() -> EvidenceResearchCoordinator:
    from wilq.content.workflow.evidence_acquisition_coordinator import (
        build_default_evidence_acquisition_coordinator,
    )
    from wilq.content.workflow.store.store import content_workflow_store

    store = content_workflow_store()
    return EvidenceResearchCoordinator(
        acquisition_reader=build_default_evidence_acquisition_coordinator().read,
        proposal_store=store,
        researcher=CodexAppServerResearcherAdapter(),
    )


__all__ = [
    "CodexAppServerResearcherAdapter",
    "ContentResearchProposalCurrentProjection",
    "ContentResearchProposalAttempt",
    "EvidenceResearchCoordinator",
    "ResearchProposalLegacyUnreadable",
    "ResearchProposalReadDiagnostic",
    "ResearchProposalReadResult",
    "build_default_evidence_research_coordinator",
    "ResearchProposalBlocker",
    "ResearchProposalStore",
    "ResearcherStructuredOutput",
    "research_output_schema",
]
