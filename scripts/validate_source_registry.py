"""Validate the current source-to-decision registry invariants."""

from __future__ import annotations

import hashlib
import re
from datetime import date
from pathlib import Path

REGISTRY_PATH = Path("docs/research/source-registry.md")
DECISIONS = {"adopt", "reject", "lab-test", "defer"}
DATE_RE = re.compile(r"\bchecked\s+(\d{4}-\d{2}-\d{2})\b")
ID_RE = re.compile(r"\b(?:SEO-G\d(?:-D)?|IR-\d|WILQ-[A-Z0-9-]+)\b")
SHA_RE = re.compile(r"\bsha256:[0-9a-f]{64}\b")
PATH_RE = re.compile(r"`(docs/research/[a-z0-9-]+\.md)`")
LAST_CHECKED_RE = re.compile(r"^Last checked:\s+(\d{4}-\d{2}-\d{2})\.")


def _table_rows(lines: list[str], start: int, end: int) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in lines[start:end]:
        if not line.startswith("|") or line.startswith("|---"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and cells[0] != "ID":
            rows.append(cells)
    return rows


def validate(path: Path = REGISTRY_PATH) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    try:
        current_start = lines.index("### Źródła primary i zakres autorytetu")
        local_start = lines.index("### Lokalne polityki pochodne")
        mechanism_start = lines.index("### Mechanism → local decision")
        map_start = lines.index("### Consumer and falsifier map")
        historical_start = lines.index("## Historical/reference source inventory")
    except ValueError as exc:
        return [f"missing registry section: {exc}"]

    source_rows = _table_rows(lines, current_start, local_start)
    local_rows = _table_rows(lines, local_start, mechanism_start)
    rows = source_rows + local_rows
    valid_rows: list[list[str]] = []
    errors: list[str] = []
    ids: list[str] = []
    for row in rows:
        if len(row) != 4:
            errors.append(f"source row must have 4 cells: {row!r}")
            continue
        valid_rows.append(row)
        source_id, source, mechanism, decision = row
        ids.append(source_id)
        if not source_id:
            errors.append("source row has empty ID")
        if not source or not mechanism:
            errors.append(f"{source_id}: source and mechanism are required")
        date_match = DATE_RE.search(source)
        if not date_match:
            errors.append(f"{source_id}: missing checked YYYY-MM-DD")
        else:
            try:
                checked = date.fromisoformat(date_match.group(1))
            except ValueError:
                errors.append(f"{source_id}: invalid checked date {date_match.group(1)!r}")
            else:
                if checked > date.today():
                    errors.append(f"{source_id}: checked date is in the future")
        if source_id == "WILQ-PLAIN-PL" and not SHA_RE.search(source):
            errors.append(f"{source_id}: local basis requires sha256 version")
        if source_id == "WILQ-PLAIN-PL":
            path_match = PATH_RE.search(source)
            hash_match = SHA_RE.search(source)
            if path_match and hash_match:
                basis_path = Path(path_match.group(1))
                basis_file = Path(__file__).resolve().parents[1] / basis_path
                if not basis_file.is_file():
                    errors.append(f"{source_id}: basis file does not exist: {basis_path}")
                else:
                    actual_hash = hashlib.sha256(basis_file.read_bytes()).hexdigest()
                    if actual_hash != hash_match.group(0).split(":", 1)[1]:
                        errors.append(f"{source_id}: local basis sha256 does not match")
        if decision.strip("`") not in DECISIONS:
            errors.append(f"{source_id}: invalid decision {decision!r}")

    if len(ids) != len(set(ids)):
        errors.append("source IDs must be unique")

    rows = valid_rows
    known_ids = set(ids)
    current_text = "\n".join(lines[current_start:historical_start])
    prose_ids = set(ID_RE.findall(current_text))
    unknown_prose_ids = sorted(prose_ids - known_ids)
    if unknown_prose_ids:
        errors.append(f"mechanism prose references unknown IDs: {unknown_prose_ids}")

    map_rows = _table_rows(lines, map_start, historical_start)
    mapped_ids: set[str] = set()
    map_by_id: dict[str, list[list[str]]] = {}
    for row in map_rows:
        if len(row) != 3:
            errors.append(f"consumer row must have 3 cells: {row!r}")
            continue
        source_id, consumer, falsifier = row
        mapped_ids.add(source_id)
        map_by_id.setdefault(source_id, []).append(row)
        if not consumer or not falsifier:
            errors.append(f"{source_id}: consumer and falsifier are required")
    duplicate_map_ids = sorted(
        source_id for source_id, entries in map_by_id.items() if len(entries) > 1
    )
    if duplicate_map_ids:
        errors.append(f"consumer map IDs must be unique: {duplicate_map_ids}")
    missing = sorted(set(ids) - mapped_ids)
    extra = sorted(mapped_ids - set(ids))
    if missing:
        errors.append(f"source IDs missing consumer/falsifier rows: {missing}")
    if extra:
        errors.append(f"consumer map has unknown IDs: {extra}")
    for source_id, _source, _mechanism, decision in rows:
        if decision.strip("`") != "defer":
            continue
        entries = map_by_id.get(source_id, [])
        consumer_text = "\n".join(entry[1] for entry in entries)
        map_text = "\n".join(" ".join(entry[1:]) for entry in entries)
        owner_marker = re.search(
            r"\b(?:owner|właściciel)\b\s*[:=]?\s*[\wŁŚŻŹĆŃÓĄĘłśżźćńóąę-]+",
            consumer_text,
            re.IGNORECASE,
        )
        negated_owner = re.search(
            r"\b(?:brak|no)\b[^;,.]*\b(?:owner|właściciel)\b",
            consumer_text,
            re.IGNORECASE,
        )
        recheck_marker = re.search(
            r"re-?check|ponown(?:ego|ym) sprawdzeni(?:a|u)", map_text, re.IGNORECASE
        )
        if not owner_marker or negated_owner or not recheck_marker:
            errors.append(
                f"{source_id}: defer requires owner and re-check condition in its map row"
            )

    last_checked = LAST_CHECKED_RE.match(lines[2] if len(lines) > 2 else "")
    if not last_checked:
        errors.append("registry: missing Last checked YYYY-MM-DD")
    else:
        try:
            if date.fromisoformat(last_checked.group(1)) > date.today():
                errors.append("registry: Last checked date is in the future")
        except ValueError:
            errors.append(f"registry: invalid Last checked date {last_checked.group(1)!r}")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("source registry invariants: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
