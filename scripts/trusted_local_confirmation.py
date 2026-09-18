"""Issue a short-lived trusted local ActionObject confirmation grant."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from typing import TextIO

from wilq.audit.identity import LOCAL_PILOT_AUDIT_IDENTITY
from wilq.audit.trusted_local_confirmation import (
    TRUSTED_LOCAL_CONFIRMATION_PHRASE,
    TrustedLocalConfirmationAuthority,
    TrustedLocalConfirmationBlocked,
    TrustedLocalConfirmationError,
    trusted_local_confirmation_authority,
)


def issue_interactive_grant(
    *,
    authority: TrustedLocalConfirmationAuthority,
    action_id: str,
    payload_digest: str,
    snapshot_digest: str,
    workspace_id: str,
    stdin: TextIO,
    stdout: TextIO,
    is_tty: bool | None = None,
    phrase_reader: Callable[[], str] | None = None,
) -> str:
    """Show the exact binding, then issue only after the TTY phrase is entered."""

    tty = (stdin.isatty() and stdout.isatty()) if is_tty is None else is_tty
    if not tty:
        raise TrustedLocalConfirmationBlocked(
            "Trusted local confirmation requires an interactive TTY.",
            code="trusted_local_confirmation_tty_required",
        )
    uid = authority.current_uid()
    stdout.write("Dokładna akcja do potwierdzenia:\n")
    stdout.write(f"action ID: {action_id}\n")
    stdout.write(f"action payload digest: {payload_digest}\n")
    stdout.write(f"promotion snapshot digest: {snapshot_digest}\n")
    stdout.write(f"workspace: {workspace_id}\n")
    stdout.write(f"OS UID: {uid}\n")
    stdout.write(f"Wpisz dokładnie: {TRUSTED_LOCAL_CONFIRMATION_PHRASE}\n")
    stdout.flush()
    phrase = phrase_reader() if phrase_reader is not None else stdin.readline().rstrip("\r\n")
    token = authority.issue(
        principal_id=LOCAL_PILOT_AUDIT_IDENTITY.principal_id,
        workspace_id=workspace_id,
        action_id=action_id,
        payload_digest=payload_digest,
        snapshot_digest=snapshot_digest,
        is_tty=tty,
        confirmation_phrase=phrase,
    )
    stdout.write(f"trusted local confirmation grant: {token}\n")
    stdout.flush()
    return token


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Wydaj jednorazowy grant trusted local confirmation dla exact ActionObject. "
            "Wymaga lokalnego interaktywnego TTY; nie zapisuje tokenu w audycie."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    issue = subparsers.add_parser(
        "issue",
        help="Pokaż exact binding i wydaj grant po wpisaniu wymaganego zwrotu.",
    )
    issue.add_argument("--action-id", required=True, help="Exact ActionObject ID.")
    issue.add_argument(
        "--payload-digest",
        required=True,
        help="64-znakowy digest payloadu akcji.",
    )
    issue.add_argument(
        "--snapshot-digest",
        required=True,
        help="64-znakowy digest snapshotu promotion.",
    )
    issue.add_argument(
        "--workspace-id",
        default=LOCAL_PILOT_AUDIT_IDENTITY.workspace_id,
        help="Workspace związany z grantem (domyślnie lokalny pilot).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command != "issue":
        return 2
    try:
        issue_interactive_grant(
            authority=trusted_local_confirmation_authority(),
            action_id=args.action_id,
            payload_digest=args.payload_digest,
            snapshot_digest=args.snapshot_digest,
            workspace_id=args.workspace_id,
            stdin=sys.stdin,
            stdout=sys.stdout,
        )
    except TrustedLocalConfirmationError as error:
        print(f"Zablokowano: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
