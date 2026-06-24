from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen


DEFAULT_API_BASE = "http://127.0.0.1:8000"
CONTENT_DIAGNOSTICS_PATH = "/api/content/diagnostics"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Export the current Ekologus target-site mapping review packet from "
            "WILQ API. The packet is review-only and does not confirm mapping, "
            "write to WordPress, publish, or claim uplift."
        )
    )
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="markdown",
        help="Output format. Markdown is easier for operator review.",
    )
    args = parser.parse_args()

    try:
        diagnostics = fetch_content_diagnostics(args.api_base)
        packet = build_mapping_review_packet(diagnostics, api_base=args.api_base)
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(packet, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(packet))
    return 0


def fetch_content_diagnostics(api_base: str) -> dict[str, Any]:
    url = f"{api_base.rstrip('/')}{CONTENT_DIAGNOSTICS_PATH}"
    try:
        with urlopen(url, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except URLError as error:
        raise RuntimeError(f"Could not fetch {url}: {error}") from error

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Endpoint {url} did not return JSON") from error
    if not isinstance(payload, dict):
        raise RuntimeError(f"Endpoint {url} returned non-object JSON")
    return payload


def build_mapping_review_packet(
    diagnostics: dict[str, Any],
    *,
    api_base: str = DEFAULT_API_BASE,
) -> dict[str, Any]:
    summary = _mapping(diagnostics.get("operator_summary"))
    inputs = _list(summary.get("target_site_mapping_review_inputs"))
    migration_map = _list(summary.get("target_site_migration_map"))
    migration_by_candidate = {
        str(item.get("candidate_id")): _mapping(item)
        for item in migration_map
        if isinstance(item, dict) and item.get("candidate_id")
    }
    items = [
        _packet_item(_mapping(item), migration_by_candidate)
        for item in inputs
        if isinstance(item, dict)
    ]
    if not items:
        raise RuntimeError(
            "Content diagnostics do not expose target_site_mapping_review_inputs"
        )

    return {
        "packet_type": "content_target_site_mapping_review_packet_v1",
        "api_base": api_base.rstrip("/"),
        "source_endpoint": CONTENT_DIAGNOSTICS_PATH,
        "generated_at": diagnostics.get("generated_at"),
        "language": diagnostics.get("language"),
        "target_site_host": summary.get("target_site_host"),
        "mapping_status": summary.get("target_site_mapping_status"),
        "review_count": len(items),
        "review_endpoint": items[0].get("review_endpoint"),
        "items": items,
        "blocked_outputs": sorted(
            {
                str(blocked)
                for item in items
                for blocked in _list(item.get("blocked_outputs"))
                if blocked
            }
        ),
        "safety_note": (
            "Ten pakiet tylko zbiera ręczne review mapowania old-to-new. "
            "Nie potwierdza migracji, nie robi staging write, nie publikuje "
            "i nie pozwala claimować wzrostu pozycji, leadów ani revenue."
        ),
    }


def _packet_item(
    item: dict[str, Any],
    migration_by_candidate: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    candidate_id = str(item.get("candidate_id") or "")
    migration = migration_by_candidate.get(candidate_id, {})
    payload_template = _mapping(item.get("review_payload_template"))
    return {
        "decision_id": item.get("decision_id"),
        "candidate_id": candidate_id,
        "title": item.get("title"),
        "source_url": item.get("source_url"),
        "current_migration_candidate_url": item.get(
            "current_migration_candidate_url"
        ),
        "candidate_target_urls": _list(item.get("candidate_target_urls")),
        "mapping_review_status": item.get("mapping_review_status"),
        "status_summary": migration.get("status_summary"),
        "allowed_outcomes": _list(item.get("allowed_outcomes")),
        "review_endpoint": item.get("review_endpoint"),
        "review_payload_template": payload_template,
        "fill_before_post": {
            "reviewed_by": "<operator>",
            "mapping_outcome": "<wybierz allowed_outcome>",
            "selected_target_url": "<wybierz target URL albo wpisz ręczny URL>",
            "mapping_notes": "<krótka decyzja marketera>",
        },
        "blocked_outputs": _list(item.get("blocked_outputs")),
    }


def render_markdown(packet: dict[str, Any]) -> str:
    lines = [
        "# Content Mapping Review Packet",
        "",
        f"- Type: `{packet.get('packet_type')}`",
        f"- Generated at: `{packet.get('generated_at') or 'unknown'}`",
        f"- Target site: `{packet.get('target_site_host') or 'unknown'}`",
        f"- Mapping status: `{packet.get('mapping_status') or 'unknown'}`",
        f"- Review endpoint: `{packet.get('review_endpoint') or 'unknown'}`",
        f"- Review items: `{packet.get('review_count')}`",
        "",
        packet.get("safety_note") or "",
        "",
    ]
    for index, item in enumerate(_list(packet.get("items")), start=1):
        item = _mapping(item)
        lines.extend(
            [
                f"## {index}. {item.get('title') or item.get('candidate_id')}",
                "",
                f"- Candidate: `{item.get('candidate_id')}`",
                f"- Source URL: {item.get('source_url') or 'brak'}",
                "- Current generated target candidate: "
                f"{item.get('current_migration_candidate_url') or 'brak'}",
                f"- Review status: `{item.get('mapping_review_status') or 'unknown'}`",
                f"- Status summary: {item.get('status_summary') or 'brak'}",
                "- Allowed outcomes: "
                f"{', '.join(f'`{value}`' for value in _list(item.get('allowed_outcomes'))) or 'brak'}",
                "- Candidate target URLs:",
            ]
        )
        target_urls = _list(item.get("candidate_target_urls"))
        if target_urls:
            lines.extend(f"  - {url}" for url in target_urls)
        else:
            lines.append("  - brak")
        lines.extend(
            [
                "",
                "Payload template to post after human review:",
                "",
                "```json",
                json.dumps(
                    item.get("review_payload_template") or {},
                    ensure_ascii=False,
                    indent=2,
                ),
                "```",
                "",
                "Fill before POST:",
                "",
                "```json",
                json.dumps(
                    item.get("fill_before_post") or {},
                    ensure_ascii=False,
                    indent=2,
                ),
                "```",
                "",
                "Blocked outputs after this packet:",
            ]
        )
        blocked_outputs = _list(item.get("blocked_outputs"))
        if blocked_outputs:
            lines.extend(f"- `{value}`" for value in blocked_outputs)
        else:
            lines.append("- brak")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


if __name__ == "__main__":
    sys.exit(main())
