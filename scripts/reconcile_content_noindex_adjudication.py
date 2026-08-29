from __future__ import annotations

import argparse
import os
import stat
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

from wilq.content.adjudication import (
    AdjudicationError,
    NoindexAdjudicationSources,
    ReconciliationResult,
    SourceArtifact,
    reconcile_noindex_adjudication,
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        sources = _sources(args)
        ledger_output = Path(args.ledger_output)
        journal_output = Path(args.journal_output)
        _validate_output_paths(
            ledger_output,
            journal_output,
            ledger_input=Path(args.ledger),
            journal_input=Path(args.journal),
            immutable_inputs=tuple(Path(path) for path in _immutable_input_paths(args)),
        )
        result = reconcile_noindex_adjudication(sources)
        if args.check:
            if not _outputs_match(ledger_output, journal_output, result):
                raise AdjudicationError("Retained authorities differ from the reconciliation.")
            print("Re-adjudykacja noindex jest aktualna.")
        else:
            _write_pair(
                ledger_output,
                result.ledger_bytes,
                journal_output,
                result.journal_bytes,
            )
            print("Zapisano re-adjudykację noindex bez promocji operacyjnej.")
    except (AdjudicationError, OSError) as error:
        print(f"Błąd re-adjudykacji noindex: {error}", file=sys.stderr)
        return 1
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Integruje review-only re-adjudykację 87 wierszy noindex."
    )
    parser.add_argument("--decision-packet", required=True)
    parser.add_argument("--decision-packet-sha256", required=True)
    for role in ("technical", "strategy", "tie-breaker"):
        parser.add_argument(f"--{role}-judge", required=True)
        parser.add_argument(f"--{role}-judge-sha256", required=True)
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--ledger-sha256", required=True)
    parser.add_argument("--journal", required=True)
    parser.add_argument("--journal-sha256", required=True)
    parser.add_argument("--recorded-at", required=True)
    parser.add_argument("--base-revision", required=True)
    parser.add_argument("--ledger-output", required=True)
    parser.add_argument("--journal-output", required=True)
    parser.add_argument("--check", action="store_true")
    return parser


def _sources(args: argparse.Namespace) -> NoindexAdjudicationSources:
    return NoindexAdjudicationSources(
        integrated_decision=_artifact(
            "integrated_decision", args.decision_packet, args.decision_packet_sha256
        ),
        technical_judge=_artifact("technical", args.technical_judge, args.technical_judge_sha256),
        strategy_judge=_artifact("strategy", args.strategy_judge, args.strategy_judge_sha256),
        tie_breaker_judge=_artifact(
            "tie_breaker", args.tie_breaker_judge, args.tie_breaker_judge_sha256
        ),
        ledger=_artifact("canonical_ledger", args.ledger, args.ledger_sha256),
        journal=_artifact("state_journal", args.journal, args.journal_sha256),
        recorded_at=args.recorded_at,
        base_revision=args.base_revision,
    )


def _artifact(role: str, raw_path: str, sha256: str) -> SourceArtifact:
    path = Path(raw_path)
    return SourceArtifact(
        role=role,
        artifact_reference=path.name,
        content=path.read_bytes(),
        expected_sha256=sha256,
    )


def _immutable_input_paths(args: argparse.Namespace) -> tuple[str, ...]:
    return (
        args.decision_packet,
        args.technical_judge,
        args.strategy_judge,
        args.tie_breaker_judge,
    )


def _validate_output_paths(
    ledger_output: Path,
    journal_output: Path,
    *,
    ledger_input: Path,
    journal_input: Path,
    immutable_inputs: Sequence[Path],
) -> None:
    if _aliases(ledger_output, journal_output):
        raise AdjudicationError("Ledger and journal outputs must be distinct.")
    if any(
        _aliases(output, source)
        for output in (ledger_output, journal_output)
        for source in immutable_inputs
    ):
        raise AdjudicationError("An output cannot overwrite an immutable input source.")
    if _aliases(ledger_output, journal_input) or _aliases(journal_output, ledger_input):
        raise AdjudicationError("Authority outputs cannot overwrite the cross-authority input.")


def _outputs_match(
    ledger_output: Path,
    journal_output: Path,
    result: object,
) -> bool:
    if not isinstance(result, ReconciliationResult):
        raise AdjudicationError("Domain reconciliation returned an unsupported result.")
    return (
        ledger_output.read_bytes() == result.ledger_bytes
        and journal_output.read_bytes() == result.journal_bytes
    )


def _aliases(left: Path, right: Path) -> bool:
    return left.resolve() == right.resolve() or (
        left.exists() and right.exists() and left.samefile(right)
    )


def _write_pair(
    ledger_path: Path,
    ledger_bytes: bytes,
    journal_path: Path,
    journal_bytes: bytes,
) -> None:
    outputs = ((ledger_path, ledger_bytes), (journal_path, journal_bytes))
    snapshots = {path: _snapshot(path) for path, _ in outputs}
    staged: list[tuple[Path, Path]] = []
    committed: list[Path] = []
    try:
        for path, payload in outputs:
            staged.append((_stage(path, payload, snapshots[path][1]), path))
        for staged_path, output_path in staged:
            os.replace(staged_path, output_path)
            committed.append(output_path)
    except OSError:
        for output_path in reversed(committed):
            _restore(output_path, snapshots[output_path])
        raise
    finally:
        for staged_path, _ in staged:
            staged_path.unlink(missing_ok=True)


def _snapshot(path: Path) -> tuple[bytes | None, int]:
    if not path.exists():
        return None, 0o644
    if not path.is_file():
        raise AdjudicationError(f"Output path is not a regular file: {path}")
    return path.read_bytes(), stat.S_IMODE(path.stat().st_mode)


def _stage(path: Path, payload: bytes, mode: int) -> Path:
    descriptor, raw_path = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    staged = Path(raw_path)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(staged, mode)
    return staged


def _restore(path: Path, snapshot: tuple[bytes | None, int]) -> None:
    payload, mode = snapshot
    if payload is None:
        path.unlink(missing_ok=True)
        return
    staged = _stage(path, payload, mode)
    os.replace(staged, path)


if __name__ == "__main__":
    raise SystemExit(main())
