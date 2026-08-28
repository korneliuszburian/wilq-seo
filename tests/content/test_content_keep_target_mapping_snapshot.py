from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from pydantic import ValidationError

from scripts.capture_content_target_mapping_snapshot import (
    CaptureError,
    _parse_json,
    main,
    render_snapshot,
)
from wilq.content.workflow.target.target_mapping_snapshot import (
    TARGET_MAPPING_AUTHORING_MODE,
    TARGET_MAPPING_DEV_URL,
    TARGET_MAPPING_ENDPOINT,
    TARGET_MAPPING_ENVIRONMENT,
    TARGET_MAPPING_LOCAL_BASE_URL,
    TARGET_MAPPING_OBJECT_ID,
    TARGET_MAPPING_PATH,
    TARGET_MAPPING_POST_TYPE,
    TARGET_MAPPING_PREVIEW_DIGEST,
    TARGET_MAPPING_PUBLIC_URL,
    TARGET_MAPPING_REVISION_ID,
    TARGET_MAPPING_ROOT_FIELD,
    TARGET_MAPPING_SCHEMA_SOURCE_REF,
    TARGET_MAPPING_SNAPSHOT_SCHEMA_VERSION,
    TARGET_MAPPING_WORK_ITEM_ID,
    ContentTargetMappingSnapshotEnvelope,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_PATH = REPO_ROOT / "docs/content-keep-target-mapping-snapshot-20260828.json"
ARTIFACT_PAYLOAD = json.loads(ARTIFACT_PATH.read_bytes())
STARTED_AT = datetime.fromisoformat(ARTIFACT_PAYLOAD["capture_started_at"].replace("Z", "+00:00"))
COMPLETED_AT = datetime.fromisoformat(
    ARTIFACT_PAYLOAD["capture_completed_at"].replace("Z", "+00:00")
)


def test_current_artifact_is_exact_validated_canonical_snapshot() -> None:
    payload = json.loads(ARTIFACT_PATH.read_bytes())
    snapshot = ContentTargetMappingSnapshotEnvelope.model_validate(payload)

    assert ARTIFACT_PATH.read_bytes() == render_snapshot(snapshot)
    assert snapshot.schema_version == TARGET_MAPPING_SNAPSHOT_SCHEMA_VERSION
    assert snapshot.artifact_role == "current_state"
    assert snapshot.identity.path == TARGET_MAPPING_PATH
    assert snapshot.request.method == "GET"
    assert snapshot.request.base_url == TARGET_MAPPING_LOCAL_BASE_URL
    assert snapshot.request.endpoint == TARGET_MAPPING_ENDPOINT
    assert snapshot.safety.vendor_read_performed is True
    assert snapshot.safety.raw_vendor_values_read_in_process is True
    assert snapshot.safety.vendor_write is False
    assert snapshot.safety.raw_response_retained is False
    assert snapshot.safety.raw_vendor_values_retained is False
    assert snapshot.safety.private_packet_read is False
    assert snapshot.preview.status == "ready_for_human_mapping"
    assert snapshot.preview.confirmation is None
    assert snapshot.preview.target is not None
    assert snapshot.preview.binding_digest is not None
    contract = snapshot.preview.target.target_contract
    assert (contract.url, contract.object_id, contract.post_type) == (
        TARGET_MAPPING_DEV_URL,
        TARGET_MAPPING_OBJECT_ID,
        TARGET_MAPPING_POST_TYPE,
    )
    assert contract.authority == "observation_only"
    assert contract.write_authorized is False
    assert contract.environment == TARGET_MAPPING_ENVIRONMENT
    assert contract.authoring_surface is not None
    assert contract.authoring_surface.kind == TARGET_MAPPING_AUTHORING_MODE
    assert contract.authoring_surface.root_field == TARGET_MAPPING_ROOT_FIELD
    assert contract.authoring_surface.schema_source_ref == TARGET_MAPPING_SCHEMA_SOURCE_REF
    assert _canonical_sha(snapshot.preview.model_dump(mode="json")) == TARGET_MAPPING_PREVIEW_DIGEST
    assert not _forbidden_structural_keys(payload)


def test_capture_uses_exactly_one_get_and_prints_only_safe_summary(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=_preview_payload())

    output = tmp_path / "snapshot.json"
    times = iter((STARTED_AT, COMPLETED_AT))
    result = main(
        ["--output", str(output)],
        transport=httpx.MockTransport(handler),
        now=lambda: next(times),
    )

    assert result == 0
    assert [(request.method, str(request.url)) for request in requests] == [
        ("GET", TARGET_MAPPING_LOCAL_BASE_URL + TARGET_MAPPING_ENDPOINT)
    ]
    snapshot = ContentTargetMappingSnapshotEnvelope.model_validate_json(output.read_bytes())
    assert output.read_bytes() == render_snapshot(snapshot)
    captured = capsys.readouterr()
    assert TARGET_MAPPING_PATH in captured.out
    assert snapshot.preview.binding_digest not in captured.out
    assert snapshot.preview.target is not None
    assert snapshot.preview.target.observation_evidence.evidence_id not in captured.out
    assert captured.err == ""


@pytest.mark.parametrize(
    ("flag", "value"),
    (
        ("--api-base", "http://localhost:8000"),
        ("--api-base", "https://127.0.0.1:8000"),
        ("--endpoint", TARGET_MAPPING_ENDPOINT + "/confirmation"),
        ("--endpoint", TARGET_MAPPING_ENDPOINT + "?refresh=true"),
    ),
)
def test_capture_refuses_wrong_host_or_route_before_any_request(
    flag: str,
    value: str,
    tmp_path: Path,
) -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=_preview_payload())

    assert (
        main(
            [flag, value, "--output", str(tmp_path / "snapshot.json")],
            transport=httpx.MockTransport(handler),
        )
        == 1
    )
    assert calls == 0


def test_existing_output_refuses_a_second_live_read(tmp_path: Path) -> None:
    output = tmp_path / "snapshot.json"
    output.write_text("already captured", encoding="utf-8")
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=_preview_payload())

    assert (
        main(
            ["--output", str(output)],
            transport=httpx.MockTransport(handler),
        )
        == 1
    )
    assert calls == 0
    assert output.read_text(encoding="utf-8") == "already captured"


@pytest.mark.parametrize(
    "field",
    (
        "path",
        "work_item",
        "revision",
        "object",
        "evidence",
        "revision_digest",
        "target_digest",
        "binding_digest",
        "environment",
        "schema_source_ref",
        "confirmation",
    ),
)
def test_tampered_identity_evidence_digest_or_confirmation_fails_closed(field: str) -> None:
    payload = _envelope_payload()
    if field == "path":
        payload["identity"]["path"] = "/inny-cel"
    elif field == "work_item":
        payload["preview"]["work_item_id"] = "content_work_item_other"
    elif field == "revision":
        payload["preview"]["revision"]["revision_id"] = "content_revision_other"
    elif field == "object":
        payload["preview"]["target"]["target_contract"]["object_id"] = "120"
    elif field == "evidence":
        payload["preview"]["target"]["observation_evidence"]["evidence_id"] = (
            "ev_wordpress_target_observation_" + "f" * 24
        )
    elif field == "revision_digest":
        payload["preview"]["revision"]["content_digest"] = "f" * 64
    elif field == "target_digest":
        payload["preview"]["target"]["target_contract_digest"] = "f" * 64
    elif field == "binding_digest":
        payload["preview"]["binding_digest"] = "f" * 64
    elif field == "environment":
        payload["preview"]["target"]["target_contract"]["environment"] = "production"
    elif field == "schema_source_ref":
        payload["preview"]["target"]["target_contract"]["authoring_surface"][
            "schema_source_ref"
        ] = "different OPTIONS source"
    else:
        payload["preview"]["confirmation"] = _confirmation(payload["preview"])

    with pytest.raises(ValidationError):
        ContentTargetMappingSnapshotEnvelope.model_validate(payload)


@pytest.mark.parametrize(
    "mutation",
    ("unobserved_writable_field", "component_omission", "component_label"),
)
def test_coherent_semantic_mutation_still_fails_closed(mutation: str) -> None:
    payload = _envelope_payload()
    preview = payload["preview"]
    if mutation == "unobserved_writable_field":
        writable_layout = next(
            layout
            for layout in preview["target"]["target_contract"]["authoring_surface"]["layouts"]
            if layout["writable_fields"]
        )
        writable_layout["writable_fields"] = ["unobserved_field"]
    elif mutation == "component_omission":
        preview["components"].pop()
    else:
        preview["components"][0]["label"] += " changed"
    _recompute_preview_lineage(preview)

    with pytest.raises(ValidationError):
        ContentTargetMappingSnapshotEnvelope.model_validate(payload)


@pytest.mark.parametrize("key", ("body", "content", "raw_values", "private_payload"))
def test_forbidden_raw_or_private_keys_fail_closed(key: str) -> None:
    payload = _envelope_payload()
    payload[key] = {"not": "retained"}

    with pytest.raises(ValidationError, match="forbidden raw key"):
        ContentTargetMappingSnapshotEnvelope.model_validate(payload)


def test_duplicate_keys_and_nonfinite_json_are_rejected() -> None:
    with pytest.raises(CaptureError, match="powtórzony klucz"):
        _parse_json(b'{"status":"one","status":"two"}')
    with pytest.raises(CaptureError, match="niefinitywne"):
        _parse_json(b'{"value":NaN}')


def test_unsafe_response_is_not_written_or_echoed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    unsafe = _preview_payload()
    raw_key = "raw_" + "values"
    field_name = "mapping_" + "secret"
    unsafe[raw_key] = {field_name: "do-not-print-this-value"}

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=unsafe)

    output = tmp_path / "snapshot.json"
    times = iter((STARTED_AT, COMPLETED_AT))
    assert (
        main(
            ["--output", str(output)],
            transport=httpx.MockTransport(handler),
            now=lambda: next(times),
        )
        == 1
    )
    captured = capsys.readouterr()
    assert "do-not-print-this-value" not in captured.out + captured.err
    assert not output.exists()


def _envelope_payload() -> dict[str, Any]:
    return {
        "schema_version": TARGET_MAPPING_SNAPSHOT_SCHEMA_VERSION,
        "artifact_role": "current_state",
        "capture_started_at": STARTED_AT.isoformat(),
        "capture_completed_at": COMPLETED_AT.isoformat(),
        "request": {
            "method": "GET",
            "base_url": TARGET_MAPPING_LOCAL_BASE_URL,
            "endpoint": TARGET_MAPPING_ENDPOINT,
            "runtime_sha_attested": False,
        },
        "identity": {
            "path": TARGET_MAPPING_PATH,
            "public_url": TARGET_MAPPING_PUBLIC_URL,
            "work_item_id": TARGET_MAPPING_WORK_ITEM_ID,
            "revision_id": TARGET_MAPPING_REVISION_ID,
        },
        "safety": {
            "read_only": True,
            "api_get_only": True,
            "vendor_read_performed": True,
            "raw_vendor_values_read_in_process": True,
            "vendor_write": False,
            "raw_response_retained": False,
            "raw_vendor_values_retained": False,
            "private_packet_read": False,
            "private_values_retained": False,
            "generation_performed": False,
            "publish_allowed": False,
            "write_authorized": False,
            "robot_ready": False,
        },
        "preview": _preview_payload(),
    }


def _preview_payload() -> dict[str, Any]:
    return deepcopy(ARTIFACT_PAYLOAD["preview"])


def _recompute_preview_lineage(preview: dict[str, Any]) -> None:
    target = preview["target"]
    contract = target["target_contract"]
    target_digest = _canonical_sha(contract)
    target["target_contract_digest"] = target_digest
    evidence = target["observation_evidence"]
    evidence_identity = {
        key: evidence[key]
        for key in ("connector_id", "object_id", "post_type", "url", "post_status", "modified")
    }
    evidence["evidence_id"] = (
        "ev_wordpress_target_observation_"
        + _canonical_sha({**evidence_identity, "target_contract_digest": target_digest})[:24]
    )
    preview["binding_digest"] = _canonical_sha(
        {
            "revision": preview["revision"],
            "target_contract_digest": target_digest,
            "components": preview["components"],
        }
    )


def _confirmation(preview: dict[str, Any]) -> dict[str, Any]:
    return {
        "confirmation_id": "content_target_mapping_confirmation_fixture",
        "confirmation_number": 1,
        "work_item_id": TARGET_MAPPING_WORK_ITEM_ID,
        "revision": deepcopy(preview["revision"]),
        "target_contract_digest": preview["target"]["target_contract_digest"],
        "binding_digest": preview["binding_digest"],
        "delivery_scope": "full_document",
        "selections": [
            {
                "component_id": "section:1",
                "layout_name": "content_data",
                "target_section_index": 1,
                "field_bindings": [{"source_field": "content_html", "target_field": "content"}],
            }
        ],
        "confirmed_by": "Wilku",
        "confirmation_digest": "d" * 64,
        "created_at": "2026-08-28T10:00:01+00:00",
    }


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _forbidden_structural_keys(value: Any) -> set[str]:
    forbidden = {"body", "content", "raw_value", "raw_values", "private_payload"}
    if isinstance(value, dict):
        return {
            *(key for key in value if key in forbidden),
            *(key for child in value.values() for key in _forbidden_structural_keys(child)),
        }
    if isinstance(value, list):
        return {key for child in value for key in _forbidden_structural_keys(child)}
    return set()
