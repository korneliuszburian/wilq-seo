from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from wilq.social.history import (
    audit_social_history_metadata_payload,
    social_history_input_example,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Waliduje metadata-only historię LinkedIn/Facebook dla social dedupe. "
            "Nie importuje postów, nie zapisuje danych i nie odblokowuje publikacji."
        )
    )
    parser.add_argument("input", nargs="?", help="Ścieżka do JSON z historią social")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument(
        "--print-input-example",
        action="store_true",
        help="Wypisz przykładowy metadata-only JSON do uzupełnienia.",
    )
    args = parser.parse_args()

    if args.print_input_example:
        print(json.dumps(social_history_input_example(), ensure_ascii=False, indent=2))
        return 0
    if not args.input:
        print("Podaj ścieżkę input albo użyj --print-input-example", file=sys.stderr)
        return 1

    try:
        payload = load_json(Path(args.input))
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 1

    audit = audit_social_history_metadata_payload(payload).model_dump(mode="json")
    if args.format == "json":
        print(json.dumps(audit, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(audit))
    return 0 if audit["status"] == "review_ready" else 1


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise RuntimeError(f"Could not read {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise RuntimeError(f"{path} is not valid JSON") from error
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} must contain a JSON object")
    return payload


def render_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# Social history inventory audit",
        "",
        f"- Contract: `{audit['contract']}`",
        f"- Status: `{audit['status']}`",
        f"- Read-only: {visible_bool(audit['read_only'])}",
        f"- Pozycji metadata: `{audit['item_count']}`",
        f"- Duplicate-free claim allowed: {visible_bool(audit['duplicate_free_claim_allowed'])}",
        f"- Publish allowed: {visible_bool(audit['publish_allowed'])}",
        "",
        "## Kanały",
        "",
    ]
    channel_counts = audit.get("channel_counts")
    if isinstance(channel_counts, dict) and channel_counts:
        for channel, count in channel_counts.items():
            lines.append(f"- `{channel}`: `{count}`")
    else:
        lines.append("- brak zwalidowanych pozycji")

    lines.extend(["", "## Braki i błędy", ""])
    errors = audit.get("errors")
    if isinstance(errors, list) and errors:
        for error in errors:
            lines.append(f"- {error}")
    else:
        lines.append("- brak")

    missing_sources = audit.get("missing_required_sources")
    if isinstance(missing_sources, list) and missing_sources:
        lines.append(
            "- Brakujące źródła historii: "
            + ", ".join(str(source) for source in missing_sources)
        )

    lines.extend(
        [
            "",
            "## Zakazane pola",
            "",
            "- "
            + ", ".join(str(field) for field in audit["forbidden_metadata_fields"]),
            "",
            "## Następny krok",
            "",
            str(audit["operator_next_step"]),
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def visible_bool(value: Any) -> str:
    return "tak" if value is True else "nie"


if __name__ == "__main__":
    raise SystemExit(main())
