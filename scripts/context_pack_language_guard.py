from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

DEFAULT_API_BASE = "http://127.0.0.1:8000"
DEFAULT_SKILLS = (
    "wilq-daily-command",
    "wilq-content-strategist",
    "wilq-merchant-feed-operator",
    "wilq-ads-doctor",
    "wilq-ga4-analyst",
    "wilq-localo-operator",
    "wilq-ahrefs-gap-finder",
)

FORBIDDEN_ACTION_PLAN_KEYS = (
    "action_type",
    "connector",
    "mode",
    "operation_type",
    "payload_preview",
    "budget_payload_preview",
    "custom_segment_payload_preview",
    "negative_keyword_payload_preview",
    "content_brief_preview",
    "wordpress_draft_payload_preview",
    "preview_contract",
    "source_preview_contract",
    "preview_contract_label",
    "required_validation",
    "required_validation_labels",
    "api_mutation_ready",
    "apply_allowed",
    "destructive",
)

FORBIDDEN_VALUE_TERMS = (
    "Command Center",
    "Content Planner",
    "Ads Doctor",
    "ActionObject",
    "Dry-run",
    "dry-run",
    "payload",
    "payload_apply_allowed_false",
    "No evidence ID",
    "No source connector",
    "No validated action",
    "No audit event",
    "No WILQ API call",
    "must not invent metrics",
    "evidence IDs",
    "ID dowodu",
    "blockers",
    "blockery",
    "source_public_url",
    "final_canonical_url",
    "intended_final_url",
    "preview_url",
    "target site",
    "target_site",
    "mapping-review",
    "mapping_review",
    "migration-map",
    "competitor_page",
    "MERCHANT_ACTION",
    "SHOPPING_ADS",
    "FREE_LISTINGS",
    "NOT_IMPACTED",
    "missing_potentially_required_attribute",
    "wartość wymiaru do sprawdzenia",
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Checks live WILQ Codex context packs for marketer-facing stale "
            "language and raw vendor/action values."
        )
    )
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument(
        "--skill",
        action="append",
        dest="skills",
        help="Skill ID to check. Repeat to check multiple skills.",
    )
    parser.add_argument("--timeout", type=float, default=90.0)
    args = parser.parse_args()

    skills = tuple(args.skills or DEFAULT_SKILLS)
    errors: list[dict[str, str]] = []
    checked: list[str] = []

    for skill in skills:
        try:
            payload = _fetch_context_pack(args.api_base, skill, timeout=args.timeout)
        except RuntimeError as error:
            errors.append(
                {"skill": skill, "path": "$", "term": "fetch_failed", "value": str(error)}
            )
            continue
        checked.append(skill)
        for path, term, value in _context_pack_structure_errors(payload):
            errors.append({"skill": skill, "path": path, "term": term, "value": value})
        for path, value in _walk_string_values(payload):
            for term in FORBIDDEN_VALUE_TERMS:
                if term in value:
                    errors.append(
                        {
                            "skill": skill,
                            "path": path,
                            "term": term,
                            "value": value[:240],
                        }
                    )
                    break

    result = {
        "status": "completed" if not errors else "failed",
        "api_base": args.api_base,
        "checked_skills": checked,
        "forbidden_terms": FORBIDDEN_VALUE_TERMS,
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


def _fetch_context_pack(api_base: str, skill: str, *, timeout: float) -> dict[str, Any]:
    request = Request(
        f"{api_base.rstrip('/')}/api/codex/context-pack",
        data=json.dumps({"skill": skill}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except (OSError, URLError, json.JSONDecodeError) as error:
        raise RuntimeError(str(error)) from error
    if not isinstance(payload, dict):
        raise RuntimeError(f"context pack for {skill} was not a JSON object")
    return payload


def _context_pack_structure_errors(payload: Mapping[str, Any]) -> list[tuple[str, str, str]]:
    errors: list[tuple[str, str, str]] = []
    actions = payload.get("active_action_objects")
    if not isinstance(actions, Sequence) or isinstance(actions, (str, bytes, bytearray)):
        actions = []
    for index, action in enumerate(actions):
        if not isinstance(action, Mapping):
            continue
        if "payload" in action:
            errors.append(
                (
                    f"$.active_action_objects[{index}].payload",
                    "action_payload_key",
                    (
                        "Use action_plan in skill context packs; keep payload on action "
                        "detail endpoints."
                    ),
                )
            )
        action_plan = action.get("action_plan")
        if isinstance(action_plan, Mapping):
            action_plan_path = f"$.active_action_objects[{index}].action_plan"
            for path, key in _walk_mapping_keys(action_plan, action_plan_path):
                if key in FORBIDDEN_ACTION_PLAN_KEYS:
                    errors.append(
                        (
                            path,
                            "technical_action_plan_key",
                            f"Use marketer-readable compact action plan keys instead of {key}.",
                        )
                    )
    capabilities = payload.get("expert_capabilities")
    if not isinstance(capabilities, Sequence) or isinstance(
        capabilities, (str, bytes, bytearray)
    ):
        return errors
    for index, capability in enumerate(capabilities):
        if isinstance(capability, Mapping) and "required_mapping" in capability:
            errors.append(
                (
                    f"$.expert_capabilities[{index}].required_mapping",
                    "required_mapping_key",
                    "Use required_inputs in compact skill context packs.",
                )
            )
    return errors


def _walk_string_values(value: Any, path: str = "$"):
    if isinstance(value, str):
        yield path, value
        return
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield from _walk_string_values(child, f"{path}.{key}")
        return
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        for index, child in enumerate(value):
            yield from _walk_string_values(child, f"{path}[{index}]")


def _walk_mapping_keys(value: Any, path: str = "$"):
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_path = f"{path}.{key}"
            yield key_path, str(key)
            yield from _walk_mapping_keys(child, key_path)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            yield from _walk_mapping_keys(child, f"{path}[{index}]")


if __name__ == "__main__":
    sys.exit(main())
