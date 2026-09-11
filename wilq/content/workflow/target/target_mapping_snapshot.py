from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, model_validator

from wilq.content.workflow.target.target_mapping import ContentTargetMappingPreview
from wilq.content.workflow.target.target_mapping_source_fields import source_field_specs

TARGET_MAPPING_SNAPSHOT_SCHEMA_VERSION: Literal["content_target_mapping_snapshot_v1"] = (
    "content_target_mapping_snapshot_v1"
)
TARGET_MAPPING_PATH = "/oferta/opracowania-dokumentacji-ekspertyz"
TARGET_MAPPING_PUBLIC_URL = "https://www.ekologus.pl/oferta/opracowania-dokumentacji-ekspertyz/"
TARGET_MAPPING_DEV_URL = (
    "https://ekologus.dev.proudsite.pl/oferta/opracowania-dokumentacji-ekspertyz/"
)
TARGET_MAPPING_WORK_ITEM_ID = (
    "content_work_item_content_decision_https___www_ekologus_pl_oferta_"
    "opracowania_dokumentacji_ekspertyz"
)
TARGET_MAPPING_REVISION_ID = "content_revision_59b7b2943d71428192a6f1e8f164a0af"
TARGET_MAPPING_REVISION_DIGEST = "".join(
    (
        "4a0168f2",
        "6e42148a",
        "169a4b39",
        "6a53f149",
        "1bb288ac",
        "c7600419",
        "05872bb8",
        "31539f94",
    )
)
TARGET_MAPPING_PREVIEW_DIGEST = "".join(
    (
        "79169faa",
        "bed06b6a",
        "aede855e",
        "add4f2ed",
        "b4d27a8b",
        "120d8c57",
        "5d0b578a",
        "c8cdbb01",
    )
)
TARGET_MAPPING_ENDPOINT = (
    f"/api/content/work-items/{TARGET_MAPPING_WORK_ITEM_ID}/draft-revisions/"
    f"{TARGET_MAPPING_REVISION_ID}/target-mapping"
)
TARGET_MAPPING_LOCAL_BASE_URL = "http://127.0.0.1:8000"
TARGET_MAPPING_OBJECT_ID = "119"
TARGET_MAPPING_POST_TYPE = "uslugi"
TARGET_MAPPING_AUTHORING_MODE = "acf_flexible_content"
TARGET_MAPPING_ROOT_FIELD = "flexible-home"
TARGET_MAPPING_ENVIRONMENT = "staging"
TARGET_MAPPING_SCHEMA_SOURCE_REF = "wp-json/wp/v2/uslugi/119 OPTIONS"
_MAX_CAPTURE_WINDOW = timedelta(minutes=2)

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
_FORBIDDEN_KEYS = frozenset(
    {
        "body",
        "content",
        "private_payload",
        "private_value",
        "private_values",
        "raw_response",
        "raw_value",
        "raw_values",
        "response_body",
        "response_content",
        "secret",
        "secrets",
        "token",
    }
)


class ContentTargetMappingSnapshotRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: Literal["GET"] = "GET"
    base_url: str
    endpoint: str
    runtime_sha_attested: Literal[False] = False


class ContentTargetMappingSnapshotIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    public_url: str
    work_item_id: str
    revision_id: str


class ContentTargetMappingSnapshotSafety(BaseModel):
    model_config = ConfigDict(extra="forbid")

    read_only: Literal[True] = True
    api_get_only: Literal[True] = True
    vendor_read_performed: Literal[True] = True
    raw_vendor_values_read_in_process: Literal[True] = True
    vendor_write: Literal[False] = False
    raw_response_retained: Literal[False] = False
    raw_vendor_values_retained: Literal[False] = False
    private_packet_read: Literal[False] = False
    private_values_retained: Literal[False] = False
    generation_performed: Literal[False] = False
    publish_allowed: Literal[False] = False
    write_authorized: Literal[False] = False
    robot_ready: Literal[False] = False


class ContentTargetMappingSnapshotEnvelope(BaseModel):
    """One sanitised GET observation; never a confirmation or write authority."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["content_target_mapping_snapshot_v1"] = (
        TARGET_MAPPING_SNAPSHOT_SCHEMA_VERSION
    )
    artifact_role: Literal["current_state"] = "current_state"
    capture_started_at: AwareDatetime
    capture_completed_at: AwareDatetime
    request: ContentTargetMappingSnapshotRequest
    identity: ContentTargetMappingSnapshotIdentity
    safety: ContentTargetMappingSnapshotSafety
    preview: ContentTargetMappingPreview

    @model_validator(mode="before")
    @classmethod
    def reject_unmodelled_payload(cls, value: Any) -> Any:
        _reject_forbidden_keys(value)
        if isinstance(value, Mapping) and isinstance(value.get("preview"), Mapping):
            preview = value["preview"]
            if (
                preview.get("response_type") != "content_target_mapping_preview"
                or preview.get("contract_version") != "content_target_mapping_preview_v1"
            ):
                raise ValueError("Snapshot must retain explicit preview discriminators.")
        return value

    @model_validator(mode="after")
    def require_exact_observation(self) -> ContentTargetMappingSnapshotEnvelope:
        if self.capture_started_at.utcoffset() != UTC.utcoffset(None) or (
            self.capture_completed_at.utcoffset() != UTC.utcoffset(None)
        ):
            raise ValueError("Target mapping capture window must use UTC.")
        if self.capture_completed_at < self.capture_started_at:
            raise ValueError("Target mapping capture window is reversed.")
        if self.capture_completed_at - self.capture_started_at > _MAX_CAPTURE_WINDOW:
            raise ValueError("Target mapping capture window is too wide.")
        if self.request.model_dump() != {
            "method": "GET",
            "base_url": TARGET_MAPPING_LOCAL_BASE_URL,
            "endpoint": TARGET_MAPPING_ENDPOINT,
            "runtime_sha_attested": False,
        }:
            raise ValueError("Target mapping snapshot must use the exact local GET.")
        if self.identity.model_dump() != {
            "path": TARGET_MAPPING_PATH,
            "public_url": TARGET_MAPPING_PUBLIC_URL,
            "work_item_id": TARGET_MAPPING_WORK_ITEM_ID,
            "revision_id": TARGET_MAPPING_REVISION_ID,
        }:
            raise ValueError("Target mapping snapshot identity is not exact.")
        validate_exact_mapping_preview(
            self.preview,
            capture_started_at=self.capture_started_at,
            capture_completed_at=self.capture_completed_at,
        )
        return self


def validate_exact_mapping_preview(
    preview: ContentTargetMappingPreview,
    *,
    capture_started_at: datetime,
    capture_completed_at: datetime,
) -> None:
    target = preview.target
    if (
        preview.status != "ready_for_human_mapping"
        or preview.work_item_id != TARGET_MAPPING_WORK_ITEM_ID
        or preview.revision.revision_id != TARGET_MAPPING_REVISION_ID
        or preview.revision.content_digest != TARGET_MAPPING_REVISION_DIGEST
        or target is None
        or preview.binding_digest is None
        or preview.confirmation is not None
        or bool(preview.blockers)
        or not preview.components
    ):
        raise ValueError("Target mapping preview is not awaiting exact human mapping.")
    _validate_target(target)
    _validate_components(preview)
    _validate_lineage(
        preview,
        capture_started_at=capture_started_at,
        capture_completed_at=capture_completed_at,
    )
    if _canonical_sha256(preview.model_dump(mode="json")) != TARGET_MAPPING_PREVIEW_DIGEST:
        raise ValueError("Target mapping preview does not match the pinned canonical capture.")


def _validate_target(target: Any) -> None:
    contract = target.target_contract
    surface = contract.authoring_surface
    if (
        contract.object_id != TARGET_MAPPING_OBJECT_ID
        or contract.url != TARGET_MAPPING_DEV_URL
        or contract.environment != TARGET_MAPPING_ENVIRONMENT
        or contract.post_type != TARGET_MAPPING_POST_TYPE
        or contract.rest_endpoint != TARGET_MAPPING_POST_TYPE
        or contract.authority != "observation_only"
        or contract.write_authorized is not False
        or surface is None
        or surface.kind != TARGET_MAPPING_AUTHORING_MODE
        or surface.root_field != TARGET_MAPPING_ROOT_FIELD
        or surface.schema_status != "available"
        or surface.schema_source_ref != TARGET_MAPPING_SCHEMA_SOURCE_REF
        or surface.write_profile_status != "ready"
        or not surface.layouts
    ):
        raise ValueError("Target mapping preview does not describe the exact dev surface.")
    for digest in (
        surface.schema_digest,
        surface.source_acf_digest,
        surface.source_acf_fields_digest,
    ):
        if not isinstance(digest, str) or _SHA256_PATTERN.fullmatch(digest) is None:
            raise ValueError("Target mapping surface is missing an exact source digest.")
    if any(
        not set(layout.writable_fields).issubset(
            set(layout.fields).intersection(layout.schema_fields)
        )
        for layout in surface.layouts
    ):
        raise ValueError(
            "Target mapping writable fields are not exactly observed and schema-backed."
        )
    section_indexes = [layout.section_index for layout in surface.layouts]
    if (
        type(surface.source_acf_root_field_count) is not int
        or surface.source_acf_root_field_count < 1
        or type(surface.source_acf_row_count) is not int
        or surface.source_acf_row_count < 1
        or not surface.schema_source_ref
        or not any(layout.writable_fields for layout in surface.layouts)
        or any(index is None for index in section_indexes)
        or len(section_indexes) != len(set(section_indexes))
    ):
        raise ValueError("Target mapping surface is not an exact writable observation.")


def _validate_components(preview: ContentTargetMappingPreview) -> None:
    if preview.target is None:
        raise ValueError("Target mapping components require an exact target.")
    surface = preview.target.target_contract.authoring_surface
    if surface is None:
        raise ValueError("Target mapping components require an authoring surface.")
    available_layouts = [layout.name for layout in surface.layouts]
    component_ids = [component.component_id for component in preview.components]
    if len(component_ids) != len(set(component_ids)):
        raise ValueError("Target mapping component IDs must be unique.")
    for component in preview.components:
        expected_fields = [
            {"key": key, "label": label} for key, label in source_field_specs(component.kind)
        ]
        if (
            component.status != "human_only"
            or component.target_root_field != TARGET_MAPPING_ROOT_FIELD
            or component.available_layouts != available_layouts
            or [field.model_dump() for field in component.source_fields] != expected_fields
        ):
            raise ValueError("Target mapping components are not exact human-only choices.")


def _validate_lineage(
    preview: ContentTargetMappingPreview,
    *,
    capture_started_at: datetime,
    capture_completed_at: datetime,
) -> None:
    if preview.target is None or preview.binding_digest is None:
        raise ValueError("Target mapping lineage requires an exact target and binding.")
    target = preview.target
    contract = target.target_contract
    if target.target_contract_digest != _canonical_sha256(contract.model_dump(mode="json")):
        raise ValueError("Target mapping contract digest is not canonical.")
    evidence = target.observation_evidence
    evidence_identity = {
        "connector_id": evidence.connector_id,
        "object_id": evidence.object_id,
        "post_type": evidence.post_type,
        "url": evidence.url,
        "post_status": evidence.post_status,
        "modified": evidence.modified,
    }
    if evidence_identity != {
        "connector_id": "wordpress_ekologus",
        "object_id": contract.object_id,
        "post_type": contract.post_type,
        "url": contract.url,
        "post_status": contract.post_status,
        "modified": contract.modified,
    }:
        raise ValueError("Target observation evidence does not match the exact contract.")
    expected_evidence_id = (
        "ev_wordpress_target_observation_"
        + _canonical_sha256(
            {**evidence_identity, "target_contract_digest": target.target_contract_digest}
        )[:24]
    )
    observed_at = _aware_datetime(evidence.observed_at, "target observation timestamp")
    if (
        evidence.evidence_id != expected_evidence_id
        or not capture_started_at <= observed_at <= capture_completed_at
    ):
        raise ValueError("Target observation evidence is not canonical for this capture.")
    expected_binding = _canonical_sha256(
        {
            "revision": preview.revision.model_dump(mode="json"),
            "target_contract_digest": target.target_contract_digest,
            "components": [component.model_dump(mode="json") for component in preview.components],
        }
    )
    if preview.binding_digest != expected_binding:
        raise ValueError("Target mapping binding digest is not canonical.")


def _reject_forbidden_keys(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if isinstance(key, str) and key.casefold() in _FORBIDDEN_KEYS:
                raise ValueError("Target mapping snapshot contains a forbidden raw key.")
            _reject_forbidden_keys(child)
    elif isinstance(value, list):
        for child in value:
            _reject_forbidden_keys(child)


def _canonical_sha256(value: Any) -> str:
    return sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _aware_datetime(value: str, context: str) -> datetime:
    try:
        observed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{context} is not an ISO datetime.") from error
    if observed.tzinfo is None or observed.utcoffset() != UTC.utcoffset(None):
        raise ValueError(f"{context} must use UTC.")
    return observed


__all__ = [
    "ContentTargetMappingSnapshotEnvelope",
    "TARGET_MAPPING_AUTHORING_MODE",
    "TARGET_MAPPING_DEV_URL",
    "TARGET_MAPPING_ENDPOINT",
    "TARGET_MAPPING_ENVIRONMENT",
    "TARGET_MAPPING_LOCAL_BASE_URL",
    "TARGET_MAPPING_OBJECT_ID",
    "TARGET_MAPPING_PATH",
    "TARGET_MAPPING_POST_TYPE",
    "TARGET_MAPPING_PREVIEW_DIGEST",
    "TARGET_MAPPING_PUBLIC_URL",
    "TARGET_MAPPING_REVISION_DIGEST",
    "TARGET_MAPPING_REVISION_ID",
    "TARGET_MAPPING_ROOT_FIELD",
    "TARGET_MAPPING_SCHEMA_SOURCE_REF",
    "TARGET_MAPPING_SNAPSHOT_SCHEMA_VERSION",
    "TARGET_MAPPING_WORK_ITEM_ID",
]
