from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from wilq.briefing.content_diagnostics import build_content_freshness_assessment_fast
from wilq.connectors.wordpress.authoring import build_wordpress_authoring_profile
from wilq.content.canonical.metric_dimensions import metric_dimensions_match_landing
from wilq.content.knowledge.work_item_service_profile import (
    build_content_work_item_service_profile_context,
)
from wilq.content.workflow.catalog import (
    ContentInventoryCatalogItem,
    ContentInventoryMaterialResponse,
    build_content_inventory_catalog_cached,
    inventory_work_item_id,
    read_content_inventory_material,
)
from wilq.content.workflow.decision_mapping import content_work_item_from_decision
from wilq.content.workflow.inventory_binding import inventory_decision_for_work_item
from wilq.content.workflow.queue import (
    ContentWorkItemQueueCandidate,
    build_content_work_item_queue_candidate,
)
from wilq.schemas import ContentDecisionItem, ContentFreshnessAssessment


class ContentDecisionContextSourceMaterial(BaseModel):
    """Observed public material, deliberately separate from an editor contract."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["available", "missing", "blocked", "unknown"]
    source_kind: str | None = None
    observed_surfaces: list[str] = Field(default_factory=list)
    word_count: int | None = None
    section_count: int | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)


class ContentDecisionContextSourcePublic(BaseModel):
    """What is known about the public source object without filling gaps heuristically."""

    model_config = ConfigDict(extra="forbid")

    identity_status: Literal["observed", "partial", "missing", "unknown"]
    object_id: str | None = None
    url: str | None = None
    title: str | None = None
    post_type: str | None = None
    post_status: str | None = None
    template: str | None = None
    material: ContentDecisionContextSourceMaterial
    label: str
    reason: str
    technical_reason: str | None = None


ContentDecisionTargetMappingStatus = Literal["exact", "unverified", "missing"]


class ContentDecisionContextAuthoringTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mapping_status: ContentDecisionTargetMappingStatus
    environment: str | None = None
    object_id: str | None = None
    post_type: str | None = None
    post_status: str | None = None
    template: str | None = None
    authoring_surfaces: list[str] = Field(default_factory=list)
    allowed_operation: str | None = None
    label: str
    reason: str
    technical_reason: str | None = None


class ContentDecisionContextRelation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["exact", "unverified", "missing"]
    relation_type: Literal[
        "same_page", "replacement", "new_page", "migration", "structure", "unknown"
    ] = "unknown"
    label: str
    reason: str
    technical_reason: str | None = None


class ContentDecisionContextReadinessAxis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ready", "review_required", "refresh_required", "missing", "blocked"]
    label: str
    reason: str
    technical_reason: str | None = None
    blocker_codes: list[str] = Field(default_factory=list)


class ContentDecisionContextDisposition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["proposed", "undetermined"]
    proposed_disposition: Literal["refresh_or_merge", "undetermined"]
    label: str
    reason: str
    technical_reason: str | None = None


class ContentDecisionContextService(BaseModel):
    """API-owned service binding for the marketer-facing page header."""

    model_config = ConfigDict(extra="forbid")

    label: str | None = None
    reason: str


class ContentDecisionContextDeliveryCapability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability: Literal["create_draft_only", "manual_handoff", "unsupported"]
    request_status: Literal["blocked", "not_applicable"]
    label: str
    reason: str
    technical_reason: str | None = None


class ContentDecisionContextMeasurementTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    label: str
    public_url: str | None = None
    reason: str
    technical_reason: str | None = None
    source_connectors: list[str] = Field(default_factory=list)


class ContentDecisionContextSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_connector: str
    label: str
    value: int | float | str
    freshness_state: Literal["fresh", "stale", "unknown"]
    evidence_ids: list[str] = Field(default_factory=list)


class ContentDecisionContextNextSafeAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal[
        "refresh_connector",
        "resolve_source_access",
        "map_authoring_target",
        "inspect_object",
        "open_workspace",
        "none",
    ]
    label: str
    reason: str
    connector_id: str | None = None


class ContentDecisionContextDisclosure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    summary: str


class ContentDecisionContextAlias(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["requested_work_item", "inventory_work_item", "decision_work_item"]
    value: str


class ContentDecisionContext(BaseModel):
    """One read-only decision view for one currently existing content work item."""

    model_config = ConfigDict(extra="forbid")

    response_type: Literal["content_decision_context"] = "content_decision_context"
    contract_version: Literal["content_decision_context_v1"] = "content_decision_context_v1"
    work_item_id: str
    work_kind: Literal["refresh_existing", "undetermined"]
    source_public: ContentDecisionContextSourcePublic
    authoring_target: ContentDecisionContextAuthoringTarget
    source_target_relation: ContentDecisionContextRelation
    object_readiness: ContentDecisionContextReadinessAxis
    decision_disposition: ContentDecisionContextDisposition
    service: ContentDecisionContextService
    evidence_readiness: ContentDecisionContextReadinessAxis
    delivery_capability: ContentDecisionContextDeliveryCapability
    measurement_target: ContentDecisionContextMeasurementTarget
    applicable_signals: list[ContentDecisionContextSignal] = Field(default_factory=list)
    next_safe_action: ContentDecisionContextNextSafeAction
    secondary_disclosures: list[ContentDecisionContextDisclosure] = Field(default_factory=list)
    legacy_aliases: list[ContentDecisionContextAlias] = Field(default_factory=list)


def build_content_decision_context(
    work_item_id: str,
) -> ContentDecisionContext | None:
    """Build the first read-only context without opening planning or authoring.

    The current public work-item ID is a selection key, not proof that WILQ has
    an exact WordPress object or a mapped dev target.  This builder is therefore
    intentionally conservative: missing object fields stay null and the global
    WordPress profile is used only for delivery capability, never for matching.
    """

    decision = inventory_decision_for_work_item(
        work_item_id,
        read_material=False,
        allow_material_pending=True,
        include_all_metric_facts=True,
    )
    if decision is None:
        return None

    source_url = _source_url(decision)
    catalog_item, material = _source_material(source_url)
    freshness = build_content_freshness_assessment_fast(
        relevant_connector_ids=decision.source_connectors,
    )
    candidate = build_content_work_item_queue_candidate(decision, freshness)
    authoring_profile = build_wordpress_authoring_profile(
        "wordpress_ekologus",
        include_dev_content=False,
    )

    source_public = _source_public_context(decision, catalog_item, material)
    authoring_target = _authoring_target_context(authoring_profile.authoring_target)
    relation = _source_target_relation(authoring_target.mapping_status)
    object_readiness = _object_readiness(source_public, authoring_target, relation)
    evidence_readiness = _evidence_readiness(freshness)
    disposition = _disposition(decision)
    service_profile = build_content_work_item_service_profile_context(
        content_work_item_from_decision(decision)
    )
    service = ContentDecisionContextService(
        label=service_profile.service_label,
        reason=service_profile.reason,
    )
    delivery = _delivery_capability(
        allowed_operation=authoring_profile.write_boundary.allowed_operation,
        target_mapping_status=authoring_target.mapping_status,
    )
    measurement = ContentDecisionContextMeasurementTarget(
        status=candidate.measurement_readiness.status,
        label=candidate.measurement_readiness.label,
        public_url=candidate.final_canonical_url,
        reason=candidate.measurement_readiness.reason,
        source_connectors=candidate.measurement_readiness.source_connectors,
    )
    return ContentDecisionContext(
        work_item_id=work_item_id,
        work_kind=(
            "refresh_existing"
            if disposition.proposed_disposition == "refresh_or_merge"
            else "undetermined"
        ),
        source_public=source_public,
        authoring_target=authoring_target,
        source_target_relation=relation,
        object_readiness=object_readiness,
        decision_disposition=disposition,
        service=service,
        evidence_readiness=evidence_readiness,
        delivery_capability=delivery,
        measurement_target=measurement,
        applicable_signals=_applicable_signals(decision, candidate, freshness, source_url),
        next_safe_action=_next_safe_action(
            freshness=freshness,
            source_public=source_public,
            object_readiness=object_readiness,
        ),
        secondary_disclosures=_secondary_disclosures(catalog_item, authoring_target),
        legacy_aliases=_aliases(work_item_id, decision, source_url),
    )


def _source_url(decision: ContentDecisionItem) -> str | None:
    for value in (
        decision.source_public_url,
        decision.final_canonical_url,
        decision.page,
    ):
        if value and value.strip():
            return value.strip()
    return None


def _source_material(
    source_url: str | None,
) -> tuple[ContentInventoryCatalogItem | None, ContentInventoryMaterialResponse | None]:
    if source_url is None:
        return None, None
    catalog = build_content_inventory_catalog_cached()
    catalog_item = next(
        (item for item in catalog.items if item.url.rstrip("/") == source_url.rstrip("/")),
        None,
    )
    if catalog_item is None:
        return None, None
    return catalog_item, read_content_inventory_material(source_url, catalog=catalog)


def _source_public_context(
    decision: ContentDecisionItem,
    catalog_item: ContentInventoryCatalogItem | None,
    material: ContentInventoryMaterialResponse | None,
) -> ContentDecisionContextSourcePublic:
    source_url = _source_url(decision)
    material_status = _material_status(material)
    evidence_ids = _unique(
        [
            catalog_item.evidence_id if catalog_item is not None else None,
            material.evidence_id if material is not None else None,
        ]
    )
    observed_surfaces = _observed_material_surfaces(material)
    caveats = ["Odczyt materiału nie jest dowodem powierzchni authoringu ani obiektu dev."]
    if material_status != "available":
        caveats.append("Materiał strony nie jest obecnie dostępny do sprawdzenia.")
    if catalog_item is not None and catalog_item.content_type == "sitemap":
        caveats.append(
            "Wpis sitemap potwierdza adres w inventory, ale nie jest typem posta WordPress."
        )
    source_material = ContentDecisionContextSourceMaterial(
        status=material_status,
        source_kind=None if material is None else material.source_kind,
        observed_surfaces=observed_surfaces,
        word_count=(
            material.content_word_count
            if material is not None and material.status == "ready"
            else (catalog_item.content_word_count if catalog_item is not None else None)
        ),
        section_count=(
            _section_count(material)
            if material is not None and material.status == "ready"
            else (catalog_item.section_count if catalog_item is not None else None)
        ),
        evidence_ids=evidence_ids,
        caveats=caveats,
    )
    if catalog_item is None:
        identity_status: Literal["observed", "partial", "missing", "unknown"] = (
            "unknown" if source_url else "missing"
        )
        label = "Nie znaleziono publicznego obiektu" if source_url else "Brakuje publicznego źródła"
        reason = (
            "Nie znaleźliśmy aktualnego rekordu tej strony w inventory."
            if source_url
            else "Ten work item nie wskazuje publicznej strony do sprawdzenia."
        )
        technical_reason = (
            "WILQ nie znalazł aktualnego rekordu inventory dla tego adresu."
            if source_url
            else "Work item nie wskazuje publicznego źródła."
        )
    elif material_status == "available":
        identity_status = "partial"
        label = "Adres i materiał rozpoznane częściowo"
        reason = (
            "WILQ widzi publiczny adres i materiał, ale nie potwierdził jeszcze konkretnego "
            "obiektu WordPress ani miejsca przygotowania zmiany."
        )
        technical_reason = (
            "WILQ zna publiczny adres i materiał, ale obecny kontrakt inventory nie "
            "zachowuje post ID, post type, statusu, template ani powierzchni authoringu."
        )
    else:
        identity_status = "observed"
        label = "Adres rozpoznany; materiał niedostępny"
        reason = (
            "WILQ zna publiczny adres, ale materiał tej strony nie jest obecnie dostępny "
            "do sprawdzenia."
        )
        technical_reason = (
            "WILQ zna adres z inventory, ale nie ma kompletnego odczytu materiału "
            "ani exact tożsamości obiektu WordPress."
        )
    return ContentDecisionContextSourcePublic(
        identity_status=identity_status,
        url=source_url,
        title=(
            material.title
            if material is not None and material.title
            else (catalog_item.title if catalog_item is not None else decision.title)
        ),
        material=source_material,
        label=label,
        reason=reason,
        technical_reason=technical_reason,
    )


def _material_status(
    material: ContentInventoryMaterialResponse | None,
) -> Literal["available", "missing", "blocked", "unknown"]:
    if material is None:
        return "unknown"
    if material.status == "ready":
        return "available"
    if material.status == "blocked":
        return "blocked"
    return "missing"


def _section_count(material: ContentInventoryMaterialResponse) -> int | None:
    headings = material.acf_section_headings or material.section_headings
    return len(headings) if headings else None


def _observed_material_surfaces(
    material: ContentInventoryMaterialResponse | None,
) -> list[str]:
    if material is None or material.status != "ready":
        return []
    region = (material.extraction_region or "").strip()
    mapping = {
        "wordpress_rest.content": "wordpress_rest_content",
        "wordpress_rest.acf": "wordpress_rest_acf",
        "public_html.main_or_article": "rendered_html",
    }
    surfaces = [mapping[region]] if region in mapping else []
    if material.acf_field_names or material.acf_section_headings:
        surfaces.append("acf_fields_observed")
    return _unique(surfaces)


def _authoring_target_context(authoring_target: str) -> ContentDecisionContextAuthoringTarget:
    environment = authoring_target.strip() or None
    if environment is None:
        return ContentDecisionContextAuthoringTarget(
            mapping_status="missing",
            label="Brakuje środowiska dev",
            reason="Nie ma skonfigurowanego środowiska dev dla tej strony.",
            technical_reason=(
                "WILQ nie ma skonfigurowanego środowiska authoringu dla tego "
                "work itemu."
            ),
        )
    return ContentDecisionContextAuthoringTarget(
        mapping_status="unverified",
        environment=environment,
        allowed_operation="create_wordpress_draft",
        label="Target dev niepotwierdzony",
        reason="Brakuje potwierdzonego celu dev dla tej strony.",
        technical_reason=(
            "Globalny profil WordPress potwierdza możliwości środowiska, ale nie "
            "dowodzi mapy tej publicznej strony do konkretnego obiektu dev."
        ),
    )


def _source_target_relation(
    target_mapping_status: ContentDecisionTargetMappingStatus,
) -> ContentDecisionContextRelation:
    if target_mapping_status == "missing":
        return ContentDecisionContextRelation(
            status="missing",
            label="Brakuje relacji strony publicznej i dev",
            reason="Bez celu dev nie możemy potwierdzić powiązania z publiczną stroną.",
            technical_reason="Bez targetu dev WILQ nie może określić relacji source do targetu.",
        )
    return ContentDecisionContextRelation(
        status="unverified",
        label="Relacja source → target niepotwierdzona",
        reason="Brakuje potwierdzenia, że strona publiczna i cel dev dotyczą tego samego elementu.",
        technical_reason=(
            "Nie ma evidence-bound ani zatwierdzonej przez człowieka relacji między "
            "publicznym source a targetem dev."
        ),
    )


def _object_readiness(
    source_public: ContentDecisionContextSourcePublic,
    authoring_target: ContentDecisionContextAuthoringTarget,
    relation: ContentDecisionContextRelation,
) -> ContentDecisionContextReadinessAxis:
    missing_fields = [
        field
        for field, value in (
            ("wordpress_post_id", source_public.object_id),
            ("post_type", source_public.post_type),
            ("post_status", source_public.post_status),
            ("template", source_public.template),
            ("authoring_target", authoring_target.object_id),
        )
        if value is None
    ]
    if source_public.identity_status in {"missing", "unknown"}:
        return ContentDecisionContextReadinessAxis(
            status="missing",
            label="Obiekt wymaga rozpoznania",
            reason="Brakuje potwierdzonego publicznego obiektu, z którym można kontynuować pracę.",
            technical_reason=source_public.technical_reason or source_public.reason,
            blocker_codes=["missing_public_object_identity"],
        )
    if relation.status != "exact" or missing_fields:
        return ContentDecisionContextReadinessAxis(
            status="review_required",
            label="Obiekt częściowo rozpoznany",
            reason=(
                "Brakuje potwierdzonego obiektu WordPress i celu dev, w którym można "
                "przygotować zmianę."
            ),
            technical_reason=(
                "WILQ nie może przypisać authoringu ani delivery do konkretnego "
                "obiektu, dopóki brakujące pola pozostają niepotwierdzone."
            ),
            blocker_codes=["object_identity_unverified", *missing_fields],
        )
    return ContentDecisionContextReadinessAxis(
        status="ready",
        label="Obiekt rozpoznany",
        reason="Publiczna strona, cel dev i ich powiązanie są potwierdzone.",
        technical_reason="Publiczny source, target i relacja mają exact potwierdzenie.",
    )


def _evidence_readiness(
    freshness: ContentFreshnessAssessment,
) -> ContentDecisionContextReadinessAxis:
    blocker_connectors = _unique(
        [
            *freshness.stale_connector_ids,
            *freshness.missing_connector_ids,
            *freshness.blocked_connector_ids,
        ]
    )
    if freshness.requires_refresh:
        return ContentDecisionContextReadinessAxis(
            status="refresh_required",
            label="Dowody wymagają odświeżenia",
            reason=freshness.summary,
            blocker_codes=[f"connector:{connector}" for connector in blocker_connectors],
        )
    if freshness.state == "missing":
        return ContentDecisionContextReadinessAxis(
            status="missing",
            label="Brakuje wymaganych dowodów",
            reason=freshness.summary,
            blocker_codes=[f"connector:{connector}" for connector in blocker_connectors],
        )
    if freshness.state == "blocked":
        return ContentDecisionContextReadinessAxis(
            status="blocked",
            label="Dowody są zablokowane",
            reason=freshness.summary,
            blocker_codes=[f"connector:{connector}" for connector in blocker_connectors],
        )
    return ContentDecisionContextReadinessAxis(
        status="ready",
        label="Dowody są aktualne",
        reason=freshness.summary,
    )


def _disposition(decision: ContentDecisionItem) -> ContentDecisionContextDisposition:
    if decision.decision_type == "refresh_or_merge":
        return ContentDecisionContextDisposition(
            status="proposed",
            proposed_disposition="refresh_or_merge",
            label="Odśwież lub scal istniejącą stronę",
            reason=(
                "Ten work item dotyczy istniejącego publicznego adresu; ostateczna "
                "decyzja wymaga aktualnych dowodów i decyzji człowieka."
            ),
        )
    return ContentDecisionContextDisposition(
        status="undetermined",
        proposed_disposition="undetermined",
        label="Rodzaj pracy nieustalony",
        reason="Obecny planner nie ma kontraktu dla tego rodzaju pracy.",
    )


def _delivery_capability(
    *,
    allowed_operation: str,
    target_mapping_status: ContentDecisionTargetMappingStatus,
) -> ContentDecisionContextDeliveryCapability:
    if allowed_operation != "create_wordpress_draft":
        return ContentDecisionContextDeliveryCapability(
            capability="unsupported",
            request_status="not_applicable",
            label="Brak obsługiwanej operacji delivery",
            reason="Nie ma bezpiecznej operacji przekazania szkicu dla tej strony.",
            technical_reason=(
                "Globalny profil WordPress nie oferuje bezpiecznej operacji "
                "draft-only."
            ),
        )
    if target_mapping_status != "exact":
        return ContentDecisionContextDeliveryCapability(
            capability="create_draft_only",
            request_status="blocked",
            label="Szkic dev wymaga potwierdzenia targetu",
            reason=(
                "Przekazanie szkicu pozostaje zablokowane, dopóki nie potwierdzimy celu "
                "dev i nie przejdziemy wymaganych kontroli."
            ),
            technical_reason=(
                "Adapter obsługuje wyłącznie create draft-only przez ActionObject; "
                "brak exact targetu i accepted revision blokuje request."
            ),
        )
    return ContentDecisionContextDeliveryCapability(
        capability="create_draft_only",
        request_status="blocked",
        label="Szkic dev wymaga dalszych bramek",
        reason="Przekazanie szkicu wymaga jeszcze wymaganych kontroli przed dalszym etapem.",
        technical_reason=(
            "Create draft-only nadal wymaga exact revision i pełnego ActionObject "
            "lifecycle."
        ),
    )


def _applicable_signals(
    decision: ContentDecisionItem,
    candidate: ContentWorkItemQueueCandidate,
    freshness: ContentFreshnessAssessment,
    source_url: str | None,
) -> list[ContentDecisionContextSignal]:
    search_metrics = candidate.search_metrics
    freshness_state: Literal["fresh", "stale", "unknown"] = (
        "stale"
        if "google_search_console" in freshness.stale_connector_ids
        else "fresh"
        if freshness.state == "fresh"
        else "unknown"
    )
    evidence_ids = _gsc_signal_evidence_ids(decision, source_url)
    signals: list[ContentDecisionContextSignal] = []
    for label, value in (
        ("Wyświetlenia GSC", search_metrics.impressions),
        ("Kliknięcia GSC", search_metrics.clicks),
        ("Najlepsza średnia pozycja", search_metrics.best_average_position),
    ):
        if value is not None:
            signals.append(
                ContentDecisionContextSignal(
                    source_connector="google_search_console",
                    label=label,
                    value=value,
                    freshness_state=freshness_state,
                    evidence_ids=evidence_ids,
                )
            )
    if search_metrics.primary_query:
        signals.append(
            ContentDecisionContextSignal(
                source_connector="google_search_console",
                label="Główne zapytanie",
                value=search_metrics.primary_query,
                freshness_state=freshness_state,
                evidence_ids=evidence_ids,
            )
        )
    return signals[:4]


def _gsc_signal_evidence_ids(
    decision: ContentDecisionItem,
    source_url: str | None,
) -> list[str]:
    if source_url is None:
        return []
    return _unique(
        fact.evidence_id
        for fact in decision.metric_facts
        if fact.source_connector == "google_search_console"
        and metric_dimensions_match_landing(fact.dimensions, source_url)
    )


def _next_safe_action(
    *,
    freshness: ContentFreshnessAssessment,
    source_public: ContentDecisionContextSourcePublic,
    object_readiness: ContentDecisionContextReadinessAxis,
) -> ContentDecisionContextNextSafeAction:
    if freshness.stale_connector_ids:
        connector_id = freshness.stale_connector_ids[0]
        return ContentDecisionContextNextSafeAction(
            kind="refresh_connector",
            label=f"Odśwież {_connector_label(freshness, connector_id)}",
            connector_id=connector_id,
            reason=freshness.summary,
        )
    if freshness.missing_connector_ids or freshness.blocked_connector_ids:
        connector_id = (freshness.missing_connector_ids or freshness.blocked_connector_ids)[0]
        return ContentDecisionContextNextSafeAction(
            kind="resolve_source_access",
            label=f"Sprawdź dostęp do {_connector_label(freshness, connector_id)}",
            connector_id=connector_id,
            reason=freshness.summary,
        )
    if (
        source_public.material.status != "available"
        or source_public.identity_status in {"missing", "unknown"}
    ):
        return ContentDecisionContextNextSafeAction(
            kind="inspect_object",
            label="Uzupełnij rozpoznanie obiektu",
            reason=object_readiness.reason,
        )
    if object_readiness.status in {"missing", "review_required", "ready"}:
        return ContentDecisionContextNextSafeAction(
            kind="open_workspace",
            label="Otwórz warsztat strony",
            reason="Możesz przejść do read-only podglądu tekstu tej samej strony.",
        )
    return ContentDecisionContextNextSafeAction(
        kind="none",
        label="Nie ma bezpiecznej akcji automatycznej",
        reason="Przed następnym etapem potrzebna jest decyzja człowieka.",
    )


def _connector_label(freshness: ContentFreshnessAssessment, connector_id: str) -> str:
    try:
        index = [
            *freshness.stale_connector_ids,
            *freshness.missing_connector_ids,
            *freshness.blocked_connector_ids,
        ].index(connector_id)
    except ValueError:
        return connector_id
    labels = freshness.connector_labels_requiring_refresh
    return labels[index] if index < len(labels) else connector_id


def _secondary_disclosures(
    catalog_item: ContentInventoryCatalogItem | None,
    authoring_target: ContentDecisionContextAuthoringTarget,
) -> list[ContentDecisionContextDisclosure]:
    disclosures = [
        ContentDecisionContextDisclosure(
            id="authoring-profile-scope",
            label="Zakres profilu WordPress",
            summary=(
                "Profil środowiska jest capability globalną; nie jest mapą wybranej "
                "strony do obiektu dev."
            ),
        )
    ]
    if catalog_item is not None:
        disclosures.insert(
            0,
            ContentDecisionContextDisclosure(
                id="inventory-record-scope",
                label="Zakres rekordu inventory",
                summary=(
                    f"Źródło katalogu: {catalog_item.content_type}. "
                    "Nie traktuj tej wartości jako post type ani template."
                ),
            ),
        )
    if authoring_target.mapping_status != "exact":
        disclosures.append(
            ContentDecisionContextDisclosure(
                id="delivery-boundary",
                label="Granica delivery",
                summary=(
                    "WILQ nie aktualizuje ani nie publikuje istniejącej strony; "
                    "dopuszczalny jest wyłącznie create draft-only przez ActionObject."
                ),
            )
        )
    return disclosures


def _aliases(
    work_item_id: str,
    decision: ContentDecisionItem,
    source_url: str | None,
) -> list[ContentDecisionContextAlias]:
    aliases = [
        ContentDecisionContextAlias(kind="requested_work_item", value=work_item_id),
        ContentDecisionContextAlias(
            kind="decision_work_item",
            value=f"content_work_item_{decision.id}",
        ),
    ]
    if source_url:
        aliases.append(
            ContentDecisionContextAlias(
                kind="inventory_work_item",
                value=inventory_work_item_id(source_url),
            )
        )
    return _unique_aliases(aliases)


def _unique(values: Iterable[str | None]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _unique_aliases(
    aliases: list[ContentDecisionContextAlias],
) -> list[ContentDecisionContextAlias]:
    by_value: dict[str, ContentDecisionContextAlias] = {}
    for alias in aliases:
        by_value.setdefault(alias.value, alias)
    return list(by_value.values())


__all__ = ["ContentDecisionContext", "build_content_decision_context"]
