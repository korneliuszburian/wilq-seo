#!/usr/bin/env python3
"""Emit a deterministic read-only inventory for one isolated SQLite file."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from wilq.storage.sqlite_schema_inventory import (
    SQLITE_SCHEMA_INVENTORY_CONTRACT,
    SqliteSchemaInventoryError,
    canonical_sqlite_schema_inventory_json,
    inspect_sqlite_schema,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        inventory = inspect_sqlite_schema(
            args.sqlite_path,
            application_sha256=args.application_sha256,
            seed_sha256=args.seed_sha256,
            expected_identity_sha256=args.expected_identity_sha256,
        )
    except (SqliteSchemaInventoryError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "contract_version": SQLITE_SCHEMA_INVENTORY_CONTRACT,
                    "error": str(exc),
                    "status": "blocked",
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 2
    print(canonical_sqlite_schema_inventory_json(inventory))
    if inventory.compatibility.status == "unsupported_schema_identity":
        return 3
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sqlite-path", type=Path, required=True)
    parser.add_argument(
        "--application-sha256",
        help="Already-authoritative application SHA-256; never inferred from the source.",
    )
    parser.add_argument(
        "--seed-sha256",
        help="Already-authoritative seed SHA-256; never inferred from database rows.",
    )
    parser.add_argument(
        "--expected-identity-sha256",
        help="Exact prior D1 identity required for post-S5 compatibility.",
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
