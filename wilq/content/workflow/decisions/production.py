from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

Classification = Literal["reuse", "refresh", "write", "blocked"]
ClassificationSource = Literal["matched", "unmatched"]
ClassificationLookupBasis = Literal["current", "retained", "historical_action_owner"]

_HEX64 = r"^[0-9a-f]{64}$"
_HEX40 = r"^[0-9a-f]{40}$"
_CLASSIFIER_RETENTION = "external_ephemeral_receipt_only"


def _require_json_boolean(value: object) -> object:
    if type(value) is not bool:
        raise ValueError("Exact JSON boolean required.")
    return value


_ExactTrue = Annotated[Literal[True], BeforeValidator(_require_json_boolean)]
_ExactFalse = Annotated[Literal[False], BeforeValidator(_require_json_boolean)]


class ContentProductionClassificationValidationError(ValueError):
    """Fail-closed error that never includes signed input material."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"Production classification rejected: {code}.")


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ContentProductionClassificationCounts(_FrozenModel):
    rows: int = Field(ge=1)
    reuse: int = Field(ge=0)
    refresh: int = Field(ge=0)
    write: int = Field(ge=0)
    blocked: int = Field(ge=0)
    generation_allowed: int = Field(ge=0)
    verified_current_actions: int = Field(ge=0)
    verified_current_drafts: int = Field(ge=0)


class ContentProductionBlocker(_FrozenModel):
    code: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    next_step_pl: str = Field(min_length=1)
    sources: tuple[str, ...] = Field(min_length=1)
    blocks_initial_generation: _ExactTrue


class ContentProductionEvidenceDefect(_FrozenModel):
    evidence_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    reason_pl: str = Field(min_length=1)
    next_step_pl: str = Field(min_length=1)
    status: Literal["invalid_unusable"]
    usable_as_decision_proof: _ExactFalse


class ContentProductionRowReceipt(_FrozenModel):
    authoring_inventory_row_sha256: str = Field(pattern=_HEX64)
    canonical_ledger_row_sha256: str = Field(pattern=_HEX64)
    keep_eligibility_row_sha256: str = Field(pattern=_HEX64)
    state_journal_url_row_sha256: str = Field(pattern=_HEX64)
    classification_artifact_reference: str = Field(min_length=1)
    classification_file_sha256: str = Field(pattern=_HEX64)
    classification_row_sha256: str = Field(pattern=_HEX64)
    classification_source: ClassificationSource
    classification_raw_artifact_retained: _ExactFalse
    classification_retention_status: Literal["external_ephemeral_receipt_only"]
    source_pack_id: str = Field(min_length=1)
    bound_mutation_audit_row_sha256: tuple[str, ...] = ()
    draft_row_sha256: tuple[str, ...] = ()
    lineage_defects_sha256: str | None = Field(default=None, pattern=_HEX64)
    usable_canonical_ledger_evidence_ids_sha256: str | None = Field(default=None, pattern=_HEX64)


class ContentProductionRetainedBinding(_FrozenModel):
    binding_basis: Literal["exact_normalized_path_with_retained_revision_state"]
    current_inventory_work_item_id: str = Field(min_length=1)
    retained_work_item_id: str | None = None
    retained_revision_id: str = Field(min_length=1)
    retained_revision_digest: str = Field(pattern=_HEX64)
    identity_reconciliation_status: Literal["fork", "retained_missing"]
    verified_draft_action_ids: tuple[str, ...] = ()
    verified_draft_post_ids: tuple[str, ...] = ()
    must_not_regenerate: _ExactTrue


class ContentProductionVerifiedAction(_FrozenModel):
    action_id: str = Field(min_length=1)
    mutation_audit_id: str = Field(min_length=1)
    action_type: Literal["content_dev_draft_create"]
    status: Literal["applied"]
    bound_work_item_id: str = Field(min_length=1)
    bound_revision_id: str = Field(min_length=1)
    bound_content_digest: str = Field(pattern=_HEX64)
    bound_final_canonical_url: str = Field(min_length=1)
    adapter_reached: _ExactTrue
    external_write_attempted: _ExactTrue


class ContentProductionVerifiedDraft(_FrozenModel):
    action_id: str = Field(min_length=1)
    apply_audit_id: str = Field(min_length=1)
    post_id: str = Field(min_length=1)
    revision_id: str = Field(min_length=1)
    revision_digest: str = Field(pattern=_HEX64)
    readback_content_digest: str = Field(pattern=_HEX64)
    state_class: Literal["dev_draft_verified"]
    wordpress_draft_status: Literal["draft"]
    readback_status: Literal["verified", "verified_manual_adapter_readback"]


class ContentProductionClassificationRow(_FrozenModel):
    canonical_path: str = Field(min_length=1)
    public_url: str = Field(min_length=1)
    decision: Classification
    generation_allowed: _ExactFalse
    current_work_item_id: str | None = None
    retained_work_item_id: str | None = None
    revision_id: str | None = None
    revision_digest: str | None = Field(default=None, pattern=_HEX64)
    revision_approved: bool
    revision_complete: bool
    rationale_pl: str = Field(min_length=1)
    next_step_pl: str = Field(min_length=1)
    blockers: tuple[ContentProductionBlocker, ...] = ()
    retained_binding: ContentProductionRetainedBinding | None = None
    verified_actions: tuple[ContentProductionVerifiedAction, ...] = ()
    verified_drafts: tuple[ContentProductionVerifiedDraft, ...] = ()
    primary_evidence_ids: tuple[str, ...] = Field(min_length=1)
    source_connectors: tuple[str, ...] = Field(min_length=1)
    lineage_evidence_ids: tuple[str, ...] = ()
    lineage_defects: tuple[ContentProductionEvidenceDefect, ...] = ()
    source_receipt: ContentProductionRowReceipt
    source_packet_row_digest: str = Field(pattern=_HEX64)

    @model_validator(mode="after")
    def require_exact_revision_action_draft_binding(self) -> Self:
        binding = self.retained_binding
        if self.decision == "reuse":
            if not self.revision_approved or not self.revision_complete or binding is None:
                raise ValueError("Reuse classification requires an approved retained binding.")
        elif binding is not None or self.revision_approved:
            raise ValueError("Only reuse classification may retain an approved binding.")
        if binding is not None and (
            binding.current_inventory_work_item_id != self.current_work_item_id
            or binding.retained_work_item_id != self.retained_work_item_id
            or binding.retained_revision_id != self.revision_id
            or binding.retained_revision_digest != self.revision_digest
        ):
            raise ValueError("Retained revision binding does not match the row.")
        actions = {item.action_id: item for item in self.verified_actions}
        drafts = {item.action_id: item for item in self.verified_drafts}
        if (
            len(actions) != len(self.verified_actions)
            or len(drafts) != len(self.verified_drafts)
            or set(actions) != set(drafts)
        ):
            raise ValueError("Verified action and draft identities must pair exactly.")
        if binding is not None:
            action_owners = {item.bound_work_item_id for item in self.verified_actions}
            if binding.identity_reconciliation_status == "fork":
                if binding.retained_work_item_id is None or any(
                    owner != binding.retained_work_item_id for owner in action_owners
                ):
                    raise ValueError("Fork actions must bind to the retained work item.")
            elif binding.retained_work_item_id is not None or len(action_owners) > 1:
                raise ValueError("Retained-missing actions must share one historical owner.")
        for action_id, action in actions.items():
            draft = drafts[action_id]
            if (
                action.mutation_audit_id != draft.apply_audit_id
                or action.bound_revision_id != draft.revision_id
                or action.bound_content_digest != draft.revision_digest
                or action.bound_revision_id != self.revision_id
                or action.bound_content_digest != self.revision_digest
                or action.bound_final_canonical_url != self.public_url
            ):
                raise ValueError("Verified action and draft binding does not match the row.")
        if binding is not None and (
            binding.verified_draft_action_ids != tuple(actions)
            or binding.verified_draft_post_ids
            != tuple(item.post_id for item in self.verified_drafts)
        ):
            raise ValueError("Retained binding does not match verified action and draft IDs.")
        return self

    def protects_work_item(self, work_item_id: str) -> bool:
        return work_item_id in _classification_authority_ids(self)

    def lookup_basis_for_work_item(
        self,
        work_item_id: str,
    ) -> ClassificationLookupBasis | None:
        """Name the exact accepted identity that matched a selected workspace lookup."""

        if work_item_id == self.current_work_item_id:
            return "current"
        if work_item_id == self.retained_work_item_id:
            return "retained"
        if any(action.bound_work_item_id == work_item_id for action in self.verified_actions):
            return "historical_action_owner"
        return None

    @property
    def reusable_work_item_id(self) -> str | None:
        """Return only the exact owner from which a retained revision may be read."""

        binding = self.retained_binding
        if self.decision != "reuse" or binding is None:
            return None
        if binding.identity_reconciliation_status == "fork":
            return binding.retained_work_item_id
        historical_owners = tuple(
            dict.fromkeys(action.bound_work_item_id for action in self.verified_actions)
        )
        if len(historical_owners) != 1 or historical_owners[0] == self.current_work_item_id:
            return None
        return historical_owners[0]


class ContentProductionSourceReceipt(_FrozenModel):
    name: str = Field(min_length=1)
    reference: str = Field(min_length=1)
    sha256: str = Field(pattern=_HEX64)
    raw_artifact_retained: bool | None = None
    retention_status: str | None = None


class ContentProductionFreshness(_FrozenModel):
    state: str = Field(min_length=1)
    checked_at: str = Field(min_length=1)
    requires_refresh: bool
    connector_ids: tuple[str, ...]


class ContentProductionJudgeReceipt(_FrozenModel):
    schema_version: str = Field(min_length=1)
    sha256: str = Field(pattern=_HEX64)
    reviewer_role: str = Field(min_length=1)
    verdict: Literal["accept"]
    reviewed_packet_sha256: str = Field(pattern=_HEX64)
    reviewed_decision_set_digest: str = Field(pattern=_HEX64)
    generated_at: str = Field(min_length=1)


class ContentProductionInputReceipt(_FrozenModel):
    policy_id: str = Field(min_length=1)
    policy_digest: str = Field(pattern=_HEX64)
    packet_schema_version: str = Field(min_length=1)
    packet_sha256: str = Field(pattern=_HEX64)
    judge_sha256: str = Field(pattern=_HEX64)
    decision_set_digest: str = Field(pattern=_HEX64)
    base_revision: str = Field(pattern=_HEX40)
    packet_generated_at: str = Field(min_length=1)


class ContentProductionAudit(_FrozenModel):
    recorded_by: str = Field(min_length=1, max_length=160)
    reviewed_by: str = Field(min_length=1, max_length=160)
    recorded_at: datetime

    @field_validator("recorded_at")
    @classmethod
    def require_aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Classification audit time must be timezone-aware.")
        return value.astimezone(UTC)


class ContentProductionClassificationRun(_FrozenModel):
    schema_version: Literal["wilq_content_production_classification_run_v1"] = (
        "wilq_content_production_classification_run_v1"
    )
    run_id: str = Field(min_length=1)
    input_digest: str = Field(pattern=_HEX64)
    run_digest: str = Field(pattern=_HEX64)
    input: ContentProductionInputReceipt
    counts: ContentProductionClassificationCounts
    freshness: ContentProductionFreshness
    source_receipts: tuple[ContentProductionSourceReceipt, ...] = Field(min_length=1)
    judge_receipt: ContentProductionJudgeReceipt
    rows: tuple[ContentProductionClassificationRow, ...] = Field(min_length=1)
    audit: ContentProductionAudit

    @model_validator(mode="after")
    def require_coherent_aggregate(self) -> Self:
        paths = tuple(row.canonical_path for row in self.rows)
        if paths != tuple(sorted(paths)) or len(paths) != len(set(paths)):
            raise ValueError("Classification rows must have unique canonical order.")
        if self.counts != classification_counts(self.rows):
            raise ValueError("Classification counts must derive from rows.")
        if self.run_id != f"content_production_classification_{self.input.packet_sha256[:24]}":
            raise ValueError("Classification run ID does not match the packet.")
        if self.input_digest != canonical_json_digest(self.input.model_dump(mode="json")):
            raise ValueError("Classification input digest does not match its receipts.")
        if (
            self.judge_receipt.sha256 != self.input.judge_sha256
            or self.judge_receipt.reviewed_packet_sha256 != self.input.packet_sha256
            or self.judge_receipt.reviewed_decision_set_digest != self.input.decision_set_digest
        ):
            raise ValueError("Judge receipt is not bound to the classification input.")
        _validate_typed_uniqueness(self.rows)
        if self.run_digest != _classification_run_digest(self):
            raise ValueError("Classification run digest does not match the aggregate.")
        return self

    def for_work_item(self, work_item_id: str) -> ContentProductionClassificationRow | None:
        return next((row for row in self.rows if row.protects_work_item(work_item_id)), None)


class ContentProductionClassificationProjection(_FrozenModel):
    run_id: str = Field(min_length=1)
    run_digest: str = Field(pattern=_HEX64)
    decision_set_digest: str = Field(pattern=_HEX64)
    freshness: ContentProductionFreshness
    row: ContentProductionClassificationRow


class ContentProductionClassificationRecordResult(_FrozenModel):
    status: Literal["created", "idempotent", "conflict"]
    run: ContentProductionClassificationRun


class ContentProductionClassificationReadResult(_FrozenModel):
    status: Literal["available", "missing"]
    run: ContentProductionClassificationRun | None = None

    @model_validator(mode="after")
    def require_matching_state(self) -> Self:
        if (self.status == "available") != (self.run is not None):
            raise ValueError("Classification read state does not match its payload.")
        return self


class ContentProductionClassificationProjectionReadResult(_FrozenModel):
    status: Literal["available", "missing"]
    projection: ContentProductionClassificationProjection | None = None

    @model_validator(mode="after")
    def require_matching_state(self) -> Self:
        if (self.status == "available") != (self.projection is not None):
            raise ValueError("Classification projection state does not match its payload.")
        return self


class ContentProductionSourceReceiptPolicy(_FrozenModel):
    name: str = Field(min_length=1)
    reference: str = Field(min_length=1)
    sha256: str = Field(pattern=_HEX64)
    raw_artifact_retained: bool | None = None
    retention_status: str | None = None


class ContentProductionProtectedBindingPolicy(_FrozenModel):
    canonical_path: str = Field(min_length=1)
    current_work_item_id: str = Field(min_length=1)
    retained_work_item_id: str | None = None
    revision_id: str = Field(min_length=1)
    revision_digest: str = Field(pattern=_HEX64)
    action_ids: tuple[str, ...] = ()
    draft_post_ids: tuple[str, ...] = ()
    identity_status: Literal["fork", "retained_missing"]
    judge_identity_status: str = Field(min_length=1)


class ContentProductionEvidenceDefectPolicy(_FrozenModel):
    evidence_id: str = Field(min_length=1)
    blocker_code: str = Field(min_length=1)
    occurrence_count: int = Field(ge=1)


class ContentProductionAcceptancePolicy(_FrozenModel):
    policy_id: str = Field(min_length=1)
    packet_schema_version: str = Field(min_length=1)
    judge_schema_version: str = Field(min_length=1)
    judge_reviewer_role: str = Field(min_length=1)
    judge_protected_binding_check_name: str = Field(min_length=1)
    packet_sha256: str = Field(pattern=_HEX64)
    judge_sha256: str = Field(pattern=_HEX64)
    decision_set_digest: str = Field(pattern=_HEX64)
    base_revision: str = Field(pattern=_HEX40)
    canonical_paths: tuple[str, ...] = Field(min_length=1)
    expected_counts: ContentProductionClassificationCounts
    expected_approved_revisions: int = Field(ge=0)
    freshness_connector_ids: tuple[str, ...]
    source_receipts: tuple[ContentProductionSourceReceiptPolicy, ...] = Field(min_length=1)
    protected_binding: ContentProductionProtectedBindingPolicy
    invalid_evidence: ContentProductionEvidenceDefectPolicy
    public_origin: str = Field(min_length=1)
    primary_evidence_http_status: int = Field(ge=100, le=599)
    primary_evidence_metrics_asserted: bool

    @model_validator(mode="after")
    def require_canonical_policy(self) -> Self:
        if (
            self.canonical_paths != tuple(sorted(self.canonical_paths))
            or len(self.canonical_paths) != len(set(self.canonical_paths))
            or self.expected_counts.rows != len(self.canonical_paths)
        ):
            raise ValueError("Classification policy paths must be unique and sorted.")
        names = tuple(item.name for item in self.source_receipts)
        if len(names) != len(set(names)) or not {
            "matched_classification",
            "unmatched_classification",
        }.issubset(names):
            raise ValueError("Classification policy source receipts are incomplete.")
        if self.protected_binding.canonical_path not in self.canonical_paths:
            raise ValueError("Protected binding is outside the classification scope.")
        return self


def canonical_json_digest(value: object) -> str:
    return sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def classification_counts(
    rows: tuple[ContentProductionClassificationRow, ...],
) -> ContentProductionClassificationCounts:
    return ContentProductionClassificationCounts(
        rows=len(rows),
        reuse=sum(row.decision == "reuse" for row in rows),
        refresh=sum(row.decision == "refresh" for row in rows),
        write=sum(row.decision == "write" for row in rows),
        blocked=sum(row.decision == "blocked" for row in rows),
        generation_allowed=sum(row.generation_allowed for row in rows),
        verified_current_actions=sum(len(row.verified_actions) for row in rows),
        verified_current_drafts=sum(len(row.verified_drafts) for row in rows),
    )


def project_content_production_classification(
    run: ContentProductionClassificationRun,
    row: ContentProductionClassificationRow,
) -> ContentProductionClassificationProjection:
    return ContentProductionClassificationProjection(
        run_id=run.run_id,
        run_digest=run.run_digest,
        decision_set_digest=run.input.decision_set_digest,
        freshness=run.freshness,
        row=row,
    )


def parse_content_production_classification(
    *,
    packet_bytes: bytes,
    judge_bytes: bytes,
    acceptance_policy: ContentProductionAcceptancePolicy,
    recorded_by: str,
    reviewed_by: str,
    recorded_at: datetime,
) -> ContentProductionClassificationRun:
    """Turn exact signed bytes into the only persisted classification aggregate."""

    from wilq.content.workflow.decisions._production_parser import (
        parse_content_production_classification_impl,
    )

    return parse_content_production_classification_impl(
        packet_bytes=packet_bytes,
        judge_bytes=judge_bytes,
        acceptance_policy=acceptance_policy,
        recorded_by=recorded_by,
        reviewed_by=reviewed_by,
        recorded_at=recorded_at,
    )


def _build_run(
    *,
    input_receipt: ContentProductionInputReceipt,
    counts: ContentProductionClassificationCounts,
    freshness: ContentProductionFreshness,
    source_receipts: tuple[ContentProductionSourceReceipt, ...],
    judge_receipt: ContentProductionJudgeReceipt,
    rows: tuple[ContentProductionClassificationRow, ...],
    audit: ContentProductionAudit,
) -> ContentProductionClassificationRun:
    provisional = ContentProductionClassificationRun.model_construct(
        run_id=f"content_production_classification_{input_receipt.packet_sha256[:24]}",
        input_digest=canonical_json_digest(input_receipt.model_dump(mode="json")),
        run_digest="0" * 64,
        input=input_receipt,
        counts=counts,
        freshness=freshness,
        source_receipts=source_receipts,
        judge_receipt=judge_receipt,
        rows=rows,
        audit=audit,
    )
    return ContentProductionClassificationRun.model_validate(
        provisional.model_copy(update={"run_digest": _classification_run_digest(provisional)})
    )


def _classification_run_digest(run: ContentProductionClassificationRun) -> str:
    return canonical_json_digest(run.model_dump(mode="json", exclude={"audit", "run_digest"}))


def _classification_authority_ids(
    row: ContentProductionClassificationRow,
) -> tuple[str, ...]:
    return tuple(
        work_item_id
        for work_item_id in (
            row.current_work_item_id,
            row.retained_work_item_id,
            *(action.bound_work_item_id for action in row.verified_actions),
        )
        if work_item_id is not None
    )


def _validate_typed_uniqueness(
    rows: tuple[ContentProductionClassificationRow, ...],
) -> None:
    revision_ids = [row.revision_id for row in rows if row.revision_id]
    action_ids = [item.action_id for row in rows for item in row.verified_actions]
    post_ids = [item.post_id for row in rows for item in row.verified_drafts]
    if any(len(values) != len(set(values)) for values in (revision_ids, action_ids, post_ids)):
        raise ValueError("Current classification identities must be unique.")
    ownership: dict[str, str] = {}
    for row in rows:
        for work_item_id in _classification_authority_ids(row):
            prior = ownership.setdefault(work_item_id, row.canonical_path)
            if prior != row.canonical_path:
                raise ValueError("Work-item classification authority must be unique.")


WAVE0_CANONICAL_PATHS: tuple[str, ...] = (
    "/",
    "/3-kroki-do-bezpiecznego-funkcjonowania-przedsiebiorstwa-w-zgodzie-z-przepisami-w-obszarze-ochrony-srodowiska",
    "/analiza-pozwolen-zintegrowanych",
    "/badania-obecnosci-radonu",
    "/bdo-co-musi-wiedziec-przedsiebiorca",
    "/bilans-lzo-przekroczenie-standardow-emisyjnych-a-obowiazek-raportowy",
    "/czy-kazda-rozbudowa-zakladu-przemyslowego-wymaga-decyzji-srodowiskowej",
    "/czy-wiesz-ze-zgodnie-z-nowa-norma-iso-45001-masz-obowiazek-reagowac-na-sytuacje-awaryjne",
    "/czy-wysokosc-skladowiska-odpadow-liczy-sie-z-warstwa-rekultywacyjna",
    "/czym-jest-europejski-system-ekozarzadzania-i-audytu-emas",
    "/czym-jest-goz-i-jakie-sa-jego-zalozenia",
    "/czym-kierowac-sie-podczas-kupna-sorbentu-aby-dobrac-go-odpowiednio-do-naszych-potrzeb",
    "/czym-sa-historyczne-zanieczyszczenia-i-jakie-obowiazki-ma-wlasciciel-gruntu",
    "/diwass-od-2026-roku-co-zmienia-cyfrowy-system-transgranicznego-przemieszczania-odpadow",
    "/dlaczego-i-kiedy-nalezy-wykonac-ocene-stanu-jakosci-gleby-ziemi-i-wod-podziemnych",
    "/dlaczego-mowimy-o-compliance-czyli-zarzadzaniu-zgodnoscia",
    "/dlaczego-warto-skorzystac-z-uslug-specjalistow-ds-ochrony-srodowiska",
    "/dokumentacja-srodowiskowa-w-procesie-inwestycyjnym",
    "/europejski-zielony-lad-co-to-takiego",
    "/informacja-o-opakowaniach-i-odpadach-opakowaniowych-oraz-o-oplacie-produktowej",
    "/jak-dobrac-sorbent-do-twojej-branzy-praktyczny-przewodnik-z-produktami",
    "/jak-postepowac-z-olejami-odpadowymi",
    "/kip-w-praktyce-inwestycyjnej-najczestsze-bledy-i-ich-konsekwencje",
    "/kompetencje-przyszlosci-w-ochronie-srodowiska-dlaczego-warto-inwestowac-w-szkolenia",
    "/kontakt",
    "/na-jakie-wymogi-prawne-zwiazane-ze-srodowiskiem-przygotowac-sie-w-2026",
    "/nagroda-eko-innowator-2024-dla-ekologus",
    "/nota-prawna",
    "/nowe-inwestycje-w-przedsiebiorstwie-brak-wspolpracy-sluzb-ds-rozwoju-ze-sluzbami-ochrony-srodowiska",
    "/o-firmie",
    "/o-firmie/kariera",
    "/obowiazki-pomiarowe-instalacji-wymagajacej-pozwolenia-zintegrowanego-tzw-instalacji-ippc-emisje-pylow-i-gazow-halas-oraz-badania-gleby-ziemi-i-wod-gruntowych",
    "/obowiazki-przedsiebiorstw-w-zakresie-rozporzadzenia-reach-i-clp-ze-szczegolnym-uwzglednieniem-zmian-w-kartach-charakterystyki",
    "/ocena-wplywu-projektow-na-srodowisko",
    "/odpowiedzialnosc-prawna-pracodawcy-za-bhp-i-ochrone-srodowiska",
    "/oferta/audyty-systemow-zarzadzania",
    "/oferta/bhp-i-p-poz",
    "/oferta/doradztwo-i-outsourcing-ekologiczny",
    "/oferta/opracowania-dokumentacji-ekspertyz",
    "/oferta/pomiary-i-analizy",
    "/oferta/rekultywacje-i-remediacje",
    "/oferta/szkolenia",
    "/operat-wodnoprawny-wszystko-co-musisz-wiedziec",
    "/outsourcing-srodowiskowy-elastyczne-rozwiazanie-dla-twojej-firmy",
    "/planowanie-i-zarzadzanie-strategiczne-latwiej-zaplanowac-trudniej-wdrozyc",
    "/planujesz-nowa-inwestycje-produkcyjna-sprawdz-srodowisko-i-inne-wymagania-zanim-zlecisz-projekt-budowlany",
    "/podsumowanie-webinaru-dlaczego-warto-poukladac-procesy-oraz-kwestie-srodowiskowe-w-swojej-firmie",
    "/pozwolenie-zintegrowane-wymagania-i-procedury-ippc",
    "/proces-inwestycyjny-w-przedsiewzieciu-budowlanym",
    "/raport-poczatkowy-i-raport-koncowy",
    "/remediacja-czym-jest-na-czym-polega-kiedy-jest-wymagana",
    "/rewolucja-w-decyzjach-o-warunkach-zabudowy-co-zmienia-sie-od-2026",
    "/roczne-sprawozdanie-w-bdo-co-sprawdzic-przed-31-grudnia-aby-nie-narazic-sie-na-kary",
    "/rozbudowa-zakladu-a-koniecznosc-uzyskania-decyzji-srodowiskowej",
    "/sorbenty-czym-sa-jak-dzialaja-i-dlaczego-warto-je-stosowac",
    "/uzasadnienie-celowosci-sporzadzania-rachunku-kosztow-srodowiskowych-w-przedsiebiorstwach-przemyslowych",
    "/zamkniecie-roku-w-ochronie-srodowiska-jak-uporzadkowac-obowiazki-i-wejsc-spokojnie-w-nowy-rok",
)

_WAVE0_SOURCES = (
    (
        "authoring_inventory",
        "docs/content-dev-authoring-inventory-20260828.json",
        "9737b6a309d13e40c662f943892849ee6c14419e1c04f3c416ad4032db01b245",  # pragma: allowlist secret  # noqa: E501
        None,
    ),
    (
        "canonical_ledger",
        "docs/content-canonical-ledger-20260828.jsonl",
        "d57cbdd989c9970a597563c16fc100869ce93f5bd0dc56234d50e7875facbab2",  # pragma: allowlist secret  # noqa: E501
        None,
    ),
    (
        "keep_eligibility",
        "docs/content-keep-eligibility-20260828.json",
        "cbcd7701cddf14204dfb8db7651655fa09e115cec2f1565b73ec350e2ac0ae3e",  # pragma: allowlist secret  # noqa: E501
        None,
    ),
    (
        "matched_classification",
        "wave0-matched-classification.json",
        "2eeecc84c310937aa1bdedd4c55c6916d6e4d44867867c99315212566305453b",  # pragma: allowlist secret  # noqa: E501
        False,
    ),
    (
        "state_journal",
        "docs/content-dev-state-journal-20260828.json",
        "53700d90d3cb78f89fd6e214664781303ecb53756f856dc259559a1c1fdaa0d6",  # pragma: allowlist secret  # noqa: E501
        None,
    ),
    (
        "unmatched_classification",
        "wave0-unmatched-classification.json",
        "29ec53efcd0398b88d7978884951c69d052f2e9c04906aa5af6d379786b4f1fe",  # pragma: allowlist secret  # noqa: E501
        False,
    ),
    (
        "wilq_content_diagnostics",
        "wave0-production-diagnostics.json",
        "0702b73dc75b8ef2863aec3c6142c0ddc5aa8d0099256d275890fb73a92d931c",  # pragma: allowlist secret  # noqa: E501
        False,
    ),
)

WAVE0_PRODUCTION_ACCEPTANCE_POLICY = ContentProductionAcceptancePolicy(
    policy_id="content_production_wave0_keep_packet_v1",
    packet_schema_version="wilq_content_production_classification_v1",
    judge_schema_version="wave0_production_classification_judge_v1",
    judge_reviewer_role="independent_packet_integrity_judge",
    judge_protected_binding_check_name="bdo",
    packet_sha256="3f5f58185e5c6b463136a5102ff61923a6e52582624ada09aa6d6e73ce3cf2a0",  # pragma: allowlist secret  # noqa: E501
    judge_sha256="1b0cac5553846ae30dca5b74957feb92707990291cdd821a7e60a79fdc1c1697",  # pragma: allowlist secret  # noqa: E501
    decision_set_digest="3c30e26305584d832b2940baf2585267fd5ade2ad9a12265958172e43ba27ecf",  # pragma: allowlist secret  # noqa: E501
    base_revision="fa36f7441ca5b3c6ee1cc89ce81073f36bf9d6ee",  # pragma: allowlist secret
    canonical_paths=WAVE0_CANONICAL_PATHS,
    expected_counts=ContentProductionClassificationCounts(
        rows=57,
        reuse=13,
        refresh=19,
        write=0,
        blocked=25,
        generation_allowed=0,
        verified_current_actions=8,
        verified_current_drafts=8,
    ),
    expected_approved_revisions=13,
    freshness_connector_ids=(
        "ahrefs",
        "google_analytics_4",
        "google_search_console",
        "wordpress_ekologus",
    ),
    source_receipts=tuple(
        ContentProductionSourceReceiptPolicy(
            name=name,
            reference=reference,
            sha256=digest,
            raw_artifact_retained=retained,
            retention_status=_CLASSIFIER_RETENTION if retained is False else None,
        )
        for name, reference, digest, retained in _WAVE0_SOURCES
    ),
    protected_binding=ContentProductionProtectedBindingPolicy(
        canonical_path="/bdo-co-musi-wiedziec-przedsiebiorca",
        current_work_item_id="content_work_item_inventory_5391632ca65d5e8714952a84",
        retained_work_item_id=(
            "content_work_item_content_decision_https___www_ekologus_pl_"
            "bdo_co_musi_wiedziec_przedsiebiorca"
        ),
        revision_id="content_revision_52d07d4011c04168842c87aeb26785a1",
        revision_digest="a8f02b1b0223651e105ced3c7e38e506d77f7f8a543b6f5ccbda99f93874b6f8",  # pragma: allowlist secret  # noqa: E501
        action_ids=("act_content_dev_draft_5a81402fb4b54897a8aee88832060a15",),
        draft_post_ids=("1991",),
        identity_status="fork",
        judge_identity_status="fork_explicitly_unresolved",
    ),
    invalid_evidence=ContentProductionEvidenceDefectPolicy(
        evidence_id="ev_regulatory_source_review_",
        blocker_code="invalid_legacy_evidence_id",
        occurrence_count=1,
    ),
    public_origin="https://www.ekologus.pl",
    primary_evidence_http_status=200,
    primary_evidence_metrics_asserted=False,
)


__all__ = [
    "ClassificationLookupBasis",
    "ContentProductionAcceptancePolicy",
    "ContentProductionAudit",
    "ContentProductionBlocker",
    "ContentProductionClassificationCounts",
    "ContentProductionClassificationProjection",
    "ContentProductionClassificationProjectionReadResult",
    "ContentProductionClassificationReadResult",
    "ContentProductionClassificationRecordResult",
    "ContentProductionClassificationRow",
    "ContentProductionClassificationRun",
    "ContentProductionClassificationValidationError",
    "ContentProductionEvidenceDefectPolicy",
    "ContentProductionProtectedBindingPolicy",
    "ContentProductionSourceReceiptPolicy",
    "WAVE0_CANONICAL_PATHS",
    "WAVE0_PRODUCTION_ACCEPTANCE_POLICY",
    "canonical_json_digest",
    "parse_content_production_classification",
    "project_content_production_classification",
]
