from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_API_BASE = "http://127.0.0.1:8000"

SurfaceStatus = Literal["production", "experimental", "placeholder", "technical"]
HttpMethod = Literal["GET", "POST"]
SurfaceFamily = Literal[
    "command",
    "diagnostic",
    "workflow",
    "registry",
    "knowledge",
    "settings",
    "technical",
]


@dataclass(frozen=True)
class SurfaceSpec:
    surface_id: str
    path: str
    label: str
    family: SurfaceFamily
    status: SurfaceStatus
    endpoint: str
    method: HttpMethod = "GET"
    request_json: dict[str, Any] | None = None
    auxiliary_endpoints: tuple[str, ...] = ()
    payload_key: str | None = None
    requires_evidence: bool = True
    requires_source_connector: bool = True
    requires_action: bool = False
    requires_decision: bool = False
    requires_records: bool = False
    requires_lineage: bool = False
    requires_private_source_trace: bool = False
    requires_blocker_or_blocked_claim: bool = False
    requires_polish_contract: bool = False
    reference_next_step: str | None = None
    demo_priority: int = 50


SURFACES: tuple[SurfaceSpec, ...] = (
    SurfaceSpec(
        "command_center",
        "/command-center",
        "Centrum pracy",
        "command",
        "production",
        "/api/dashboard/command-center",
        requires_action=True,
        requires_decision=True,
        requires_blocker_or_blocked_claim=True,
        demo_priority=10,
    ),
    SurfaceSpec(
        "ads_doctor",
        "/ads-doctor",
        "Google Ads",
        "diagnostic",
        "production",
        "/api/ads/diagnostics?view=summary",
        requires_action=True,
        requires_decision=True,
        requires_blocker_or_blocked_claim=True,
        requires_polish_contract=True,
        demo_priority=20,
    ),
    SurfaceSpec(
        "merchant",
        "/merchant",
        "Merchant",
        "diagnostic",
        "production",
        "/api/merchant/diagnostics",
        requires_action=True,
        requires_decision=True,
        requires_blocker_or_blocked_claim=True,
        requires_polish_contract=True,
        demo_priority=25,
    ),
    SurfaceSpec(
        "content_planner",
        "/content-planner",
        "Treści",
        "diagnostic",
        "production",
        "/api/content/diagnostics",
        requires_action=True,
        requires_decision=True,
        requires_blocker_or_blocked_claim=True,
        requires_polish_contract=True,
        demo_priority=30,
    ),
    SurfaceSpec(
        "ga4",
        "/ga4",
        "GA4",
        "diagnostic",
        "production",
        "/api/ga4/diagnostics",
        requires_action=True,
        requires_decision=True,
        requires_blocker_or_blocked_claim=True,
        requires_polish_contract=True,
        demo_priority=35,
    ),
    SurfaceSpec(
        "service_profile",
        "/service-profile",
        "Service Profile",
        "knowledge",
        "production",
        "/api/content/service-profile",
        requires_action=True,
        requires_source_connector=False,
        requires_decision=True,
        requires_private_source_trace=True,
        requires_blocker_or_blocked_claim=True,
        requires_polish_contract=True,
        demo_priority=40,
    ),
    SurfaceSpec(
        "content_workflow",
        "/content-workflow",
        "Workflow treści",
        "workflow",
        "production",
        "/api/content/work-items/snapshot",
        auxiliary_endpoints=("/api/content/wordpress/authoring-profile",),
        requires_decision=True,
        requires_blocker_or_blocked_claim=True,
        demo_priority=42,
    ),
    SurfaceSpec(
        "ahrefs",
        "/ahrefs",
        "Ahrefs",
        "diagnostic",
        "production",
        "/api/ahrefs/diagnostics",
        requires_decision=True,
        requires_blocker_or_blocked_claim=True,
        requires_polish_contract=True,
        demo_priority=45,
    ),
    SurfaceSpec(
        "localo",
        "/localo",
        "Localo",
        "diagnostic",
        "production",
        "/api/localo/diagnostics",
        requires_action=True,
        requires_decision=True,
        requires_blocker_or_blocked_claim=True,
        requires_polish_contract=True,
        demo_priority=50,
    ),
    SurfaceSpec(
        "demand_gen",
        "/ads-doctor/demand-gen",
        "Demand Gen",
        "diagnostic",
        "experimental",
        "/api/demand-gen/diagnostics",
        requires_action=True,
        requires_decision=True,
        requires_blocker_or_blocked_claim=True,
        requires_polish_contract=True,
        demo_priority=60,
    ),
    SurfaceSpec(
        "social_publisher",
        "/social-publisher",
        "Publikacje social",
        "workflow",
        "experimental",
        "/api/codex/context-pack",
        method="POST",
        request_json={"skill": "wilq-social-publisher"},
        payload_key="social_draft_context",
        requires_action=True,
        requires_decision=True,
        requires_blocker_or_blocked_claim=True,
        demo_priority=65,
    ),
    SurfaceSpec(
        "actions",
        "/actions",
        "Akcje",
        "registry",
        "production",
        "/api/actions",
        requires_evidence=False,
        requires_source_connector=False,
        reference_next_step=(
            "Użyj po wybraniu konkretnej akcji z Centrum pracy; to rejestr "
            "dowodów, walidacji i blokad, nie kolejka startowa."
        ),
        demo_priority=70,
    ),
    SurfaceSpec(
        "opportunities",
        "/opportunities",
        "Szanse",
        "registry",
        "production",
        "/api/opportunities",
        requires_evidence=False,
        requires_source_connector=False,
        reference_next_step=(
            "Użyj jako rejestr szans po Centrum pracy; decyzję uruchamiaj "
            "przez powiązaną akcję i dowody."
        ),
        demo_priority=75,
    ),
    SurfaceSpec(
        "workflows",
        "/workflows",
        "Procesy",
        "workflow",
        "production",
        "/api/workflows",
        requires_evidence=False,
        requires_source_connector=False,
        demo_priority=80,
    ),
    SurfaceSpec(
        "knowledge",
        "/knowledge",
        "Baza wiedzy",
        "knowledge",
        "production",
        "/api/knowledge/cards",
        requires_evidence=False,
        requires_source_connector=False,
        requires_records=True,
        requires_lineage=True,
        reference_next_step=(
            "Użyj do trace i review źródeł wiedzy; sama karta nie oznacza "
            "production-depth bez zatwierdzenia."
        ),
        demo_priority=85,
    ),
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit live WILQ dashboard surfaces for Wilku demo/usefulness readiness. "
            "The audit checks API-owned evidence, decisions, blockers and safe next steps; "
            "it does not assert exact live metric values."
        )
    )
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument(
        "--min-production-score",
        type=int,
        default=7,
        help="Fail when a production surface scores below this threshold.",
    )
    args = parser.parse_args()

    report = build_report(args.api_base, min_production_score=args.min_production_score)
    if args.format == "markdown":
        print(render_markdown(report))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["pass"] else 1


def build_report(api_base: str = DEFAULT_API_BASE, min_production_score: int = 7) -> dict[str, Any]:
    surface_reports = [
        evaluate_surface(spec, _safe_fetch(api_base, spec)) for spec in SURFACES
    ]
    production_failures = [
        surface
        for surface in surface_reports
        if surface["status"] == "production"
        and surface["usefulness_score"] < min_production_score
    ]
    error_surfaces = [
        surface
        for surface in surface_reports
        if surface["status"] == "production" and surface["errors"]
    ]
    return {
        "api_base": api_base,
        "surface_count": len(surface_reports),
        "min_production_score": min_production_score,
        "demo_ready_count": sum(
            1 for surface in surface_reports if surface["readiness"] == "demo_ready"
        ),
        "review_ready_count": sum(
            1 for surface in surface_reports if surface["readiness"] == "review_ready"
        ),
        "blocked_count": sum(
            1 for surface in surface_reports if surface["readiness"] == "blocked"
        ),
        "production_failure_count": len(production_failures) + len(error_surfaces),
        "pass": not production_failures and not error_surfaces,
        "surfaces": sorted(
            surface_reports,
            key=lambda surface: (surface["demo_priority"], surface["path"]),
        ),
    }


def evaluate_surface(spec: SurfaceSpec, fetch_result: dict[str, Any]) -> dict[str, Any]:
    payload = fetch_result.get("payload")
    if spec.payload_key and isinstance(payload, dict):
        payload = payload.get(spec.payload_key, payload)
    errors = list(fetch_result.get("errors") or [])
    evidence_ids = sorted(_find_unique_values(payload, "evidence_ids"))
    source_connectors = sorted(_find_unique_values(payload, "source_connectors"))
    action_ids = sorted(_find_action_ids(payload))
    blocked_claims = sorted(_find_unique_values(payload, "blocked_claims"))
    decision_count = _decision_count(payload)
    record_count = _record_count(payload)
    lineage_count = len(_find_unique_values(payload, "source_lineage"))
    safe_next_steps = _safe_next_steps(payload)
    sample_next_steps = safe_next_steps[:3]
    if not sample_next_steps and spec.reference_next_step:
        sample_next_steps = [spec.reference_next_step]
    language = payload.get("language") if isinstance(payload, dict) else None
    has_blockers = _has_blockers(payload)
    auxiliary_checks = _evaluate_auxiliary_checks(
        spec,
        fetch_result.get("auxiliary_payloads") or {},
    )
    for check in auxiliary_checks:
        errors.extend(check["errors"])

    if spec.requires_evidence and not evidence_ids:
        errors.append("missing evidence_ids")
    if spec.requires_source_connector and not source_connectors:
        errors.append("missing source_connectors")
    if spec.requires_action and not action_ids:
        errors.append("missing action_ids")
    if spec.requires_decision and decision_count == 0:
        errors.append("missing decision queue or decision-like records")
    if spec.requires_records and record_count == 0:
        errors.append("missing records")
    if spec.requires_lineage and lineage_count == 0:
        errors.append("missing source lineage")
    private_source_trace = _private_source_trace_check(payload)
    if spec.requires_private_source_trace and not private_source_trace["ready"]:
        errors.extend(private_source_trace["errors"])
    has_blocker_count = _has_positive_count(payload, "blocker_count")
    has_decision_blocker_count = _has_positive_count(payload, "decision_blocker_count")
    if spec.requires_blocker_or_blocked_claim and not (
        blocked_claims or has_blockers or has_blocker_count or has_decision_blocker_count
    ):
        errors.append("missing blocked_claims or blocker count")
    if spec.requires_polish_contract and language not in {None, "pl-PL"}:
        errors.append("language is not pl-PL")
    if spec.requires_decision and not safe_next_steps:
        errors.append("missing safe next step/operator action")

    score = 0
    score += 2 if not fetch_result.get("fetch_error") else 0
    score += 2 if (evidence_ids or not spec.requires_evidence) else 0
    score += 1 if (source_connectors or not spec.requires_source_connector) else 0
    score += 1 if (action_ids or not spec.requires_action) else 0
    score += 1 if (decision_count > 0 or not spec.requires_decision) else 0
    score += 1 if (record_count > 0 or not spec.requires_records) else 0
    score += 1 if (lineage_count > 0 or not spec.requires_lineage) else 0
    score += 1 if (
        blocked_claims
        or has_blockers
        or has_blocker_count
        or has_decision_blocker_count
        or not spec.requires_blocker_or_blocked_claim
    ) else 0
    score += 1 if (safe_next_steps or not spec.requires_decision) else 0
    score += 1 if (language in {None, "pl-PL"} or not spec.requires_polish_contract) else 0
    score = min(score, 10)

    readiness = _readiness(spec.status, score, errors)
    return {
        "surface_id": spec.surface_id,
        "path": spec.path,
        "label": spec.label,
        "family": spec.family,
        "status": spec.status,
        "endpoint": spec.endpoint,
        "demo_priority": spec.demo_priority,
        "readiness": readiness,
        "usefulness_score": score,
        "decision_count": decision_count,
        "record_count": record_count,
        "lineage_count": lineage_count,
        "evidence_count": len(evidence_ids),
        "source_connector_count": len(source_connectors),
        "action_count": len(action_ids),
        "blocked_claim_count": len(blocked_claims),
        "safe_next_step_count": len(safe_next_steps),
        "sample_evidence_ids": evidence_ids[:4],
        "sample_source_connectors": source_connectors[:4],
        "sample_action_ids": action_ids[:4],
        "sample_blocked_claims": blocked_claims[:4],
        "sample_next_steps": sample_next_steps,
        "private_source_trace": private_source_trace,
        "auxiliary_checks": auxiliary_checks,
        "errors": errors,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# WILQ dashboard usefulness audit",
        "",
        f"- API: `{report['api_base']}`",
        f"- Surfaces: {report['surface_count']}",
        f"- Demo-ready: {report['demo_ready_count']}",
        f"- Review-ready: {report['review_ready_count']}",
        f"- Blocked: {report['blocked_count']}",
        f"- Pass: `{str(report['pass']).lower()}`",
        "",
        "| Ekran | Status | Gotowość | Score | Rekordy | Ślady | Dowody | Akcje | "
        "Decyzje | Następny krok |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for surface in report["surfaces"]:
        next_step = surface["sample_next_steps"][0] if surface["sample_next_steps"] else "-"
        row = (
            "| {label} | `{status}` | `{readiness}` | {score} | {records} | "
            "{lineage} | {evidence} | {actions} | {decisions} | {next_step} |"
        )
        lines.append(
            row.format(
                label=surface["label"],
                status=surface["status"],
                readiness=surface["readiness"],
                score=surface["usefulness_score"],
                records=surface["record_count"],
                lineage=surface["lineage_count"],
                evidence=surface["evidence_count"],
                actions=surface["action_count"],
                decisions=surface["decision_count"],
                next_step=_markdown_cell(next_step),
            )
        )
    blocked = [surface for surface in report["surfaces"] if surface["errors"]]
    if blocked:
        lines.extend(["", "## Blokady", ""])
        for surface in blocked:
            lines.append(
                f"- {surface['label']} `{surface['path']}`: "
                + "; ".join(surface["errors"])
            )
    auxiliary_checks = [
        (surface, check)
        for surface in report["surfaces"]
        for check in surface.get("auxiliary_checks") or []
    ]
    if auxiliary_checks:
        lines.extend(["", "## Kontrole pomocnicze", ""])
        for surface, check in auxiliary_checks:
            lines.append(
                f"- {surface['label']} `{surface['path']}`: "
                f"`{check['status']}` - {check['summary']}"
            )
    return "\n".join(lines)


def _safe_fetch(api_base: str, spec: SurfaceSpec) -> dict[str, Any]:
    try:
        payload = _fetch_json(api_base, spec)
    except RuntimeError as error:
        return {
            "payload": {},
            "fetch_error": True,
            "errors": [str(error)],
        }
    errors: list[str] = []
    auxiliary_payloads: dict[str, Any] = {}
    for endpoint in spec.auxiliary_endpoints:
        try:
            auxiliary_payloads[endpoint] = _fetch_json_endpoint(api_base, endpoint)
        except RuntimeError as error:
            errors.append(str(error))
    return {
        "payload": payload,
        "auxiliary_payloads": auxiliary_payloads,
        "errors": errors,
    }


def _fetch_json(api_base: str, spec: SurfaceSpec) -> Any:
    return _fetch_json_endpoint(
        api_base,
        spec.endpoint,
        method=spec.method,
        request_json=spec.request_json,
    )


def _fetch_json_endpoint(
    api_base: str,
    endpoint: str,
    *,
    method: HttpMethod = "GET",
    request_json: dict[str, Any] | None = None,
) -> Any:
    url = f"{api_base.rstrip('/')}{endpoint}"
    data = None
    headers = {}
    if method == "POST":
        data = json.dumps(request_json or {}).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=25) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        raise RuntimeError(f"{endpoint} returned HTTP {error.code}") from error
    except (TimeoutError, URLError) as error:
        raise RuntimeError(f"{endpoint} unreachable: {error}") from error
    except json.JSONDecodeError as error:
        raise RuntimeError(f"{endpoint} did not return JSON") from error


def _find_unique_values(value: Any, key: str) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            if child_key == key:
                found.update(_string_values(child_value))
            else:
                found.update(_find_unique_values(child_value, key))
    elif isinstance(value, list):
        for item in value:
            found.update(_find_unique_values(item, key))
    return found


def _find_action_ids(value: Any) -> set[str]:
    found = _find_unique_values(value, "action_ids")
    found.update(_find_unique_values(value, "action_id"))
    found.update(_find_unique_values(value, "draft_action_ids"))
    if isinstance(value, dict):
        item_id = value.get("id")
        if isinstance(item_id, str) and _looks_like_action_id(item_id):
            found.add(item_id)
        for child in value.values():
            found.update(_find_action_ids(child))
    elif isinstance(value, list):
        for item in value:
            found.update(_find_action_ids(item))
    return found


def _looks_like_action_id(value: str) -> bool:
    return value.startswith("act_") or value.startswith("service_profile_review_")


def _string_values(value: Any) -> set[str]:
    if isinstance(value, str) and value.strip():
        return {value.strip()}
    if isinstance(value, list):
        return {
            item.strip()
            for item in value
            if isinstance(item, str) and item.strip()
        }
    return set()


def _decision_count(value: Any) -> int:
    if isinstance(value, dict):
        count = 0
        for key in (
            "daily_decisions",
            "decision_queue",
            "tactical_items",
            "sections",
            "proposals",
            "cards",
        ):
            child = value.get(key)
            if isinstance(child, list):
                count += len(child)
        if _looks_decision_like(value):
            count += 1
        return count + sum(_decision_count(child) for child in value.values())
    if isinstance(value, list):
        return sum(_decision_count(item) for item in value)
    return 0


def _record_count(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        for key in ("items", "cards", "actions", "opportunities", "workflows", "records"):
            child = value.get(key)
            if isinstance(child, list):
                return len(child)
    return 0


def _looks_decision_like(value: dict[str, Any]) -> bool:
    return bool(
        value.get("decision_type")
        or value.get("decision_state")
        or value.get("next_step")
        or value.get("operator_next_step")
        or value.get("operator_action")
        or value.get("safe_next_step")
    )


def _safe_next_steps(value: Any) -> list[str]:
    values: list[str] = []
    if isinstance(value, dict):
        for key in (
            "primary_next_step",
            "next_step",
            "operator_next_step",
            "operator_action",
            "safe_next_step",
            "allowed_next_step",
        ):
            child = value.get(key)
            if isinstance(child, str) and child.strip():
                values.append(child.strip())
        for child in value.values():
            values.extend(_safe_next_steps(child))
    elif isinstance(value, list):
        for item in value:
            values.extend(_safe_next_steps(item))
    return _dedupe(values)


def _has_positive_count(value: Any, key: str) -> bool:
    if isinstance(value, dict):
        child = value.get(key)
        if isinstance(child, int) and child > 0:
            return True
        return any(_has_positive_count(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_has_positive_count(item, key) for item in value)
    return False


def _has_blockers(value: Any) -> bool:
    if isinstance(value, dict):
        child = value.get("blockers")
        if isinstance(child, list) and len(child) > 0:
            return True
        return any(_has_blockers(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_blockers(item) for item in value)
    return False


def _evaluate_auxiliary_checks(
    spec: SurfaceSpec,
    auxiliary_payloads: dict[str, Any],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    authoring_endpoint = "/api/content/wordpress/authoring-profile"
    if authoring_endpoint in spec.auxiliary_endpoints:
        checks.append(
            _wordpress_authoring_profile_check(
                auxiliary_payloads.get(authoring_endpoint),
                authoring_endpoint,
            )
        )
    return checks


def _private_source_trace_check(payload: Any) -> dict[str, Any]:
    queue = _private_review_queue(payload)
    if not queue:
        return {
            "ready": False,
            "item_count": 0,
            "trace_ready_count": 0,
            "errors": ["missing private source review queue"],
        }
    errors: list[str] = []
    trace_ready_count = 0
    required_list_fields = ("data_classes", "source_block_refs", "eval_case_ids")
    required_text_fields = ("retention_decision", "source_locator_label", "owner_role")
    for index, item in enumerate(queue, start=1):
        if not isinstance(item, dict):
            errors.append(f"private source review item {index} is not an object")
            continue
        missing_fields: list[str] = []
        for field in required_list_fields:
            value = item.get(field)
            if not isinstance(value, list) or not any(str(entry).strip() for entry in value):
                missing_fields.append(field)
        for field in required_text_fields:
            if not str(item.get(field) or "").strip():
                missing_fields.append(field)
        if item.get("redacted") is not True:
            missing_fields.append("redacted")
        if item.get("source_trace_ready") is not True:
            missing_fields.append("source_trace_ready")
        if missing_fields:
            errors.append(
                f"private source review item {index} missing trace fields: "
                + ", ".join(missing_fields)
            )
        else:
            trace_ready_count += 1
    return {
        "ready": not errors,
        "item_count": len(queue),
        "trace_ready_count": trace_ready_count,
        "errors": errors,
    }


def _private_review_queue(payload: Any) -> list[Any]:
    if not isinstance(payload, dict):
        return []
    source_fact_coverage = payload.get("source_fact_coverage")
    if not isinstance(source_fact_coverage, dict):
        return []
    queue = source_fact_coverage.get("private_review_queue")
    return queue if isinstance(queue, list) else []


def _wordpress_authoring_profile_check(
    payload: Any,
    endpoint: str,
) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return {
            "id": "wordpress_authoring_profile",
            "endpoint": endpoint,
            "status": "blocked",
            "summary": "Brak profilu authoringu WordPress/ACF.",
            "errors": ["missing wordpress authoring profile"],
        }
    acf = payload.get("acf") if isinstance(payload.get("acf"), dict) else {}
    rest_api = payload.get("rest_api") if isinstance(payload.get("rest_api"), dict) else {}
    wp_cli = payload.get("wp_cli") if isinstance(payload.get("wp_cli"), dict) else {}
    write_boundary = (
        payload.get("write_boundary")
        if isinstance(payload.get("write_boundary"), dict)
        else {}
    )
    blockers = payload.get("blockers") if isinstance(payload.get("blockers"), list) else []
    layout_count = len(acf.get("layouts") or [])
    if payload.get("profile_version") != "wordpress_authoring_profile_v1":
        errors.append("wordpress authoring profile version mismatch")
    if rest_api.get("status") != "configured":
        errors.append("wordpress REST authoring is not configured")
    if wp_cli.get("status") != "configured":
        errors.append("read-only WP-CLI fallback is not configured")
    if acf.get("layouts_discovered") is not True or layout_count == 0:
        errors.append("ACF flexible content layouts are not discovered")
    if blockers:
        blocker_codes = [
            str(blocker.get("code") or blocker.get("id") or "unknown")
            for blocker in blockers
            if isinstance(blocker, dict)
        ]
        errors.append(
            "wordpress authoring profile has blockers: "
            + ", ".join(blocker_codes or ["unknown"])
        )
    expected_false_fields = (
        "direct_vendor_write_allowed",
        "live_write_enabled",
        "publish_allowed",
        "destructive_update_allowed",
        "external_write_attempted",
    )
    for field in expected_false_fields:
        if write_boundary.get(field) is not False:
            errors.append(f"wordpress authoring write boundary not false: {field}")
    return {
        "id": "wordpress_authoring_profile",
        "endpoint": endpoint,
        "status": "ready" if not errors else "blocked",
        "summary": (
            f"REST={rest_api.get('status') or 'unknown'}, "
            f"WP-CLI={wp_cli.get('status') or 'unknown'}, "
            f"ACF layouts={layout_count}, writes blocked="
            f"{not any(write_boundary.get(field) is not False for field in expected_false_fields)}"
        ),
        "errors": errors,
    }


def _readiness(status: SurfaceStatus, score: int, errors: list[str]) -> str:
    if errors or score < 6:
        return "blocked"
    if status in {"experimental", "placeholder", "technical"}:
        return "review_ready"
    if score >= 8:
        return "demo_ready"
    return "review_ready"


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def _markdown_cell(value: str) -> str:
    escaped = value.replace("|", "\\|").replace("\n", " ").strip()
    if len(escaped) <= 180:
        return escaped
    return escaped[:177].rstrip() + "..."


if __name__ == "__main__":
    raise SystemExit(main())
