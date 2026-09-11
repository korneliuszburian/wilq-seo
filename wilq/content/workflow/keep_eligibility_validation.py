from __future__ import annotations

import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from wilq.content.knowledge.source_facts import ekologus_service_binding_urls
from wilq.content.workflow.target.target_mapping_snapshot import (
    TARGET_MAPPING_PATH,
    ContentTargetMappingSnapshotEnvelope,
)


def _digest(*chunks: str) -> str:
    return "".join(chunks)


_AUTHORING_SCHEMA_VERSION = "dev_authoring_inventory_v1"
_JOURNAL_SCHEMA_VERSION = "dev_content_state_journal_v1"
_LEDGER_SCHEMA_VERSION = "content_canonical_ledger_row_v1"
_CONTEXT_SCHEMA_VERSION = "content_keep_eligibility_context_v1"

_SOURCE_KEYS = (
    "authoring_inventory",
    "state_journal",
    "canonical_ledger",
    "context",
    "target_mapping_snapshot",
)
_PUBLIC_HOST = "www.ekologus.pl"
_DEV_HOST = "ekologus.dev.proudsite.pl"
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")

_EXPECTED_CONNECTORS = {
    "ads_evidence_id": "google_ads",
    "ahrefs_evidence_id": "ahrefs",
    "ga4_evidence_id": "google_analytics_4",
    "gsc_evidence_id": "google_search_console",
    "wordpress_read_evidence_id": "wordpress_ekologus",
}
_EXPECTED_SERVICE_BINDING_SOURCE = {
    "path": "wilq/content/knowledge/source_facts.py",
    "sha256": _digest(
        "23d13f63",
        "6a373a12",
        "d537ab1c",
        "b0b644c9",
        "1d135e6b",
        "be7d2936",
        "039ab5c2",
        "ef18f358",
    ),
    "commit": "441579ea",
    "map": "ekologus_service_binding_urls",
}


KeepEligibilityError = RuntimeError


@dataclass(frozen=True)
class SourceProvenance:
    source_ref: str
    sha256: str


@dataclass(frozen=True)
class KeepEligibilityInput:
    authoring_inventory: Mapping[str, Any]
    state_journal: Mapping[str, Any]
    canonical_ledger: Sequence[Mapping[str, Any]]
    context: Mapping[str, Any]
    target_mapping_snapshot: Mapping[str, Any]
    provenance: Mapping[str, SourceProvenance]
    expected_counts: tuple[tuple[str, int], ...]
    expected_primary_blocker_counts: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class _JournalData:
    rows: dict[str, Mapping[str, Any]]
    verified_draft_paths: frozenset[str]
    applied_action_paths: frozenset[str]
    source_pack_verification_ref: str


@dataclass(frozen=True)
class _ContextData:
    catalog_rows: dict[str, Mapping[str, Any]]
    service_cards: dict[str, Mapping[str, Any]]
    bindings_by_path: dict[str, tuple[Mapping[str, Any], ...]]
    connector_evidence: dict[str, Mapping[str, Any]]
    capture_completed_at: str


@dataclass(frozen=True)
class _ValidatedInput:
    authoring: dict[str, Mapping[str, Any]]
    journal: _JournalData
    ledger: dict[str, Mapping[str, Any]]
    context: _ContextData
    target_mapping_by_path: dict[str, ContentTargetMappingSnapshotEnvelope]
    keep_paths: set[str]


def _validate_input(source: KeepEligibilityInput) -> _ValidatedInput:
    _require_equal("provenance source keys", set(source.provenance), set(_SOURCE_KEYS))
    authoring = _validated_authoring(source.authoring_inventory)
    journal = _validated_journal(source.state_journal)
    ledger = _validated_ledger(source.canonical_ledger)
    context = _validated_context(source.context)
    keep_paths = _validated_keep_sets(authoring, journal.rows, ledger, context.catalog_rows)
    target_mapping = _validated_target_mapping_snapshot(source.target_mapping_snapshot)
    _cross_check_target_mapping_snapshot(
        target_mapping,
        authoring=authoring,
        journal=journal,
        context=context,
        keep_paths=keep_paths,
    )
    return _ValidatedInput(
        authoring=authoring,
        journal=journal,
        ledger=ledger,
        context=context,
        target_mapping_by_path={target_mapping.identity.path: target_mapping},
        keep_paths=keep_paths,
    )


def _validated_target_mapping_snapshot(
    payload: Mapping[str, Any],
) -> ContentTargetMappingSnapshotEnvelope:
    try:
        return ContentTargetMappingSnapshotEnvelope.model_validate(payload)
    except ValueError as error:
        raise KeepEligibilityError(
            "Target mapping snapshot does not satisfy the exact sanitised contract."
        ) from error


def _cross_check_target_mapping_snapshot(
    snapshot: ContentTargetMappingSnapshotEnvelope,
    *,
    authoring: Mapping[str, Mapping[str, Any]],
    journal: _JournalData,
    context: _ContextData,
    keep_paths: set[str],
) -> None:
    path = snapshot.identity.path
    if path not in keep_paths or path != TARGET_MAPPING_PATH:
        raise KeepEligibilityError("Target mapping snapshot is outside the exact keep set.")
    authoring_row = authoring[path]
    journal_row = journal.rows[path]
    preview = snapshot.preview
    if preview.target is None:
        raise KeepEligibilityError("Validated target snapshot lost its exact target.")
    contract = preview.target.target_contract
    surface = contract.authoring_surface
    if surface is None:
        raise KeepEligibilityError("Validated target snapshot lost its authoring surface.")
    expected_authoring = {
        "object_id": int(contract.object_id),
        "endpoint": contract.rest_endpoint,
        "post_type": contract.post_type,
        "authoring_mode": surface.kind,
        "status": contract.post_status,
        "modified": contract.modified,
    }
    authoring_url = _text(authoring_row.get("dev_url"), "target mapping authoring URL")
    if (
        any(authoring_row.get(key) != value for key, value in expected_authoring.items())
        or _url_path(authoring_url, _DEV_HOST) != _url_path(contract.url, _DEV_HOST)
        or not _acf_layouts_match(authoring_row, surface.layouts)
    ):
        raise KeepEligibilityError(
            "Target mapping snapshot does not match the retained authoring inventory."
        )
    expected_journal = {
        "planning_probe_work_item_id": snapshot.identity.work_item_id,
        "current_revision_id": snapshot.identity.revision_id,
        "current_revision_digest": preview.revision.content_digest,
        "current_revision_status": "approved",
    }
    if any(journal_row.get(key) != value for key, value in expected_journal.items()):
        raise KeepEligibilityError(
            "Target mapping snapshot does not match the retained approved revision."
        )
    matches = context.bindings_by_path.get(path, ())
    if len(matches) != 1:
        raise KeepEligibilityError(
            "Target mapping snapshot does not have one exact current service binding."
        )
    card_id = _text(matches[0].get("service_card_id"), "target mapping service card")
    card = context.service_cards[card_id]
    freshness = _text(card.get("freshness"), "target mapping service freshness").casefold()
    if (
        card.get("lifecycle_status") != "approved_current"
        or freshness.startswith(("stale", "rejected"))
        or not _string_list(card, "evidence_ids", "target mapping service card")
        or not _string_list(card, "source_connectors", "target mapping service card")
    ):
        raise KeepEligibilityError(
            "Target mapping snapshot service binding is not currently verified."
        )


def _acf_layouts_match(row: Mapping[str, Any], observed_layouts: Sequence[Any]) -> bool:
    retained_counts: Counter[str] = Counter()
    retained_fields: dict[str, set[str]] = defaultdict(set)
    for index, value in enumerate(_list(row, "acf_layouts", "target authoring row")):
        layout = _mapping(value, f"target authoring layout {index}")
        if layout.get("row_index") is not None:
            continue
        root_field = _text(layout.get("root_field"), f"target authoring layout {index}.root")
        if root_field != "flexible-home":
            raise KeepEligibilityError("Target authoring layout has a different root field.")
        name = _text(layout.get("layout_name"), f"target authoring layout {index}.name")
        retained_counts[name] += 1
        retained_fields[name].update(
            _string_list(layout, "field_names", f"target authoring layout {index}")
        )
    observed_counts = Counter(layout.name for layout in observed_layouts)
    return retained_counts == observed_counts and all(
        set(layout.fields).issubset(retained_fields[layout.name]) for layout in observed_layouts
    )


def _validated_authoring(payload: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    _require_schema(payload, _AUTHORING_SCHEMA_VERSION, "authoring inventory")
    _require_flags(
        payload,
        {
            "read_only": True,
            "source_refetch_performed": False,
            "generation_performed": False,
            "raw_body_retained": False,
            "publish_allowed": False,
            "write_authorized": False,
            "robot_ready": False,
        },
        "authoring inventory",
    )
    by_path: dict[str, Mapping[str, Any]] = {}
    for index, row_value in enumerate(_list(payload, "rows", "authoring inventory")):
        row = _mapping(row_value, f"authoring row {index}")
        path = _bare_path(_text(row.get("path"), f"authoring row {index}.path"))
        _add_unique(by_path, path, row, "authoring path")
        if row.get("final_disposition") == "keep":
            _require_flags(
                row,
                {
                    "new_generation_allowed": False,
                    "publish_allowed": False,
                    "write_authorized": False,
                    "robot_ready": False,
                    "raw_values_retained": False,
                },
                f"authoring row {path}",
            )
            _validate_keep_authoring_row(row, path)
    return {path: row for path, row in by_path.items() if row.get("final_disposition") == "keep"}


def _validate_keep_authoring_row(row: Mapping[str, Any], path: str) -> None:
    _require_bool(row, "rest_object_observed", True, f"keep authoring row {path}")
    _require_equal(f"keep authoring blocker for {path}", row.get("blocker"), None)
    object_id = row.get("object_id")
    if type(object_id) is not int or object_id <= 0:
        raise KeepEligibilityError(f"Authoring object_id must be positive for {path}.")
    endpoint = _text(row.get("endpoint"), f"keep authoring row {path}.endpoint")
    post_type = _text(row.get("post_type"), f"keep authoring row {path}.post_type")
    if {"posts": "post", "pages": "page", "uslugi": "uslugi"}.get(endpoint) != post_type:
        raise KeepEligibilityError(f"Authoring endpoint/type mismatch for {path}.")
    if row.get("authoring_mode") not in {"the_content", "acf_flexible_content"}:
        raise KeepEligibilityError(f"Unsupported authoring mode for {path}.")
    if (
        _url_path(_text(row.get("dev_url"), f"keep authoring row {path}.dev_url"), _DEV_HOST)
        != path
    ):
        raise KeepEligibilityError(f"Authoring dev URL/path mismatch for {path}.")


def _validated_journal(payload: Mapping[str, Any]) -> _JournalData:
    _require_schema(payload, _JOURNAL_SCHEMA_VERSION, "state journal")
    safety = _mapping(payload.get("safety"), "state journal.safety")
    _require_flags(
        safety,
        {
            "delete_performed": False,
            "deployment_performed": False,
            "env_values_read": False,
            "generation_performed": False,
            "new_generation_allowed": False,
            "private_packet_read": False,
            "read_only_run": True,
            "vendor_write_performed": False,
        },
        "state journal.safety",
    )
    rows: dict[str, Mapping[str, Any]] = {}
    for index, row_value in enumerate(_list(payload, "urls", "state journal")):
        row = _mapping(row_value, f"journal URL row {index}")
        path = _bare_path(_text(row.get("path"), f"journal URL row {index}.path"))
        _add_unique(rows, path, row, "journal path")
        if _url_path(_text(row.get("url"), f"journal URL row {path}.url"), _DEV_HOST) != path:
            raise KeepEligibilityError(f"Journal URL/path mismatch for {path}.")
        if row.get("final_disposition") == "keep":
            _require_flags(
                row,
                {"publish_allowed": False, "write_authorized": False, "robot_ready": False},
                f"journal URL row {path}",
            )
            _validate_keep_journal_row(row, path)
    sources = _mapping(payload.get("sources"), "state journal.sources")
    source_pack = _mapping(sources.get("source_pack_verification"), "source-pack source")
    _require_bool(source_pack, "read_only", True, "source-pack source")
    _require_equal("source-pack SHA mismatches", source_pack.get("sha256_mismatch"), 0)
    _require_equal("source-pack size mismatches", source_pack.get("size_mismatch"), 0)
    return _JournalData(
        rows={path: row for path, row in rows.items() if row.get("final_disposition") == "keep"},
        verified_draft_paths=frozenset(_verified_draft_paths(payload)),
        applied_action_paths=frozenset(_applied_action_paths(payload)),
        source_pack_verification_ref=_text(source_pack.get("path"), "source-pack source.path"),
    )


def _validate_keep_journal_row(row: Mapping[str, Any], path: str) -> None:
    evidence = _mapping(row.get("connector_evidence"), f"journal connector evidence {path}")
    _require_equal(f"connector evidence keys for {path}", set(evidence), set(_EXPECTED_CONNECTORS))
    for key in _EXPECTED_CONNECTORS:
        _text(evidence.get(key), f"journal connector evidence {path}.{key}")
    _text(row.get("keyword_planner_status"), f"journal URL row {path}.keyword_planner_status")
    work_item_id = row.get("planning_probe_work_item_id")
    if work_item_id is not None:
        _text(work_item_id, f"journal URL row {path}.planning_probe_work_item_id")
    revision_values = (
        row.get("current_revision_id"),
        row.get("current_revision_digest"),
        row.get("current_revision_status"),
    )
    if any(value is not None for value in revision_values):
        if any(value is None for value in revision_values):
            raise KeepEligibilityError(f"Partial current revision identity for {path}.")
        _text(revision_values[0], f"journal revision id {path}")
        _sha256(_text(revision_values[1], f"journal revision digest {path}"), f"revision {path}")
        _text(revision_values[2], f"journal revision status {path}")


def _verified_draft_paths(payload: Mapping[str, Any]) -> set[str]:
    result: set[str] = set()
    seen_revisions: set[str] = set()
    for index, value in enumerate(_list(payload, "drafts", "state journal")):
        row = _mapping(value, f"journal draft {index}")
        revision_id = _text(row.get("revision_id"), f"journal draft {index}.revision_id")
        _reject_duplicate(seen_revisions, revision_id, "journal draft revision_id")
        path = _bare_path(_text(row.get("path"), f"journal draft {index}.path"))
        if (
            row.get("canonical_disposition") == "keep"
            and row.get("state_class") == "dev_draft_verified"
        ):
            result.add(path)
    return result


def _applied_action_paths(payload: Mapping[str, Any]) -> set[str]:
    result: set[str] = set()
    seen_ids: set[str] = set()
    for index, value in enumerate(_list(payload, "mutation_audits", "state journal")):
        row = _mapping(value, f"journal mutation audit {index}")
        audit_id = _text(row.get("id"), f"journal mutation audit {index}.id")
        _reject_duplicate(seen_ids, audit_id, "journal mutation audit id")
        if row.get("status") != "applied" or row.get("external_write_attempted") is not True:
            continue
        binding_value = row.get("binding")
        if binding_value is None:
            continue
        binding = _mapping(binding_value, f"journal mutation audit {audit_id}.binding")
        _text(binding.get("work_item_id"), f"journal mutation audit {audit_id}.work_item_id")
        _text(binding.get("revision_id"), f"journal mutation audit {audit_id}.revision_id")
        public_url = _text(
            binding.get("final_canonical_url"),
            f"journal mutation audit {audit_id}.final_canonical_url",
        )
        result.add(_url_path(public_url, _PUBLIC_HOST))
    return result


def _validated_ledger(payload: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    if isinstance(payload, (str, bytes, bytearray)):
        raise KeepEligibilityError("Canonical ledger must be a sequence of objects.")
    by_path: dict[str, Mapping[str, Any]] = {}
    source_pack_ids: set[str] = set()
    for index, value in enumerate(payload):
        row = _mapping(value, f"canonical ledger row {index}")
        _require_schema(row, _LEDGER_SCHEMA_VERSION, f"canonical ledger row {index}")
        path = _url_path(_text(row.get("url"), f"ledger row {index}.url"), _DEV_HOST)
        _add_unique(by_path, path, row, "canonical ledger path")
        if row.get("final_disposition") == "keep":
            _require_flags(
                row,
                {"publish_allowed": False, "write_authorized": False, "robot_ready": False},
                f"canonical ledger row {path}",
            )
            _validate_keep_ledger_row(row, path, source_pack_ids)
    return {path: row for path, row in by_path.items() if row.get("final_disposition") == "keep"}


def _validate_keep_ledger_row(row: Mapping[str, Any], path: str, source_pack_ids: set[str]) -> None:
    public_url = _text(row.get("public_url"), f"ledger row {path}.public_url")
    if _url_path(public_url, _PUBLIC_HOST) != path:
        raise KeepEligibilityError(f"Ledger public URL/path mismatch for {path}.")
    owner_url = _text(row.get("canonical_owner_url"), f"ledger row {path}.canonical_owner_url")
    _require_equal(f"canonical owner for {path}", owner_url, public_url)
    _require_equal(
        f"canonical lineage for {path}", row.get("lineage_status"), "canonical_target_verified"
    )
    source_pack_id = _text(row.get("source_pack_id"), f"ledger row {path}.source_pack_id")
    _reject_duplicate(source_pack_ids, source_pack_id, "keep source_pack_id")
    if not _string_list(row, "evidence_ids", f"ledger row {path}"):
        raise KeepEligibilityError(f"Ledger evidence must be non-empty for {path}.")
    _string_list(row, "work_item_ids", f"ledger row {path}")


def _validated_context(payload: Mapping[str, Any]) -> _ContextData:
    _require_schema(payload, _CONTEXT_SCHEMA_VERSION, "eligibility context")
    capture_completed = _text(payload.get("capture_completed_at"), "context capture completion")
    _require_flags(
        _mapping(payload.get("safety"), "context.safety"),
        {
            "read_only": True,
            "api_get_only": True,
            "target_context_capture_performed": False,
            "vendor_read_performed": False,
            "vendor_write": False,
            "refresh": False,
            "private_material_read": False,
            "raw_material_read": False,
            "raw_values_retained": False,
        },
        "context.safety",
    )
    service_cards = _service_card_index(payload)
    return _ContextData(
        catalog_rows=_catalog_index(payload),
        service_cards=service_cards,
        bindings_by_path=_service_binding_index(payload, service_cards),
        connector_evidence=_connector_evidence_index(payload),
        capture_completed_at=capture_completed,
    )


def _service_card_index(payload: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    cards: dict[str, Mapping[str, Any]] = {}
    for index, value in enumerate(_list(payload, "service_cards", "eligibility context")):
        card = _mapping(value, f"service card {index}")
        card_id = _text(card.get("card_id"), f"service card {index}.card_id")
        _add_unique(cards, card_id, card, "service card id")
    _require_equal("service card count", len(cards), 11)
    return cards


def _service_binding_index(
    payload: Mapping[str, Any], cards: Mapping[str, Mapping[str, Any]]
) -> dict[str, tuple[Mapping[str, Any], ...]]:
    root = _mapping(payload.get("service_bindings"), "service bindings")
    _require_exact_int(root, "api_observed_url_count", 0, "service bindings")
    _require_exact_int(root, "current_code_url_count", 7, "service bindings")
    source = _mapping(root.get("current_code_source"), "service binding current code source")
    _require_equal(
        "service binding current code source keys",
        set(source),
        set(_EXPECTED_SERVICE_BINDING_SOURCE),
    )
    for key, expected in _EXPECTED_SERVICE_BINDING_SOURCE.items():
        _require_equal(f"service binding current code source {key}", source.get(key), expected)
    values = _list(root, "current_exact_bindings", "service bindings")
    _require_equal("current exact binding rows", len(values), 7)
    by_path: dict[str, list[Mapping[str, Any]]] = {}
    seen_rows: set[tuple[str, str]] = set()
    for index, value in enumerate(values):
        item = _mapping(value, f"service binding {index}")
        public_url = _text(item.get("public_url"), f"service binding {index}.public_url")
        card_id = _text(item.get("service_card_id"), f"service binding {index}.service_card_id")
        _reject_duplicate(seen_rows, (public_url, card_id), "service binding row")
        if card_id not in cards:
            raise KeepEligibilityError(f"Service binding references unknown card {card_id}.")
        by_path.setdefault(_url_path(public_url, _PUBLIC_HOST), []).append(item)
    expected_rows = {
        (public_url, card_id)
        for card_id in cards
        for public_url in ekologus_service_binding_urls(card_id)
    }
    _require_equal("service bindings from attested source map", seen_rows, expected_rows)
    return {path: tuple(items) for path, items in by_path.items()}


def _connector_evidence_index(payload: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for index, value in enumerate(_list(payload, "connector_evidence", "eligibility context")):
        item = _mapping(value, f"connector evidence {index}")
        evidence_id = _text(item.get("evidence_id"), f"connector evidence {index}.evidence_id")
        _add_unique(result, evidence_id, item, "connector evidence id")
    _require_equal("connector evidence count", len(result), 5)
    return result


def _catalog_index(payload: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    inventory = _mapping(payload.get("inventory"), "context inventory")
    rows: dict[str, Mapping[str, Any]] = {}
    for index, value in enumerate(_list(inventory, "rows", "context inventory")):
        item = _mapping(value, f"context inventory row {index}")
        path = _bare_path(_text(item.get("path"), f"context inventory row {index}.path"))
        _add_unique(rows, path, item, "context inventory path")
    return rows


def _validated_keep_sets(
    authoring: Mapping[str, Any],
    journal: Mapping[str, Any],
    ledger: Mapping[str, Any],
    catalog: Mapping[str, Any],
) -> set[str]:
    paths = set(authoring)
    for name, observed in (
        ("journal", set(journal)),
        ("ledger", set(ledger)),
        ("context", set(catalog)),
    ):
        _require_equal(f"57-keep set equality: {name}", observed, paths)
    return paths


def _bare_path(value: str) -> str:
    if not isinstance(value, str):
        raise KeepEligibilityError("URL path must be text.")
    segments = value.split("/")[1:]
    invalid = (
        not value.startswith("/")
        or value.startswith("//")
        or (value != "/" and value.endswith("/"))
        or (value != "/" and "" in segments)
        or any(segment in {".", ".."} for segment in segments)
        or any(token in value for token in ("%", "\\", "?", "#"))
        or any(
            character.isspace() or ord(character) < 32 or ord(character) == 127
            for character in value
        )
    )
    if invalid:
        raise KeepEligibilityError(f"Non-canonical exact path: {value!r}.")
    return value


def _url_path(value: str, expected_host: str) -> str:
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as error:
        raise KeepEligibilityError("Invalid exact URL.") from error
    path = parsed.path or "/"
    normalized = path if path == "/" else path.rstrip("/")
    invalid = (
        value != value.strip()
        or parsed.scheme != "https"
        or parsed.netloc != expected_host
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or bool(parsed.query or parsed.fragment)
        or (path != normalized and path != normalized + "/")
    )
    if invalid:
        raise KeepEligibilityError(f"URL must use exact https://{expected_host} origin.")
    return _bare_path(normalized)


def _require_schema(value: Mapping[str, Any], expected: str, context: str) -> None:
    _require_equal(f"{context} schema_version", value.get("schema_version"), expected)


def _mapping(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise KeepEligibilityError(f"{context} must be an object.")
    return value


def _list(value: Mapping[str, Any], key: str, context: str) -> list[Any]:
    result = value.get(key)
    if not isinstance(result, list):
        raise KeepEligibilityError(f"{context}.{key} must be an array.")
    return result


def _text(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise KeepEligibilityError(f"{context} must be non-empty trimmed text.")
    return value


def _require_bool(value: Mapping[str, Any], key: str, expected: bool, context: str) -> None:
    observed = value.get(key)
    if type(observed) is not bool or observed is not expected:
        raise KeepEligibilityError(f"{context}.{key} must be {str(expected).lower()}.")


def _require_flags(value: Mapping[str, Any], expected: Mapping[str, bool], context: str) -> None:
    for key, state in expected.items():
        _require_bool(value, key, state, context)


def _require_exact_int(value: Mapping[str, Any], key: str, expected: int, context: str) -> None:
    observed = value.get(key)
    if type(observed) is not int or observed != expected:
        raise KeepEligibilityError(f"{context}.{key} must be exactly {expected}.")


def _string_list(value: Mapping[str, Any], key: str, context: str) -> list[str]:
    result = _list(value, key, context)
    if any(not isinstance(item, str) or not item or item != item.strip() for item in result):
        raise KeepEligibilityError(f"{context}.{key} must contain non-empty trimmed strings.")
    if len(result) != len(set(result)):
        raise KeepEligibilityError(f"{context}.{key} contains a duplicate value.")
    return result


def _sha256(value: str, context: str) -> str:
    if _SHA256_PATTERN.fullmatch(value) is None:
        raise KeepEligibilityError(f"{context} must be an exact lowercase SHA-256.")
    return value


def _add_unique[K, V](target: dict[K, V], key: K, value: V, context: str) -> None:
    if key in target:
        raise KeepEligibilityError(f"Duplicate {context}: {key}")
    target[key] = value


def _reject_duplicate[T](seen: set[T], value: T, context: str) -> None:
    if value in seen:
        raise KeepEligibilityError(f"Duplicate {context}: {value}")
    seen.add(value)


def _require_equal(context: str, observed: Any, expected: Any) -> None:
    if observed != expected:
        raise KeepEligibilityError(f"{context} does not match the required contract.")
