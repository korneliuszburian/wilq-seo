from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from . import _contract as contract
from ._models import AdjudicationExpectations


def validate_authorities(
    ledger: Sequence[Mapping[str, Any]],
    journal: Mapping[str, Any],
    expectations: AdjudicationExpectations,
) -> tuple[dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    if isinstance(ledger, (str, bytes, bytearray)) or len(ledger) != expectations.ledger_rows:
        raise contract.AdjudicationError("Canonical ledger row count does not match the contract.")
    ledger_rows: dict[str, Mapping[str, Any]] = {}
    public_urls: set[str] = set()
    operational_counts: Counter[str] = Counter()
    for index, raw in enumerate(ledger):
        row = contract.object_value(raw, f"ledger row {index}")
        if row.get("schema_version") != contract.LEDGER_SCHEMA_VERSION:
            raise contract.AdjudicationError(f"Unsupported ledger schema at row {index}.")
        url = contract.string_value(row.get("url"), f"ledger row {index}.url")
        path = contract.dev_path(url, f"ledger row {index}.url")
        if path in ledger_rows:
            raise contract.AdjudicationError(f"Duplicate canonical ledger path: {path}")
        public_url = contract.string_value(
            row.get("public_url"),
            f"ledger row {path}.public_url",
        )
        contract.public_path(public_url, f"ledger row {path}.public_url")
        if public_url in public_urls:
            raise contract.AdjudicationError(f"Duplicate canonical ledger public URL: {public_url}")
        public_urls.add(public_url)
        disposition = contract.string_value(
            row.get("final_disposition"),
            f"ledger row {path}.final_disposition",
        )
        if disposition not in contract.OPERATIONAL_DISPOSITIONS:
            raise contract.AdjudicationError(f"Unsupported operational disposition for {path}.")
        contract.false_row_flags(row, f"ledger row {path}")
        ledger_rows[path] = row
        operational_counts[disposition] += 1
    observed_partition = contract.complete_counts(
        operational_counts,
        contract.OPERATIONAL_DISPOSITIONS,
    )
    if observed_partition != expectations.operational_partition:
        raise contract.AdjudicationError(
            "Operational ledger partition does not match the contract."
        )

    if journal.get("schema_version") != contract.JOURNAL_SCHEMA_VERSION:
        raise contract.AdjudicationError("Unsupported state journal schema.")
    safety = contract.object_value(journal.get("safety"), "journal.safety")
    for key, expected in contract.JOURNAL_SAFETY_FLAGS.items():
        if safety.get(key) is not expected:
            raise contract.AdjudicationError(f"Journal safety flag is not exact: {key}")
    raw_urls = contract.array_value(journal.get("urls"), "journal.urls")
    if len(raw_urls) != expectations.ledger_rows:
        raise contract.AdjudicationError("State journal row count does not match the contract.")
    journal_rows: dict[str, Mapping[str, Any]] = {}
    journal_urls: set[str] = set()
    for index, raw in enumerate(raw_urls):
        row = contract.object_value(raw, f"journal row {index}")
        path = contract.path_value(row.get("path"), f"journal row {index}.path")
        if path in journal_rows:
            raise contract.AdjudicationError(f"Duplicate state journal path: {path}")
        url = contract.string_value(row.get("url"), f"journal row {path}.url")
        if url in journal_urls or contract.dev_path(url, f"journal row {path}.url") != path:
            raise contract.AdjudicationError(f"Duplicate or mismatched journal URL: {path}")
        journal_urls.add(url)
        contract.false_row_flags(row, f"journal row {path}")
        journal_rows[path] = row
    if set(ledger_rows) != set(journal_rows):
        raise contract.AdjudicationError("Ledger and journal path sets differ.")
    for path, ledger_row in ledger_rows.items():
        if journal_rows[path].get("final_disposition") != ledger_row["final_disposition"]:
            raise contract.AdjudicationError(f"Operational disposition differs for {path}.")
    return ledger_rows, journal_rows
