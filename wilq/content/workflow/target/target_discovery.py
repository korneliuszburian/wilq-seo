from __future__ import annotations

import json
from hashlib import sha256
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field

from wilq.connectors.wordpress.acf_relationship_observation import (
    observe_wordpress_acf_panel_labels,
)
from wilq.connectors.wordpress.acf_rest_schema import (
    WordPressAcfRestSchema,
    read_wordpress_acf_rest_schema,
)
from wilq.connectors.wordpress.acf_source_snapshot import (
    WordPressAcfFlexibleSnapshot,
    read_wordpress_acf_flexible_snapshot,
)
from wilq.connectors.wordpress.authoring import (
    WordPressAuthoringDevContentObject,
    WordPressAuthoringProfile,
    build_wordpress_authoring_profile,
)
from wilq.content.workflow.decisions.inventory_binding import inventory_decision_for_work_item
from wilq.content.workflow.policies import wordpress_dev_host_allowed
from wilq.content.workflow.target.native_content_observation import (
    NativePostContentObservation,
    observe_native_post_content,
    positive_ascii_decimal,
    valid_url_port,
)
from wilq.schemas import utc_now


class ContentTargetAuthoringLayout(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    # WordPress authoring observation numbers visible ACF rows from one.
    # Keep that human-visible identity through mapping; the eventual compiler
    # owns the single conversion to a zero-based JSON array position.
    section_index: int | None = Field(default=None, ge=1)
    label: str = ""
    fields: list[str] = Field(default_factory=list)
    schema_fields: list[str] = Field(default_factory=list)
    writable_fields: list[str] = Field(default_factory=list)
    relationships: list[ContentTargetAuthoringRelationship] = Field(default_factory=list)


class ContentTargetAuthoringRelationshipItem(BaseModel):
    """One exact ID observed in an ACF relationship field."""

    model_config = ConfigDict(extra="forbid")

    relationship_id: int = Field(gt=0)
    label: str = Field(min_length=1)


class ContentTargetAuthoringRelationship(BaseModel):
    """Read-only relationship labels inferred only from matching public markup."""

    model_config = ConfigDict(extra="forbid")

    field_name: str
    item_kind: Literal["integer_id"] = "integer_id"
    status: Literal["available", "unavailable"] = "unavailable"
    source_ref: str = ""
    items: list[ContentTargetAuthoringRelationshipItem] = Field(default_factory=list)
    reason: str = ""


class ContentTargetAuthoringSurface(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["acf_flexible_content", "wordpress_post_content"]
    root_field: str
    layouts: list[ContentTargetAuthoringLayout] = Field(default_factory=list)
    schema_status: Literal["available", "observed", "unavailable"] = "unavailable"
    schema_digest: str | None = None
    schema_source_ref: str = ""
    schema_reason: str = ""
    source_acf_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    source_acf_fields_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    source_acf_root_field_count: int | None = Field(default=None, ge=0)
    source_acf_row_count: int | None = Field(default=None, ge=0)
    write_profile_status: Literal["ready", "not_required", "unavailable"] = "unavailable"
    write_profile_reason: str = ""


class ContentTargetContract(BaseModel):
    """Exact observed target facts; never an authorization to deliver."""

    model_config = ConfigDict(extra="forbid")

    environment: str
    object_id: str
    url: str
    post_type: str
    rest_endpoint: str = "pages"
    post_status: str
    modified: str
    template: str | None = None
    authority: Literal["observation_only"] = "observation_only"
    write_authorized: Literal[False] = False
    authoring_surface: ContentTargetAuthoringSurface | None = None


class ContentTargetObservationEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    connector_id: str
    object_id: str
    post_type: str
    url: str
    post_status: str
    modified: str
    observed_at: str


class ContentTargetDiscoveryCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    object_id: str
    url: str
    post_type: str
    post_status: str
    observation_evidence: ContentTargetObservationEvidence


class ContentTargetDiscoveryTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    object_id: str
    url: str
    post_type: str = "page"
    post_status: str
    template: str | None = None
    observed_surfaces: list[str] = Field(default_factory=list)
    target_contract: ContentTargetContract
    target_contract_digest: str = Field(min_length=64, max_length=64)
    observation_evidence: ContentTargetObservationEvidence


class ContentTargetDiscovery(BaseModel):
    """Read-only observation of a dev object, never an authorization to write."""

    model_config = ConfigDict(extra="forbid")

    response_type: Literal["content_target_discovery"] = "content_target_discovery"
    contract_version: Literal["content_target_discovery_v2"] = "content_target_discovery_v2"
    work_item_id: str
    public_url: str | None = None
    relation_status: Literal["partial", "ambiguous", "unavailable"]
    label: str
    reason: str
    target: ContentTargetDiscoveryTarget | None = None
    candidates: list[ContentTargetDiscoveryCandidate] = Field(default_factory=list)
    blocker_code: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)


_NativePostContentObservation = NativePostContentObservation


def build_content_target_discovery(work_item_id: str) -> ContentTargetDiscovery | None:
    decision = inventory_decision_for_work_item(
        work_item_id,
        read_material=False,
        allow_material_pending=True,
        include_all_metric_facts=False,
    )
    if decision is None:
        return None
    public_url = _public_url(decision)
    profile = build_wordpress_authoring_profile("wordpress_ekologus", include_dev_content=True)
    evidence_ids = sorted(set(profile.evidence_ids))
    if public_url is None:
        return ContentTargetDiscovery(
            work_item_id=work_item_id,
            relation_status="unavailable",
            label="Brakuje publicznego adresu do porównania",
            reason="Nie można sprawdzić relacji z dev bez publicznego adresu strony.",
            blocker_code="missing_public_canonical",
            evidence_ids=evidence_ids,
            caveats=[
                "Brak adresu nie blokuje pracy nad dokumentem, ale blokuje rozpoznanie targetu."
            ],
        )
    if profile.dev_content.status != "available":
        return _unavailable_dev_content_discovery(work_item_id, public_url, evidence_ids, profile)
    invalid_url_items = [
        item for item in profile.dev_content.items if not _safe_dev_observation_url(item.link)
    ]
    if invalid_url_items:
        return _invalid_dev_inventory_discovery(
            work_item_id,
            public_url,
            evidence_ids,
            "wordpress_dev_target_url_invalid",
            "Profil WordPress zwrócił malformed albo niezatwierdzony adres obiektu dev.",
        )
    invalid_id_items = [
        item
        for item in profile.dev_content.items
        if not positive_ascii_decimal(item.post_id)
    ]
    if invalid_id_items:
        return _invalid_dev_inventory_discovery(
            work_item_id,
            public_url,
            evidence_ids,
            "wordpress_dev_target_id_invalid",
            "Profil WordPress zwrócił nieprawidłowy identyfikator obiektu dev.",
        )
    matching_items = _unique_matching_items(profile.dev_content.items, public_url)
    if not matching_items:
        return ContentTargetDiscovery(
            work_item_id=work_item_id,
            public_url=public_url,
            relation_status="unavailable",
            label="Nie znaleziono odpowiadającego obiektu na dev",
            reason="WILQ nie znalazł na dev obiektu o tym samym adresie.",
            blocker_code="target_not_found",
            evidence_ids=evidence_ids,
            caveats=[
                "Różny adres nie jest dowodem, że target nie istnieje; "
                "relacja wymaga późniejszego potwierdzenia."
            ],
        )
    observed_at = utc_now().isoformat()
    if len(matching_items) > 1:
        candidates = [_candidate(item, profile, observed_at) for item in matching_items]
        return ContentTargetDiscovery(
            work_item_id=work_item_id,
            public_url=public_url,
            relation_status="ambiguous",
            label="Wykryto kilka obiektów dev o tym samym adresie",
            reason=(
                "WILQ nie wybiera samodzielnie między obiektami WordPress o tej samej ścieżce."
            ),
            candidates=candidates,
            evidence_ids=sorted(
                {
                    *evidence_ids,
                    *(item.observation_evidence.evidence_id for item in candidates),
                }
            ),
            caveats=[
                "Wybór konkretnego obiektu wymaga późniejszej decyzji człowieka.",
                "Ten odczyt nie odblokowuje ACF, tworzenia draftu ani publikacji.",
            ],
        )
    return _observed_target_discovery(
        work_item_id, public_url, evidence_ids, matching_items[0], profile, observed_at
    )


def _observed_target_discovery(
    work_item_id: str,
    public_url: str,
    evidence_ids: list[str],
    item: WordPressAuthoringDevContentObject,
    profile: WordPressAuthoringProfile,
    observed_at: str,
) -> ContentTargetDiscovery:
    target, native_observation = _observed_target(item, profile, observed_at)
    native_blocked = (
        native_observation is not None and native_observation.status == "unavailable"
    )
    target_reason = (
        " WILQ nie potwierdził odczytu natywnej treści WordPress: "
        + native_observation.reason
        if native_blocked and native_observation is not None
        else ""
    )
    target_caveats = [
        "Szczegóły dotyczą odczytanego obiektu dev, nie mapowania zatwierdzonego dokumentu.",
        "Ten odczyt nie odblokowuje ACF, tworzenia draftu ani publikacji.",
    ]
    if native_blocked and native_observation is not None:
        target_caveats.append(native_observation.reason)
    return ContentTargetDiscovery(
        work_item_id=work_item_id,
        public_url=public_url,
        relation_status="partial",
        label="Znaleziono stronę dev do sprawdzenia",
        reason=(
            "WILQ odczytał konkretną stronę na dev o tym samym adresie, ale sama zgodność "
            "adresu nie potwierdza jeszcze relacji ani prawa do zapisu."
            + target_reason
        ),
        target=target,
        blocker_code=(
            native_observation.blocker_code
            if native_blocked and native_observation is not None
            else None
        ),
        evidence_ids=sorted({*evidence_ids, target.observation_evidence.evidence_id}),
        caveats=target_caveats,
    )


def _observed_target(
    item: WordPressAuthoringDevContentObject,
    profile: WordPressAuthoringProfile,
    observed_at: str,
) -> tuple[ContentTargetDiscoveryTarget, _NativePostContentObservation | None]:
    acf_schema = (
        read_wordpress_acf_rest_schema("wordpress_ekologus", item) if item.acf_field_name else None
    )
    source_snapshot = _source_acf_snapshot(item)
    native_observation = (
        _native_post_content_observation(item)
        if not item.acf_field_name and item.content_type in {"page", "post"}
        else None
    )
    return _target(
        item,
        profile,
        observed_at,
        acf_schema=acf_schema,
        source_snapshot=source_snapshot,
        source_acf_digest=source_snapshot.root_digest if source_snapshot else None,
        source_acf_fields_digest=source_snapshot.fields_digest if source_snapshot else None,
        source_acf_root_field_count=len(source_snapshot.fields) if source_snapshot else None,
        source_acf_row_count=len(source_snapshot.rows) if source_snapshot else None,
        source_acf_rows=(source_snapshot.rows if source_snapshot else None),
        relationships_by_section=_observed_relationships(
            item,
            acf_schema=acf_schema,
            source_snapshot=source_snapshot,
        ),
        native_content_observation=native_observation,
    ), native_observation


def _public_url(decision: object) -> str | None:
    return next(
        (
            value.strip()
            for value in (
                getattr(decision, "source_public_url", None),
                getattr(decision, "final_canonical_url", None),
                getattr(decision, "page", None),
            )
            if value and value.strip()
        ),
        None,
    )


def _unique_matching_items(
    items: list[WordPressAuthoringDevContentObject], public_url: str
) -> list[WordPressAuthoringDevContentObject]:
    """Keep exact duplicate observations from becoming a false ambiguity.

    The dev inventory can contain the same REST object more than once when
    discovery sources overlap.  Ambiguity is meaningful only for distinct
    observations; collapsing merely the exact model payload preserves a real
    conflict in post type, URL, state, or authoring surface.
    """

    unique: dict[str, WordPressAuthoringDevContentObject] = {}
    for item in items:
        if _path(item.link) != _path(public_url):
            continue
        identity = json.dumps(
            item.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        unique.setdefault(identity, item)
    return list(unique.values())


def _unavailable_dev_content_discovery(
    work_item_id: str,
    public_url: str,
    evidence_ids: list[str],
    profile: WordPressAuthoringProfile,
) -> ContentTargetDiscovery:
    blocker = next(iter(profile.dev_content.blockers), None)
    return ContentTargetDiscovery(
        work_item_id=work_item_id,
        public_url=public_url,
        relation_status="unavailable",
        label="Nie można teraz odczytać obiektów dev",
        reason=(
            blocker.reason
            if blocker is not None
            else "WILQ nie ma potwierdzonego odczytu obiektów dev."
        ),
        blocker_code=(None if blocker is None else getattr(blocker, "code", None)),
        evidence_ids=evidence_ids,
        caveats=[
            blocker.next_step
            if blocker is not None
            else "Spróbuj ponownie, gdy odczyt inventory dev będzie dostępny.",
            "Brak odczytu nie jest dowodem, że odpowiadający obiekt dev nie istnieje.",
        ],
    )


def _invalid_dev_inventory_discovery(
    work_item_id: str,
    public_url: str,
    evidence_ids: list[str],
    blocker_code: str,
    reason: str,
) -> ContentTargetDiscovery:
    return ContentTargetDiscovery(
        work_item_id=work_item_id,
        public_url=public_url,
        relation_status="unavailable",
        label="Odrzucono nieprawidłowy obiekt dev",
        reason=reason,
        blocker_code=blocker_code,
        evidence_ids=evidence_ids,
        caveats=[
            "WILQ nie przekazuje niezatwierdzonego adresu ani identyfikatora do panelu "
            "lub odczytów vendorowych."
        ],
    )


def _target(
    item: WordPressAuthoringDevContentObject,
    profile: WordPressAuthoringProfile,
    observed_at: str,
    *,
    acf_schema: WordPressAcfRestSchema | None = None,
    source_snapshot: WordPressAcfFlexibleSnapshot | None = None,
    source_acf_digest: str | None = None,
    source_acf_fields_digest: str | None = None,
    source_acf_root_field_count: int | None = None,
    source_acf_row_count: int | None = None,
    source_acf_rows: list[dict[str, object]] | None = None,
    relationships_by_section: dict[int, list[ContentTargetAuthoringRelationship]] | None = None,
    native_content_observation: _NativePostContentObservation | None = None,
) -> ContentTargetDiscoveryTarget:
    contract = _target_contract(
        item,
        profile,
        acf_schema=acf_schema,
        source_acf_snapshot=source_snapshot,
        source_acf_digest=source_acf_digest,
        source_acf_fields_digest=source_acf_fields_digest,
        source_acf_root_field_count=source_acf_root_field_count,
        source_acf_row_count=source_acf_row_count,
        source_acf_rows=source_acf_rows,
        relationships_by_section=relationships_by_section,
        native_content_observation=native_content_observation,
    )
    digest = _digest(contract)
    observation = _observation_evidence(item, digest, observed_at)
    return ContentTargetDiscoveryTarget(
        object_id=item.post_id,
        url=item.link,
        post_type=item.content_type,
        post_status=item.status,
        template=item.template or None,
        observed_surfaces=[contract.authoring_surface.kind] if contract.authoring_surface else [],
        target_contract=contract,
        target_contract_digest=digest,
        observation_evidence=observation,
    )


def _candidate(
    item: WordPressAuthoringDevContentObject,
    profile: WordPressAuthoringProfile,
    observed_at: str,
) -> ContentTargetDiscoveryCandidate:
    digest = _digest(_target_contract(item, profile, allow_native_observation=False))
    return ContentTargetDiscoveryCandidate(
        object_id=item.post_id,
        url=item.link,
        post_type=item.content_type,
        post_status=item.status,
        observation_evidence=_observation_evidence(item, digest, observed_at),
    )


def _target_contract(
    item: WordPressAuthoringDevContentObject,
    profile: WordPressAuthoringProfile,
    *,
    acf_schema: WordPressAcfRestSchema | None = None,
    source_acf_snapshot: WordPressAcfFlexibleSnapshot | None = None,
    source_acf_digest: str | None = None,
    source_acf_fields_digest: str | None = None,
    source_acf_root_field_count: int | None = None,
    source_acf_row_count: int | None = None,
    source_acf_rows: list[dict[str, object]] | None = None,
    relationships_by_section: dict[int, list[ContentTargetAuthoringRelationship]] | None = None,
    native_content_observation: _NativePostContentObservation | None = None,
    allow_native_observation: bool = True,
) -> ContentTargetContract:
    surface = None
    if item.acf_field_name:
        writable_fields_by_layout, profile_reason = _acf_writable_fields(
            item,
            acf_schema=acf_schema,
            source_snapshot=source_acf_snapshot,
            source_acf_digest=source_acf_digest,
            source_acf_row_count=source_acf_row_count,
            source_acf_rows=source_acf_rows,
        )
        schema_layouts = (
            {layout.name: layout for layout in acf_schema.layouts} if acf_schema is not None else {}
        )
        surface = ContentTargetAuthoringSurface(
            kind="acf_flexible_content",
            root_field=item.acf_field_name,
            layouts=[
                ContentTargetAuthoringLayout(
                    name=section.layout_name,
                    section_index=section.section_index,
                    label=section.layout_label,
                    fields=section.field_names,
                    schema_fields=_schema_field_names(schema_layouts.get(section.layout_name)),
                    writable_fields=writable_fields_by_layout.get(section.layout_name, []),
                    relationships=(relationships_by_section or {}).get(section.section_index, []),
                )
                for section in item.sections
            ],
            schema_status=_acf_schema_status(
                item,
                acf_schema=acf_schema,
                source_snapshot=source_acf_snapshot,
            ),
            schema_digest=acf_schema.schema_digest if acf_schema is not None else None,
            schema_source_ref=_acf_schema_source_ref(
                item,
                acf_schema=acf_schema,
                source_snapshot=source_acf_snapshot,
            ),
            schema_reason=_acf_schema_reason(
                item,
                acf_schema=acf_schema,
                source_snapshot=source_acf_snapshot,
            ),
            source_acf_digest=source_acf_digest,
            source_acf_fields_digest=source_acf_fields_digest,
            source_acf_root_field_count=source_acf_root_field_count,
            source_acf_row_count=source_acf_row_count,
            write_profile_status=("ready" if writable_fields_by_layout else "unavailable"),
            write_profile_reason=_write_profile_reason(profile_reason, acf_schema),
        )
    elif (
        item.content_type in {"page", "post"}
        and (
            (
                native_content_observation is not None
                and native_content_observation.status == "available"
            )
            or (
                native_content_observation is None
                and allow_native_observation
                and _native_post_content_observed(item)
            )
        )
    ):
        surface = ContentTargetAuthoringSurface(
            kind="wordpress_post_content",
            root_field="content",
            layouts=[
                ContentTargetAuthoringLayout(
                    name="wordpress_post_content",
                    fields=["title", "content_html"],
                )
            ],
            schema_status="available",
            schema_reason="Treść wpisu ma bezpośredni kontrakt WordPress post_content.",
            write_profile_status="not_required",
            write_profile_reason="Treść wpisu WordPress ma bezpośredni, dokładny kontrakt HTML.",
        )
    return ContentTargetContract(
        environment=profile.authoring_target,
        object_id=item.post_id,
        url=item.link,
        post_type=item.content_type,
        rest_endpoint=item.rest_endpoint,
        post_status=item.status,
        modified=item.modified,
        template=item.template or None,
        authoring_surface=surface,
    )


def _write_profile_reason(
    profile_reason: str,
    acf_schema: WordPressAcfRestSchema | None,
) -> str:
    if acf_schema is None or acf_schema.status != "available":
        return profile_reason
    return (
        "Schema ACF została odczytana dla dokładnego obiektu dev. WILQ przed zapisem "
        "ponownie odczyta cały układ, zachowa niewybrane wartości i podmieni tylko "
        "zatwierdzone pola copy. "
        f"{profile_reason}"
    )


def _acf_schema_status(
    item: WordPressAuthoringDevContentObject,
    *,
    acf_schema: WordPressAcfRestSchema | None,
    source_snapshot: WordPressAcfFlexibleSnapshot | None,
) -> Literal["available", "observed", "unavailable"]:
    if acf_schema is not None and acf_schema.status == "available":
        return "available"
    if source_snapshot is not None and source_snapshot.root_field == item.acf_field_name:
        return "observed"
    return "unavailable"


def _acf_schema_source_ref(
    item: WordPressAuthoringDevContentObject,
    *,
    acf_schema: WordPressAcfRestSchema | None,
    source_snapshot: WordPressAcfFlexibleSnapshot | None,
) -> str:
    if acf_schema is not None and acf_schema.status == "available":
        return acf_schema.source_ref
    if source_snapshot is not None and source_snapshot.root_field == item.acf_field_name:
        return f"wp-json/wp/v2/{item.rest_endpoint}/{item.post_id} GET acf"
    return acf_schema.source_ref if acf_schema is not None else ""


def _acf_schema_reason(
    item: WordPressAuthoringDevContentObject,
    *,
    acf_schema: WordPressAcfRestSchema | None,
    source_snapshot: WordPressAcfFlexibleSnapshot | None,
) -> str:
    if acf_schema is not None and acf_schema.status == "available":
        return acf_schema.reason
    if source_snapshot is not None and source_snapshot.root_field == item.acf_field_name:
        return (
            "REST GET zwrócił rzeczywisty układ ACF dla dokładnego obiektu; "
            "OPTIONS nie dostarczył zagnieżdżonego schema, więc pola są obserwacją "
            "read-only, a nie samodzielną zgodą na zapis."
        )
    return acf_schema.reason if acf_schema is not None else ""


def _schema_field_names(layout: object) -> list[str]:
    fields = getattr(layout, "fields", [])
    return [field.name for field in fields if isinstance(getattr(field, "name", None), str)]


def _acf_writable_fields(
    item: WordPressAuthoringDevContentObject,
    *,
    acf_schema: WordPressAcfRestSchema | None,
    source_snapshot: WordPressAcfFlexibleSnapshot | None = None,
    source_acf_digest: str | None = None,
    source_acf_row_count: int | None = None,
    source_acf_rows: list[dict[str, object]] | None = None,
) -> tuple[dict[str, list[str]], str]:
    """Allow only observed direct string leaves for a preserve-first clone.

    The eventual draft does *not* construct a Flexible Content row.  It re-reads
    its exact source, keeps every untouched value and changes only these
    schema-confirmed scalar leaves.  Nested objects, arrays, links, media and
    unknown values remain outside this narrow authoring profile.
    """

    if acf_schema is not None and acf_schema.status == "available":
        if acf_schema.root_field != item.acf_field_name:
            return {}, "Odczytany schemat ACF dotyczy innego pola Flexible Content."
    elif source_snapshot is None or source_snapshot.root_field != item.acf_field_name:
        return {}, "Brakuje odczytanego układu ACF dla pola Flexible Content."
    if source_acf_digest is None or not source_acf_row_count or not source_acf_rows:
        return {}, "Odczyt targetu nie potwierdza pełnego digesta źródłowego pola ACF."
    if acf_schema is None or acf_schema.status != "available":
        return _observed_acf_writable_fields(
            item,
            source_snapshot=source_snapshot,
        )
    if acf_schema.root_field != item.acf_field_name:
        return {}, "Odczytany schemat ACF dotyczy innego pola Flexible Content."
    layouts_by_name = {layout.name: layout for layout in acf_schema.layouts}
    writable_by_layout: dict[str, list[str]] = {}
    for section in item.sections:
        if section.acf_field_name != item.acf_field_name:
            continue
        layout = layouts_by_name.get(section.layout_name)
        if layout is None:
            continue
        if section.section_index > len(source_acf_rows):
            continue
        source_row = source_acf_rows[section.section_index - 1]
        if source_row.get("acf_fc_layout") != section.layout_name:
            continue
        writable = sorted(
            field.name
            for field in layout.fields
            if (
                field.name in section.field_names
                and field.field_type == "string"
                and not field.sub_fields
                and field.name in source_row
                and isinstance(source_row[field.name], str)
            )
        )
        if not writable:
            continue
        writable_by_layout[section.layout_name] = writable
    if writable_by_layout:
        return (
            writable_by_layout,
            "Dokładny schema REST i digest źródła pozwalają zachować layout oraz "
            "zmienić wyłącznie bezpośrednie pola tekstowe.",
        )
    return (
        {},
        "Schema ACF nie potwierdza obserwowanego, bezpośredniego pola tekstowego "
        "do bezpiecznej podmiany.",
    )


def _observed_acf_writable_fields(
    item: WordPressAuthoringDevContentObject,
    *,
    source_snapshot: WordPressAcfFlexibleSnapshot | None,
) -> tuple[dict[str, list[str]], str]:
    if source_snapshot is None:
        return {}, "Brakuje odczytanego układu ACF dla pola Flexible Content."
    observed_writable_by_layout: dict[str, list[str]] = {}
    for section in item.sections:
        row_index = section.section_index - 1
        if row_index < 0 or row_index >= len(source_snapshot.rows):
            continue
        row = source_snapshot.rows[row_index]
        if row.get("acf_fc_layout") != section.layout_name:
            continue
        direct_text_candidates = {
            path
            for path in section.text_field_paths
            if "." not in path and path in section.field_names
        }
        writable = sorted(
            field
            for field in direct_text_candidates
            if isinstance(row.get(field), str) and row.get(field, "").strip()
        )
        if writable:
            observed_writable_by_layout[section.layout_name] = writable
    if observed_writable_by_layout:
        return (
            observed_writable_by_layout,
            "REST GET i digest źródła potwierdzają bezpośrednie pola tekstowe; "
            "klon przed ewentualnym zapisem ponownie zweryfikuje cały układ i typy liści.",
        )
    return (
        {},
        "REST GET potwierdza układ ACF, ale nie znalazł bezpośredniego pola tekstowego "
        "do bezpiecznej podmiany.",
    )


def _source_acf_snapshot(
    item: WordPressAuthoringDevContentObject,
) -> WordPressAcfFlexibleSnapshot | None:
    if not item.acf_field_name:
        return None
    try:
        return read_wordpress_acf_flexible_snapshot(
            "wordpress_ekologus",
            object_id=item.post_id,
            content_type=item.rest_endpoint,
            root_field=item.acf_field_name,
        )
    except ValueError:
        return None


def _observed_relationships(
    item: WordPressAuthoringDevContentObject,
    *,
    acf_schema: WordPressAcfRestSchema | None,
    source_snapshot: WordPressAcfFlexibleSnapshot | None,
) -> dict[int, list[ContentTargetAuthoringRelationship]]:
    """Expose only exact relationship IDs which current dev markup confirms.

    A relation observation is deliberately separate from the clone/write profile:
    an observed label helps an operator understand the page but never authorizes
    a relation-field mutation.
    """

    if (
        acf_schema is None
        or acf_schema.status != "available"
        or source_snapshot is None
        or acf_schema.root_field != item.acf_field_name
    ):
        return {}
    layouts_by_name = {layout.name: layout for layout in acf_schema.layouts}
    result: dict[int, list[ContentTargetAuthoringRelationship]] = {}
    for section in item.sections:
        if section.section_index < 1 or section.acf_field_name != item.acf_field_name:
            continue
        layout = layouts_by_name.get(section.layout_name)
        row_index = section.section_index - 1
        if layout is None or row_index >= len(source_snapshot.rows):
            continue
        source_row = source_snapshot.rows[row_index]
        if source_row.get("acf_fc_layout") != section.layout_name:
            continue
        relationships: list[ContentTargetAuthoringRelationship] = []
        for field in layout.fields:
            raw_ids = source_row.get(field.name)
            if (
                field.field_type != "integer_array"
                or not isinstance(raw_ids, list)
                or not raw_ids
                or any(
                    isinstance(value, bool) or not isinstance(value, int) or value <= 0
                    for value in raw_ids
                )
            ):
                continue
            if not _safe_dev_observation_url(item.link):
                relationships.append(
                    ContentTargetAuthoringRelationship(
                        field_name=field.name,
                        source_ref="",
                        reason="Adres dev relacji ACF nie spełnia wymagań bezpiecznego odczytu.",
                    )
                )
                continue
            unique_raw_ids = list(dict.fromkeys(raw_ids))
            observation = observe_wordpress_acf_panel_labels(item.link, unique_raw_ids)
            if observation.status != "available":
                relationships.append(
                    ContentTargetAuthoringRelationship(
                        field_name=field.name,
                        source_ref=observation.source_url,
                        reason=observation.reason,
                    )
                )
                continue
            relationships.append(
                ContentTargetAuthoringRelationship(
                    field_name=field.name,
                    status=observation.status,
                    source_ref=observation.source_url,
                    items=[
                        ContentTargetAuthoringRelationshipItem(
                            relationship_id=relationship_id,
                            label=observation.labels_by_id[relationship_id],
                        )
                        for relationship_id in unique_raw_ids
                    ],
                    reason=observation.reason,
                )
            )
        if relationships:
            result[section.section_index] = relationships
    return result


def _native_post_content_observed(item: WordPressAuthoringDevContentObject) -> bool:
    """Compatibility boolean for callers that only need surface availability."""
    return _native_post_content_observation(item).status == "available"


def _native_post_content_observation(
    item: WordPressAuthoringDevContentObject,
) -> _NativePostContentObservation:
    return observe_native_post_content(item)


def _safe_dev_observation_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    if not valid_url_port(parsed):
        return False
    return (
        parsed.scheme == "https"
        and wordpress_dev_host_allowed(value)
        and parsed.username is None
        and parsed.password is None
    )


def _digest(contract: ContentTargetContract) -> str:
    return sha256(
        json.dumps(
            contract.model_dump(mode="json"),
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def _observation_evidence(
    item: WordPressAuthoringDevContentObject,
    target_contract_digest: str,
    observed_at: str,
) -> ContentTargetObservationEvidence:
    payload = {
        "connector_id": "wordpress_ekologus",
        "object_id": item.post_id,
        "post_type": item.content_type,
        "url": item.link,
        "post_status": item.status,
        "modified": item.modified,
        "target_contract_digest": target_contract_digest,
    }
    evidence_id = (
        "ev_wordpress_target_observation_"
        + sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
        ).hexdigest()[:24]
    )
    return ContentTargetObservationEvidence(
        evidence_id=evidence_id,
        connector_id="wordpress_ekologus",
        object_id=item.post_id,
        post_type=item.content_type,
        url=item.link,
        post_status=item.status,
        modified=item.modified,
        observed_at=observed_at,
    )


def _path(value: str) -> str:
    try:
        path = urlparse(value).path.rstrip("/")
    except ValueError:
        return ""
    return path or "/"


__all__ = ["ContentTargetDiscovery", "build_content_target_discovery"]
