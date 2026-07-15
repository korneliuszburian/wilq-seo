from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def parse_shard(value: str) -> tuple[int, int]:
    try:
        index_text, total_text = value.split("/", maxsplit=1)
        index = int(index_text)
        total = int(total_text)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError(
            "shard must use the form INDEX/TOTAL, for example 1/8"
        ) from exc

    if total < 1:
        raise argparse.ArgumentTypeError("TOTAL must be at least 1")
    if index < 1 or index > total:
        raise argparse.ArgumentTypeError("INDEX must be between 1 and TOTAL")
    return index, total


def discover_backend_tests(repo_root: Path) -> tuple[Path, ...]:
    return tuple(
        sorted(path.relative_to(repo_root) for path in (repo_root / "tests").rglob("test_*.py"))
    )


def select_shard(test_files: tuple[Path, ...], *, index: int, total: int) -> tuple[Path, ...]:
    return test_files[index - 1 :: total]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run one deterministic, non-overlapping shard of the backend pytest files."
    )
    parser.add_argument("--shard", required=True, type=parse_shard, metavar="INDEX/TOTAL")
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Print the selected files without running pytest.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    index, total = args.shard
    selected = select_shard(discover_backend_tests(repo_root), index=index, total=total)
    if not selected:
        parser.error(f"shard {index}/{total} selects no test files")

    if args.list_only:
        for path in selected:
            print(path.as_posix())
        return 0

    print(f"Running backend test shard {index}/{total}: {len(selected)} files", flush=True)
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *(str(path) for path in selected)],
        cwd=repo_root,
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
