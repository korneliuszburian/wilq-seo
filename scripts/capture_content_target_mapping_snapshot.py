#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from pydantic import ValidationError

from wilq.content.workflow.target.target_mapping import ContentTargetMappingPreview
from wilq.content.workflow.target.target_mapping_snapshot import (
    TARGET_MAPPING_ENDPOINT,
    TARGET_MAPPING_LOCAL_BASE_URL,
    TARGET_MAPPING_PATH,
    TARGET_MAPPING_PUBLIC_URL,
    TARGET_MAPPING_REVISION_ID,
    TARGET_MAPPING_SNAPSHOT_SCHEMA_VERSION,
    TARGET_MAPPING_WORK_ITEM_ID,
    ContentTargetMappingSnapshotEnvelope,
)

DEFAULT_OUTPUT = "docs/content-keep-target-mapping-snapshot-20260828.json"
MAX_RESPONSE_BYTES = 1_000_000


class CaptureError(RuntimeError):
    pass


def render_snapshot(snapshot: ContentTargetMappingSnapshotEnvelope) -> bytes:
    try:
        rendered = json.dumps(
            snapshot.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise CaptureError("Snapshot nie jest kanonicznym JSON-em.") from error
    return (rendered + "\n").encode("utf-8")


def capture_snapshot(
    *,
    api_base: str,
    endpoint: str,
    transport: httpx.BaseTransport | None = None,
    now: Callable[[], datetime] | None = None,
) -> ContentTargetMappingSnapshotEnvelope:
    if api_base != TARGET_MAPPING_LOCAL_BASE_URL:
        raise CaptureError("Dozwolony jest wyłącznie lokalny adres API 127.0.0.1:8000.")
    if endpoint != TARGET_MAPPING_ENDPOINT:
        raise CaptureError("Dozwolony jest wyłącznie dokładny endpoint target-mapping GET.")
    clock = now or _utc_now
    started_at = _aware_utc(clock(), "Początek odczytu")
    preview = _fetch_preview(api_base, endpoint, transport=transport)
    completed_at = _aware_utc(clock(), "Koniec odczytu")
    try:
        return ContentTargetMappingSnapshotEnvelope.model_validate(
            {
                "schema_version": TARGET_MAPPING_SNAPSHOT_SCHEMA_VERSION,
                "artifact_role": "current_state",
                "capture_started_at": started_at,
                "capture_completed_at": completed_at,
                "request": {
                    "method": "GET",
                    "base_url": api_base,
                    "endpoint": endpoint,
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
                "preview": preview,
            }
        )
    except ValidationError as error:
        raise CaptureError(
            "Odpowiedź API nie spełnia dokładnego bezpiecznego kontraktu snapshotu."
        ) from error


def main(
    argv: Sequence[str] | None = None,
    *,
    transport: httpx.BaseTransport | None = None,
    now: Callable[[], datetime] | None = None,
) -> int:
    args = _parser().parse_args(argv)
    output = Path(args.output)
    try:
        if output.exists():
            raise CaptureError("Artefakt już istnieje; ponowny live odczyt jest zabroniony.")
        snapshot = capture_snapshot(
            api_base=args.api_base,
            endpoint=args.endpoint,
            transport=transport,
            now=now,
        )
        with output.open("xb") as stream:
            stream.write(render_snapshot(snapshot))
        print(
            "Zapisano sanitised podgląd mapowania dla "
            f"{TARGET_MAPPING_PATH}; status: gotowy wyłącznie do potwierdzenia człowieka."
        )
    except CaptureError as error:
        print(f"Błąd snapshotu target-mapping: {error}", file=sys.stderr)
        return 1
    except OSError:
        print(
            "Błąd snapshotu target-mapping: operacja plikowa nie powiodła się.",
            file=sys.stderr,
        )
        return 1
    return 0


def _fetch_preview(
    api_base: str,
    endpoint: str,
    *,
    transport: httpx.BaseTransport | None,
) -> ContentTargetMappingPreview:
    try:
        with httpx.Client(
            base_url=api_base,
            timeout=30.0,
            follow_redirects=False,
            transport=transport,
        ) as client:
            response = client.get(endpoint, headers={"Accept": "application/json"})
    except httpx.HTTPError as error:
        raise CaptureError("Lokalny odczyt GET nie powiódł się.") from error
    if response.status_code != 200:
        raise CaptureError("Lokalny endpoint GET nie zwrócił statusu 200.")
    media_type = response.headers.get("content-type", "").split(";", 1)[0].strip().casefold()
    if media_type != "application/json":
        raise CaptureError("Lokalny endpoint GET nie zwrócił JSON-u.")
    if len(response.content) > MAX_RESPONSE_BYTES:
        raise CaptureError("Odpowiedź API przekracza bezpieczny limit rozmiaru.")
    payload = _parse_json(response.content)
    if not isinstance(payload, Mapping):
        raise CaptureError("Odpowiedź API nie jest obiektem JSON.")
    if (
        payload.get("response_type") != "content_target_mapping_preview"
        or payload.get("contract_version") != "content_target_mapping_preview_v1"
    ):
        raise CaptureError("Odpowiedź API nie ma jawnego kontraktu preview mapowania.")
    try:
        return ContentTargetMappingPreview.model_validate(payload)
    except ValidationError as error:
        raise CaptureError("Odpowiedź API nie jest kanonicznym preview mapowania.") from error


def _parse_json(raw: bytes) -> Any:
    try:
        return json.loads(
            raw,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CaptureError("Odpowiedź API nie jest poprawnym JSON-em UTF-8.") from error


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CaptureError("Odpowiedź API zawiera powtórzony klucz JSON.")
        result[key] = value
    return result


def _reject_nonfinite(_: str) -> None:
    raise CaptureError("Odpowiedź API zawiera niedozwolone dane niefinitywne.")


def _aware_utc(value: datetime, context: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(None):
        raise CaptureError(f"{context} musi używać UTC.")
    return value


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Zapisuje jeden sanitised read-only snapshot target-mapping."
    )
    parser.add_argument("--api-base", default=TARGET_MAPPING_LOCAL_BASE_URL)
    parser.add_argument("--endpoint", default=TARGET_MAPPING_ENDPOINT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
