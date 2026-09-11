#!/usr/bin/env python3
"""Create or apply the bounded S5 legacy Stop reconciliation contract.

Both commands require an explicit SQLite path. ``manifest`` uses a mode=ro
connection. ``apply`` is a dry-run unless the caller also supplies the exact
manifest/count/backup gates and ``--authorize-mutation`` maintenance approval.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from wilq.codex.stop_reconciliation import (
    StopReconciliationFailureReceipt,
    StopReconciliationManifestError,
    StopReconciliationStorageError,
    apply_stop_reconciliation,
    create_stop_reconciliation_manifest,
    plan_stop_reconciliation,
    read_manifest,
    write_manifest,
)
from wilq.storage.local_state import LocalStateStore
from wilq.storage.local_state_stop_reconciliation import SqliteStopReconciliationSource


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "manifest":
            return _create_manifest(args)
        return _apply_manifest(args)
    except StopReconciliationManifestError as exc:
        print(
            StopReconciliationFailureReceipt(
                status="blocked",
                error=str(exc),
                rollback_result=exc.rollback_result,
            ).model_dump_json()
        )
        return 2
    except StopReconciliationStorageError as exc:
        print(
            StopReconciliationFailureReceipt(
                status="failed",
                error=str(exc),
                rollback_result=exc.rollback_result,
            ).model_dump_json()
        )
        return 4


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    manifest = subparsers.add_parser("manifest", help="create a read-only immutable manifest")
    manifest.add_argument("--state-db", type=Path, required=True)
    manifest.add_argument("--output", type=Path, required=True)
    manifest.add_argument("--source-fixed-point", required=True)
    manifest.add_argument("--generated-at", type=_aware_datetime, required=True)
    manifest.add_argument("--run-id", action="append", required=True)

    apply = subparsers.add_parser(
        "apply",
        help="dry-run by default; mutate only with every gate and explicit authorization",
    )
    apply.add_argument("--state-db", type=Path, required=True)
    apply.add_argument("--manifest", type=Path, required=True)
    apply.add_argument("--manifest-sha256", required=True)
    apply.add_argument("--expected-count", type=int, required=True)
    apply.add_argument("--backup", type=Path, required=True)
    apply.add_argument("--batch-id", required=True)
    apply.add_argument("--authorize-mutation", action="store_true")
    return parser


def _create_manifest(args: argparse.Namespace) -> int:
    manifest = create_stop_reconciliation_manifest(
        SqliteStopReconciliationSource(args.state_db),
        run_ids=args.run_id,
        source_fixed_point=args.source_fixed_point,
        generated_at=args.generated_at,
    )
    digest = write_manifest(args.output, manifest)
    print(
        json.dumps(
            {
                "status": "manifest_created",
                "manifest": str(args.output),
                "manifest_sha256": digest,
                "expected_count": manifest.expected_count,
            },
            ensure_ascii=False,
        )
    )
    return 0


def _apply_manifest(args: argparse.Namespace) -> int:
    manifest = read_manifest(args.manifest)
    store = LocalStateStore(args.state_db)
    if not args.authorize_mutation:
        dry_run_receipt = plan_stop_reconciliation(
            store,
            manifest=manifest,
            batch_id=args.batch_id,
            backup_path=args.backup,
            expected_count=args.expected_count,
            expected_manifest_sha256=args.manifest_sha256,
        )
        print(dry_run_receipt.model_dump_json())
        return 3 if dry_run_receipt.status == "dry_run_partial" else 0
    apply_receipt = apply_stop_reconciliation(
        store,
        manifest=manifest,
        batch_id=args.batch_id,
        backup_path=args.backup,
        mutation_authorized=True,
        expected_count=args.expected_count,
        expected_manifest_sha256=args.manifest_sha256,
    )
    print(apply_receipt.model_dump_json())
    return 3 if apply_receipt.status == "partial" else 0


def _aware_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("generated-at must be an ISO-8601 datetime") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("generated-at must include a timezone")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
