#!/usr/bin/env python3
"""Validate a commit message against the WILQ semantic-commit contract."""

from __future__ import annotations

import re
import sys
from pathlib import Path

_HEADER = re.compile(
    r"^(?P<kind>build|chore|ci|docs|feat|fix|perf|refactor|refine|revert|style|test)"
    r"(?:\([a-z0-9][a-z0-9._/-]*\))?: (?P<subject>\S.*\S)$"
)
_MAX_SUBJECT_LENGTH = 100


def validate_commit_message(message: str) -> list[str]:
    """Return human-readable violations for the first non-comment header."""

    header = next(
        (
            line.strip()
            for line in message.splitlines()
            if line.strip() and not line.startswith("#")
        ),
        "",
    )
    if not header:
        return ["commit message needs a non-empty semantic header"]
    match = _HEADER.fullmatch(header)
    if match is None:
        return [
            "header must match '<type>(optional-scope): <imperative description>' "
            "using feat, fix, docs, refactor, refine, perf, test, build, ci, "
            "chore, revert, or style"
        ]
    if len(header) > _MAX_SUBJECT_LENGTH:
        return [f"semantic header must be at most {_MAX_SUBJECT_LENGTH} characters"]
    if match.group("subject")[0].isupper():
        return ["semantic description must start with lowercase text"]
    if match.group("subject").endswith("."):
        return ["semantic description must not end with a period"]
    return []


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0]} COMMIT_MESSAGE_FILE", file=sys.stderr)
        return 2
    try:
        message = Path(argv[1]).read_text(encoding="utf-8")
    except OSError as error:
        print(f"cannot read commit message: {error}", file=sys.stderr)
        return 2
    violations = validate_commit_message(message)
    if violations:
        print("semantic commit rejected:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
