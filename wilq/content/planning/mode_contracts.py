from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.workflow.target.public_to_dev_mapping import ContentPublicToDevMapping

ContentPlanningMode = Literal[
    "refresh_existing",
    "new_page",
    "create",
    "migration",
    "structure",
    "no_change",
    "defer",
]
ContentPlanningContinuationMode = Literal[
    "refresh_existing",
    "new_page",
    "create",
    "migration",
]
ContentPlanningTerminalMode = Literal["no_change", "defer"]
ContentPlanningModeRoutingStatus = Literal["existing_flow", "contract_only"]
ContentPlanningModeBlockerCode = Literal[
    "create_public_source_conflict",
    "missing_create_foundation_identity",
    "missing_create_ia_identity",
    "missing_create_service_identity",
    "missing_migration_public_source",
    "missing_migration_target_identity",
    "missing_new_page_foundation_identity",
    "missing_new_page_ia_identity",
    "missing_new_page_service_identity",
    "missing_refresh_public_canonical",
    "migration_target_not_exact",
    "migration_target_source_mismatch",
    "new_page_public_source_conflict",
    "refresh_foundation_conflict",
    "structure_requires_human_decision",
    "unsupported_mode",
]


class ContentPlanningModeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    requested_mode: str
    service_card_id: str | None = None
    public_canonical_url: str | None = None
    planning_foundation_id: str | None = None
    proposed_ia_location: str | None = None
    migration_target: ContentPublicToDevMapping | None = None


class ContentPlanningModeBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ContentPlanningModeBlockerCode
    label: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    next_step: str = Field(min_length=1)


class ContentPlanningModeAllowedPath(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["allowed"] = "allowed"
    mode: ContentPlanningContinuationMode
    path: ContentPlanningContinuationMode
    routing_status: ContentPlanningModeRoutingStatus
    brief_required: Literal[True] = True
    write_authorized: Literal[False] = False

    @model_validator(mode="after")
    def require_matching_mode_and_path(self) -> ContentPlanningModeAllowedPath:
        if self.mode != self.path:
            raise ValueError("Allowed planning mode and path must match.")
        return self


class ContentPlanningModeBlockedPath(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["blocked"] = "blocked"
    requested_mode: str
    mode: ContentPlanningMode | None = None
    path: None = None
    blocker: ContentPlanningModeBlocker
    automatic_text_draft_allowed: Literal[False] = False
    write_authorized: Literal[False] = False


class ContentPlanningModeTerminalPath(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["terminal"] = "terminal"
    mode: ContentPlanningTerminalMode
    path: Literal["end_without_brief"] = "end_without_brief"
    brief_required: Literal[False] = False
    automatic_text_draft_allowed: Literal[False] = False
    write_authorized: Literal[False] = False
    reason: str = Field(min_length=1)
    next_step: str = Field(min_length=1)


ContentPlanningModeGuardResult = Annotated[
    ContentPlanningModeAllowedPath
    | ContentPlanningModeBlockedPath
    | ContentPlanningModeTerminalPath,
    Field(discriminator="status"),
]


class ContentPlanningModeReadinessResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_type: Literal["content_planning_mode_readiness"] = (
        "content_planning_mode_readiness"
    )
    contract_version: Literal["content_planning_mode_readiness_v1"] = (
        "content_planning_mode_readiness_v1"
    )
    requested_mode: str
    outcome: ContentPlanningModeGuardResult


def guard_content_planning_mode(
    request: ContentPlanningModeRequest,
) -> ContentPlanningModeGuardResult:
    if request.requested_mode == "refresh_existing":
        if not request.public_canonical_url:
            return ContentPlanningModeBlockedPath(
                requested_mode=request.requested_mode,
                mode="refresh_existing",
                blocker=ContentPlanningModeBlocker(
                    code="missing_refresh_public_canonical",
                    label="Brakuje publicznego adresu strony",
                    reason=(
                        "Tryb refresh_existing zachowuje wymaganie dokładnego "
                        "final_canonical_url."
                    ),
                    next_step="Wskaż publiczny kanoniczny adres istniejącej strony.",
                ),
            )
        if request.planning_foundation_id:
            return ContentPlanningModeBlockedPath(
                requested_mode=request.requested_mode,
                mode="refresh_existing",
                blocker=ContentPlanningModeBlocker(
                    code="refresh_foundation_conflict",
                    label="Odświeżenie nie używa podstawy nowej strony",
                    reason=(
                        "Tryb refresh_existing zachowuje zakaz dołączania new-page "
                        "foundation."
                    ),
                    next_step="Usuń foundation albo wybierz tryb nowej strony.",
                ),
            )
        return ContentPlanningModeAllowedPath(
            mode="refresh_existing",
            path="refresh_existing",
            routing_status="existing_flow",
        )
    if request.requested_mode == "new_page":
        if request.public_canonical_url:
            return ContentPlanningModeBlockedPath(
                requested_mode=request.requested_mode,
                mode="new_page",
                blocker=ContentPlanningModeBlocker(
                    code="new_page_public_source_conflict",
                    label="Nowa strona nie ma publicznego źródła",
                    reason=(
                        "Tryb new_page zachowuje zakaz przypisywania istniejącego "
                        "final_canonical_url."
                    ),
                    next_step="Usuń publiczny adres albo wybierz tryb dla istniejącej strony.",
                ),
            )
        if not request.service_card_id:
            return ContentPlanningModeBlockedPath(
                requested_mode=request.requested_mode,
                mode="new_page",
                blocker=ContentPlanningModeBlocker(
                    code="missing_new_page_service_identity",
                    label="Brakuje usługi dla nowej strony",
                    reason="Tryb new_page zachowuje wymaganie dokładnej karty usługi.",
                    next_step="Wybierz dokładną kartę usługi dla nowej strony.",
                ),
            )
        if not request.planning_foundation_id:
            return ContentPlanningModeBlockedPath(
                requested_mode=request.requested_mode,
                mode="new_page",
                blocker=ContentPlanningModeBlocker(
                    code="missing_new_page_foundation_identity",
                    label="Brakuje podstawy nowej strony",
                    reason="Tryb new_page zachowuje wymaganie exact foundation.",
                    next_step="Potwierdź foundation nowej strony przed planowaniem.",
                ),
            )
        if not request.proposed_ia_location:
            return ContentPlanningModeBlockedPath(
                requested_mode=request.requested_mode,
                mode="new_page",
                blocker=ContentPlanningModeBlocker(
                    code="missing_new_page_ia_identity",
                    label="Brakuje miejsca nowej strony w architekturze",
                    reason="Tryb new_page zachowuje wymaganie dokładnej lokalizacji IA.",
                    next_step="Wskaż planowane miejsce strony w architekturze informacji.",
                ),
            )
        return ContentPlanningModeAllowedPath(
            mode="new_page",
            path="new_page",
            routing_status="existing_flow",
        )
    if request.requested_mode == "create":
        if request.public_canonical_url:
            return ContentPlanningModeBlockedPath(
                requested_mode=request.requested_mode,
                mode="create",
                blocker=ContentPlanningModeBlocker(
                    code="create_public_source_conflict",
                    label="Tryb utworzenia nie ma publicznego źródła",
                    reason=(
                        "Wskazany publiczny adres oznacza istniejącą stronę i nie może "
                        "być podstawą trybu create."
                    ),
                    next_step=(
                        "Wybierz odświeżenie albo migrację istniejącej strony lub usuń "
                        "publiczny adres z kontraktu nowej strony."
                    ),
                ),
            )
        if not request.service_card_id:
            return ContentPlanningModeBlockedPath(
                requested_mode=request.requested_mode,
                mode="create",
                blocker=ContentPlanningModeBlocker(
                    code="missing_create_service_identity",
                    label="Brakuje usługi dla nowej strony",
                    reason="Tryb create wymaga jawnego powiązania z usługą Ekologus.",
                    next_step="Wybierz dokładną kartę usługi przed dalszym planowaniem.",
                ),
            )
        if not request.planning_foundation_id:
            return ContentPlanningModeBlockedPath(
                requested_mode=request.requested_mode,
                mode="create",
                blocker=ContentPlanningModeBlocker(
                    code="missing_create_foundation_identity",
                    label="Brakuje podstawy nowej strony",
                    reason="Tryb create wymaga dokładnej, potwierdzonej podstawy planowania.",
                    next_step="Potwierdź foundation nowej strony przed dalszym planowaniem.",
                ),
            )
        if not request.proposed_ia_location:
            return ContentPlanningModeBlockedPath(
                requested_mode=request.requested_mode,
                mode="create",
                blocker=ContentPlanningModeBlocker(
                    code="missing_create_ia_identity",
                    label="Brakuje miejsca nowej strony w architekturze",
                    reason="Tryb create wymaga jawnej tożsamości IA dla nowego dokumentu.",
                    next_step="Wskaż planowane miejsce strony w architekturze informacji.",
                ),
            )
        return ContentPlanningModeAllowedPath(
            mode="create",
            path="create",
            routing_status="contract_only",
        )
    if request.requested_mode == "migration":
        if not request.public_canonical_url:
            return ContentPlanningModeBlockedPath(
                requested_mode=request.requested_mode,
                mode="migration",
                blocker=ContentPlanningModeBlocker(
                    code="missing_migration_public_source",
                    label="Brakuje publicznego źródła migracji",
                    reason="Tryb migration wymaga dokładnej istniejącej strony publicznej.",
                    next_step="Wskaż kanoniczny publiczny adres strony źródłowej.",
                ),
            )
        if request.migration_target is None:
            return ContentPlanningModeBlockedPath(
                requested_mode=request.requested_mode,
                mode="migration",
                blocker=ContentPlanningModeBlocker(
                    code="missing_migration_target_identity",
                    label="Brakuje dokładnego targetu migracji",
                    reason=(
                        "Tryb migration wymaga jawnej, evidence-bound relacji źródła "
                        "publicznego z obiektem docelowym."
                    ),
                    next_step="Potwierdź dokładny target i dowód relacji public-to-dev.",
                ),
            )
        if request.migration_target.mapping_status != "exact":
            return ContentPlanningModeBlockedPath(
                requested_mode=request.requested_mode,
                mode="migration",
                blocker=ContentPlanningModeBlocker(
                    code="migration_target_not_exact",
                    label="Target migracji nie jest potwierdzony",
                    reason=(
                        "Obserwowany kandydat nie dowodzi dokładnej relacji public-to-dev "
                        "dla tej strony."
                    ),
                    next_step="Potwierdź exact mapping wraz z dowodem relacji.",
                ),
            )
        if request.migration_target.public_url != request.public_canonical_url:
            return ContentPlanningModeBlockedPath(
                requested_mode=request.requested_mode,
                mode="migration",
                blocker=ContentPlanningModeBlocker(
                    code="migration_target_source_mismatch",
                    label="Target dotyczy innej strony publicznej",
                    reason=(
                        "Dokładny mapping musi wiązać target z tą samą stroną, która "
                        "jest źródłem migracji."
                    ),
                    next_step="Odczytaj exact mapping dla wskazanego publicznego źródła.",
                ),
            )
        return ContentPlanningModeAllowedPath(
            mode="migration",
            path="migration",
            routing_status="contract_only",
        )
    if request.requested_mode == "structure":
        return ContentPlanningModeBlockedPath(
            requested_mode=request.requested_mode,
            mode="structure",
            blocker=ContentPlanningModeBlocker(
                code="structure_requires_human_decision",
                label="Struktura wymaga osobnej decyzji",
                reason=(
                    "Tryb structure służy do rozstrzygnięcia układu dokumentu i nie "
                    "otwiera automatycznie pracy nad tekstem."
                ),
                next_step="Zapisz osobną decyzję o strukturze przed wyborem dalszego trybu.",
            ),
        )
    if request.requested_mode == "no_change":
        return ContentPlanningModeTerminalPath(
            mode="no_change",
            reason="Decyzja no_change kończy pracę bez przygotowania briefu.",
            next_step=(
                "Zachowaj decyzję jako wynik tej oceny i nie otwieraj planowania tekstu."
            ),
        )
    if request.requested_mode == "defer":
        return ContentPlanningModeTerminalPath(
            mode="defer",
            reason="Decyzja defer odkłada pracę bez przygotowania briefu.",
            next_step="Zapisz powód odroczenia i wróć do oceny po zmianie warunków.",
        )
    return ContentPlanningModeBlockedPath(
        requested_mode=request.requested_mode,
        blocker=ContentPlanningModeBlocker(
            code="unsupported_mode",
            label="Nieobsługiwany tryb pracy",
            reason="WILQ nie ma jawnego kontraktu dla wskazanego trybu pracy.",
            next_step="Wybierz jeden z jawnie obsługiwanych trybów planowania.",
        ),
    )


def content_planning_mode_readiness(
    request: ContentPlanningModeRequest,
) -> ContentPlanningModeReadinessResponse:
    return ContentPlanningModeReadinessResponse(
        requested_mode=request.requested_mode,
        outcome=guard_content_planning_mode(request),
    )


__all__ = [
    "ContentPlanningMode",
    "ContentPlanningModeAllowedPath",
    "ContentPlanningModeBlockedPath",
    "ContentPlanningModeBlocker",
    "ContentPlanningModeReadinessResponse",
    "ContentPlanningModeRequest",
    "ContentPlanningModeTerminalPath",
    "content_planning_mode_readiness",
    "guard_content_planning_mode",
]
