#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from typing import Any, cast

from scripts.content_uat_snapshot import (
    exact_candidate_from_snapshot,
    matched_snapshot_for_work_item,
    sales_brief_trace_from_snapshot,
    sales_brief_trace_markdown_lines,
    search_demand_from_snapshot,
    search_demand_markdown_lines,
)

# Operator copy rendered by the imported trace helper includes:
# "ograniczenia wiedzy z dowodami" and "zablokowany albo niedostępny".

SKILL_NAME = "wilq-content-operator"
DEV_HOST = "ekologus.dev.proudsite.pl"
SERVICE_PROFILE_REVIEW_RECORDER = "scripts/record_service_profile_review_result.py"
PUBLIC_PROMOTION_ACTION_ID = "act_prepare_service_profile_knowledge_promotion"
PRIVATE_PROMOTION_ACTION_ID = "act_prepare_service_profile_private_proposal_promotion"
PUBLIC_SERVICE_REVIEW_SCOPES = {"public_service_card"}
PRIVATE_SOURCE_REVIEW_SCOPES = {
    "private_service_proposal",
    "private_claim_policy_proposal",
    "private_evidence_policy_proposal",
}
PRIVATE_SERVICE_REVIEW_SCOPES = {"private_service_proposal"}
PRIVATE_POLICY_REVIEW_SCOPES = {
    "private_claim_policy_proposal",
    "private_evidence_policy_proposal",
}


def request_json(
    api_base: str,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    *,
    timeout: int = 180,
) -> Any:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{api_base.rstrip('/')}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")[:500]
        raise SystemExit(f"HTTP {exc.code} from {path}: {message}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not reach WILQ API at {api_base}: {exc.reason}") from exc


def require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SystemExit(f"{label} must be an object")
    return value


def review_scope(action: dict[str, Any]) -> str:
    return str(action.get("review_scope") or "").strip()


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def review_requirements_summary(action: dict[str, Any]) -> str:
    requirements = [
        item
        for item in as_list(action.get("review_requirements"))
        if isinstance(item, dict)
    ]
    if not requirements:
        return ""
    required_fields = [
        str(item.get("field"))
        for item in requirements
        if item.get("required") is True and item.get("field")
    ]
    follow_up_rules = [
        str(item.get("blocking_rule"))
        for item in requirements
        if item.get("field") == "follow_up_beads" and item.get("blocking_rule")
    ]
    parts: list[str] = []
    if required_fields:
        parts.append("wymagane pola: " + ", ".join(required_fields))
    if follow_up_rules:
        parts.append("follow_up_beads: " + "; ".join(follow_up_rules))
    return "; ".join(parts)


def safe_enrichment(api_base: str, work_item_id: str) -> dict[str, Any]:
    try:
        return require_dict(
            request_json(api_base, "GET", f"/api/content/work-items/{work_item_id}/enrichment"),
            "content enrichment response",
        )
    except SystemExit as exc:
        return {
            "status": "blocked",
            "blocker": str(exc),
        }


def safe_workflow_snapshot(api_base: str, work_item_id: str) -> dict[str, Any]:
    try:
        return require_dict(
            request_json(api_base, "GET", f"/api/content/work-items/{work_item_id}/snapshot"),
            "content workflow snapshot response",
        )
    except SystemExit as exc:
        return {
            "status": "blocked",
            "blocker": str(exc),
        }


def safe_action(api_base: str, action_id: str) -> dict[str, Any]:
    try:
        return require_dict(
            request_json(api_base, "GET", f"/api/actions/{action_id}"),
            f"action {action_id}",
        )
    except SystemExit as exc:
        return {
            "id": action_id,
            "status": "blocked",
            "blocker": str(exc),
            "payload": {},
        }


def promotion_preview_summary(action: dict[str, Any]) -> dict[str, Any]:
    raw_payload = action.get("payload")
    payload: dict[str, Any] = raw_payload if isinstance(raw_payload, dict) else {}
    preview_rows = [
        item
        for item in as_list(payload.get("payload_preview"))
        if isinstance(item, dict)
    ]
    return {
        "action_id": action.get("id"),
        "validation_status": action.get("validation_status"),
        "preview_contract": payload.get("preview_contract"),
        "preview_row_count": len(preview_rows),
        "apply_allowed": payload.get("apply_allowed"),
        "api_mutation_ready": payload.get("api_mutation_ready"),
        "target_card_ids": [
            row.get("target_card_id")
            for row in preview_rows
            if row.get("target_card_id")
        ],
        "review_action_ids": [
            row.get("review_action_id")
            for row in preview_rows
            if row.get("review_action_id")
        ],
    }


def review_result_recorders(
    *,
    public_promotion: dict[str, Any],
    private_promotion: dict[str, Any],
) -> dict[str, Any]:
    public_summary = promotion_preview_summary(public_promotion)
    private_summary = promotion_preview_summary(private_promotion)
    command = (
        f"rtk uv run python {SERVICE_PROFILE_REVIEW_RECORDER} "
        ".local-lab/proof/service-profile-review-result-YYYYMMDD.json "
        "--api-base http://127.0.0.1:8000 --format markdown"
    )
    return {
        "recorder_script": SERVICE_PROFILE_REVIEW_RECORDER,
        "command_template": command,
        "live_review_requirements_authoritative": True,
        "review_requirements_note": (
            "Minimal field lists are a floor. The recorder validates the current "
            "API-owned review_requirements for each live action_id."
        ),
        "public_review": {
            "review_type": "public_service_cards",
            "result_report_type": "service_profile_public_card_review_result_v1",
            "promotion_preview": public_summary,
            "minimal_payload_required_fields": [
                "data_review",
                "reviewer",
                "scope_label",
                "decisions[].action_id",
                "decisions[].target_card_id",
                "decisions[].decision",
                "decisions[].source_trace_clear",
                "decisions[].blocked_claims_reviewed",
                "decisions[].notes",
            ],
        },
        "private_review": {
            "review_type": "private_source_proposals",
            "result_report_type": "service_profile_private_proposal_review_result_v1",
            "promotion_preview": private_summary,
            "minimal_payload_required_fields": [
                "review_type",
                "data_review",
                "reviewer",
                "scope_label",
                "decisions[].action_id",
                "decisions[].target_card_id",
                "decisions[].decision",
                "decisions[].source_trace_clear",
                "decisions[].blocked_claims_reviewed",
                "decisions[].data_classes_confirmed",
                "decisions[].source_block_refs_confirmed",
                "decisions[].freshness_status_confirmed",
                "decisions[].audience_scope_confirmed",
                "decisions[].retention_decision_confirmed",
                "decisions[].deletion_path_confirmed",
                "decisions[].eval_gates_confirmed",
                "decisions[].notes",
            ],
        },
        "safety_note": (
            "Recorder zapisuje tylko wynik review. Nie promuje source facts ani "
            "knowledge cards; zatwierdzone decyzje muszą istnieć w prepare-only "
            "promotion preview."
        ),
    }


def service_profile_uat_summary(api_base: str) -> dict[str, Any]:
    profile = require_dict(
        request_json(api_base, "GET", "/api/content/service-profile"),
        "service profile response",
    )
    coverage_summary = require_dict(
        profile.get("coverage_summary") or {},
        "service profile coverage summary",
    )
    private_summary = require_dict(
        profile.get("private_source_proposal_summary") or {},
        "private source proposal summary",
    )
    coverage_gaps = [
        {
            "gap_id": gap.get("gap_id"),
            "severity": gap.get("severity"),
            "label": gap.get("label"),
            "safe_next_step": gap.get("safe_next_step"),
        }
        for gap in as_list(profile.get("coverage_gaps"))
        if isinstance(gap, dict)
    ]
    review_actions = [
        action
        for action in as_list(profile.get("review_actions"))
        if isinstance(action, dict)
    ]
    public_service_review_actions = [
        {
            "action_id": action.get("action_id"),
            "label": action.get("label"),
            "reason": action.get("reason"),
            "review_scope": action.get("review_scope"),
            "priority": action.get("priority"),
            "decision_options": action.get("decision_options") or [],
            "review_requirements": action.get("review_requirements") or [],
            "blocked_write_claim": action.get("blocked_write_claim"),
            "required_human_role": action.get("required_human_role"),
            "target_card_id": action.get("target_card_id"),
            "mode": action.get("mode"),
        }
        for action in review_actions
        if review_scope(action) in PUBLIC_SERVICE_REVIEW_SCOPES
    ]
    private_review_actions = [
        {
            "action_id": action.get("action_id"),
            "label": action.get("label"),
            "reason": action.get("reason"),
            "review_scope": action.get("review_scope"),
            "priority": action.get("priority"),
            "decision_options": action.get("decision_options") or [],
            "review_requirements": action.get("review_requirements") or [],
            "blocked_write_claim": action.get("blocked_write_claim"),
            "required_human_role": action.get("required_human_role"),
            "target_card_id": action.get("target_card_id"),
            "mode": action.get("mode"),
        }
        for action in review_actions
        if review_scope(action) in PRIVATE_SOURCE_REVIEW_SCOPES
    ]
    private_proposal_details = [
        {
            "proposal_id": proposal.get("proposal_id"),
            "source_id": proposal.get("source_id"),
            "source_type": proposal.get("source_type"),
            "privacy_class": proposal.get("privacy_class"),
            "scope": proposal.get("scope"),
            "target_card_id": proposal.get("target_card_id"),
            "target_card_title": proposal.get("target_card_title"),
            "freshness_status": proposal.get("freshness_status"),
            "review_status": proposal.get("review_status"),
            "support_level": proposal.get("support_level"),
            "risk_tier": proposal.get("risk_tier"),
            "data_classes": proposal.get("data_classes") or [],
            "source_block_refs": proposal.get("source_block_refs") or [],
            "retention_decision": proposal.get("retention_decision"),
            "deletion_path": proposal.get("deletion_path") or [],
            "eval_case_ids": proposal.get("eval_case_ids") or [],
            "confidence_label": proposal.get("confidence_label"),
            "audience": proposal.get("audience"),
            "blocked_claims": proposal.get("blocked_claims") or [],
            "safe_next_step": proposal.get("safe_next_step"),
            "promotion_allowed": proposal.get("promotion_allowed"),
            "redacted": proposal.get("redacted"),
        }
        for proposal in as_list(profile.get("private_source_proposals"))
        if isinstance(proposal, dict)
    ]
    private_service_review_actions = [
        action
        for action in private_review_actions
        if review_scope(action) in PRIVATE_SERVICE_REVIEW_SCOPES
    ]
    private_policy_review_actions = [
        action
        for action in private_review_actions
        if review_scope(action) in PRIVATE_POLICY_REVIEW_SCOPES
    ]
    api_review_action_summary = profile.get("review_action_summary")
    review_action_summary = (
        api_review_action_summary
        if isinstance(api_review_action_summary, dict)
        else {
            "total_count": len(review_actions),
            "public_service_review_count": len(public_service_review_actions),
            "private_review_count": len(private_review_actions),
            "private_service_review_count": len(private_service_review_actions),
            "private_policy_review_count": len(private_policy_review_actions),
            "review_request_count": sum(
                1 for action in review_actions if action.get("mode") == "review_request"
            ),
        }
    )
    public_promotion = safe_action(api_base, PUBLIC_PROMOTION_ACTION_ID)
    private_promotion = safe_action(api_base, PRIVATE_PROMOTION_ACTION_ID)
    return {
        "endpoint": "/api/content/service-profile",
        "read_only": profile.get("read_only"),
        "production_depth_ready": coverage_summary.get("ready_for_daily_content"),
        "status_label": coverage_summary.get("status_label"),
        "safe_next_step": coverage_summary.get("safe_next_step"),
        "service_card_count": coverage_summary.get("service_card_count"),
        "approved_current_count": coverage_summary.get("approved_current_count"),
        "source_backed_review_required_count": coverage_summary.get(
            "source_backed_review_required_count"
        ),
        "coverage_gaps": coverage_gaps,
        "private_source_proposals": {
            "proposal_count": private_summary.get("proposal_count"),
            "service_proposal_count": private_summary.get("service_proposal_count"),
            "claim_policy_proposal_count": private_summary.get("claim_policy_proposal_count"),
            "evidence_requirement_proposal_count": private_summary.get(
                "evidence_requirement_proposal_count"
            ),
            "review_required_count": private_summary.get("review_required_count"),
            "approved_count": private_summary.get("approved_count"),
            "promotion_ready": private_summary.get("promotion_ready"),
            "promotion_blocked_reason": private_summary.get("promotion_blocked_reason"),
            "promotion_checklist": private_summary.get("promotion_checklist") or [],
            "redacted": private_summary.get("redacted"),
        },
        "private_proposal_details": private_proposal_details,
        "review_action_summary": review_action_summary,
        "public_service_review_actions": public_service_review_actions,
        "private_review_actions": private_review_actions,
        "private_service_review_actions": private_service_review_actions,
        "private_policy_review_actions": private_policy_review_actions,
        "review_result_recorders": review_result_recorders(
            public_promotion=public_promotion,
            private_promotion=private_promotion,
        ),
    }


def packet_item(api_base: str, candidate: dict[str, Any]) -> dict[str, Any]:
    work_item_id = str(candidate.get("work_item_id") or "")
    enrichment_response: dict[str, Any] = (
        safe_enrichment(api_base, work_item_id) if work_item_id else {}
    )
    snapshot_response: dict[str, Any] = (
        safe_workflow_snapshot(api_base, work_item_id) if work_item_id else {}
    )
    matched_snapshot = matched_snapshot_for_work_item(snapshot_response, work_item_id)
    exact_candidate = exact_candidate_from_snapshot(matched_snapshot, work_item_id)
    display_candidate = exact_candidate or candidate
    raw_enrichment = enrichment_response.get("enrichment")
    enrichment: dict[str, Any] = (
        cast(dict[str, Any], raw_enrichment)
        if isinstance(raw_enrichment, dict)
        else enrichment_response
    )
    response_blockers = enrichment_response.get("blockers") if isinstance(
        enrichment_response.get("blockers"), list
    ) else []
    final_url = display_candidate.get("final_canonical_url") or display_candidate.get(
        "intended_final_url"
    )
    preview_url = display_candidate.get("preview_url")
    final_url_status = (
        "blocked_dev_url"
        if isinstance(final_url, str) and DEV_HOST in final_url
        else "ready_or_missing"
    )
    return {
        "work_item_id": work_item_id,
        "title": display_candidate.get("title"),
        "topic": display_candidate.get("topic"),
        "recommended_mode": display_candidate.get("recommended_mode"),
        "recommended_mode_label": display_candidate.get("recommended_mode_label"),
        "status_label": display_candidate.get("status_label"),
        "reason": display_candidate.get("reason"),
        "safe_next_step": display_candidate.get("safe_next_step"),
        "evidence_ids": display_candidate.get("evidence_ids") or [],
        "source_connectors": display_candidate.get("source_connectors") or [],
        "final_canonical_url": final_url,
        "preview_url": preview_url,
        "final_url_status": final_url_status,
        "preflight_status": display_candidate.get("preflight_status"),
        "duplicate_canonical_risk_summary": display_candidate.get(
            "duplicate_canonical_risk_summary"
        ),
        "measurement_readiness": display_candidate.get("measurement_readiness"),
        "blockers": display_candidate.get("blockers") or [],
        "search_demand": search_demand_from_snapshot(matched_snapshot),
        "enrichment_summary": {
            "status": enrichment.get("status") or enrichment.get("enrichment_status"),
            "intent": enrichment.get("intent_label")
            or enrichment.get("intent")
            or enrichment.get("search_intent"),
            "service_fit": enrichment.get("service_fit")
            or enrichment.get("service_fit_label")
            or enrichment.get("service_fit_status"),
            "buyer_problem": enrichment.get("buyer_problem")
            or enrichment.get("buyer_problem_label"),
            "safe_next_step": enrichment.get("safe_next_step"),
            "blockers": enrichment.get("blockers") or response_blockers,
        },
        "sales_brief_trace": sales_brief_trace_from_snapshot(matched_snapshot),
    }


def uat_readiness(
    *,
    queue: dict[str, Any],
    service_profile: dict[str, Any],
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    blockers: list[str] = []
    actionable_items = [
        item
        for item in items
        if item.get("recommended_mode") != "block" and not item.get("blockers")
    ]
    actionable_candidate_count = queue.get("actionable_candidate_count")
    if not isinstance(actionable_candidate_count, int):
        actionable_candidate_count = len(actionable_items)
    if actionable_candidate_count == 0:
        blockers.append("brak gotowego itemu contentowego bez blockerów")
    if service_profile.get("production_depth_ready") is not True:
        blockers.append("Service Profile nie jest production-depth")
    if service_profile.get("public_service_review_actions"):
        blockers.append("publiczne karty usług wymagają review Wilka/ownera")
    if service_profile.get("private_review_actions"):
        blockers.append("prywatne propozycje wymagają review Wilka/ownera")
    if queue.get("queue_status") == "blocked":
        blockers.append("kolejka content workflow ma status blocked")
    return {
        "status": "blocked_for_full_uat" if blockers else "ready_for_uat",
        "blockers": blockers,
        "recommended_scope": (
            "review/blokady i traceability"
            if blockers
            else "pełna sesja contentowa z briefem i wariantem szkicu"
        ),
        "actionable_candidate_count": actionable_candidate_count,
        "shown_actionable_item_ids": [item["work_item_id"] for item in actionable_items],
    }


def marketer_summary_lines(packet: dict[str, Any]) -> list[str]:
    readiness = packet.get("uat_readiness")
    readiness_dict = readiness if isinstance(readiness, dict) else {}
    service_profile = packet.get("service_profile")
    service_profile_dict = service_profile if isinstance(service_profile, dict) else {}
    status = str(readiness_dict.get("status") or "")
    blockers = [str(value) for value in readiness_dict.get("blockers") or []]
    if status == "blocked_for_full_uat":
        current_state = (
            "Pełny content UAT jest zablokowany. Ta sesja ma ocenić, czy "
            "Wilku rozumie źródła, blokady, język i następny bezpieczny krok."
        )
    else:
        current_state = (
            "Można przejść do pełnej sesji content UAT, ale nadal obowiązuje "
            "review człowieka przed draftem, WordPressem i claimami sukcesu."
        )
    first_blocker = blockers[0] if blockers else "brak głównej blokady"
    safe_next_step = str(
        service_profile_dict.get("safe_next_step")
        or "Wybierz jeden item i sprawdź źródła, blokady oraz CTA."
    )
    return [
        f"Co Wilku ma teraz ocenić: {current_state}",
        f"Dlaczego pełny UAT jest zablokowany: {first_blocker}.",
        f"Co można bezpiecznie zrobić: {safe_next_step}",
        (
            "Czego WILQ nadal nie może obiecać: finalnego draftu, publikacji, "
            "production-depth wiedzy, braku duplikacji ani efektu SEO bez "
            "review i measurement window."
        ),
        (
            "Jaką decyzję wpisać po review: zatwierdź, popraw, odrzuć albo "
            "odśwież źródła."
        ),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Build {SKILL_NAME} Wilku UAT packet")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="Output format for the live UAT packet.",
    )
    args = parser.parse_args()

    health = require_dict(request_json(args.api_base, "GET", "/api/health"), "health response")
    if health.get("status") != "ok":
        raise SystemExit(f"WILQ API health is not ok: {health}")

    queue = require_dict(
        request_json(args.api_base, "GET", "/api/content/work-items/queue"),
        "content queue response",
    )
    candidates = [
        candidate
        for candidate in as_list(queue.get("candidates"))
        if isinstance(candidate, dict)
    ]
    service_profile = service_profile_uat_summary(args.api_base)
    items = [packet_item(args.api_base, candidate) for candidate in candidates[: args.limit]]
    readiness = uat_readiness(queue=queue, service_profile=service_profile, items=items)
    packet = {
        "skill": SKILL_NAME,
        "purpose": "UAT sesji pracy contentowej Wilka przez WILQ API dla 3-5 itemów",
        "queue_status": queue.get("queue_status"),
        "operator_summary": queue.get("operator_summary"),
        "candidate_count": queue.get("candidate_count"),
        "actionable_candidate_count": queue.get("actionable_candidate_count"),
        "service_profile": service_profile,
        "uat_readiness": readiness,
        "items": items,
        "uat_tasks": [
            (
                "Sprawdź Service Profile: powiedz, które luki, public service review "
                "actions i private review actions blokują production-depth."
            ),
            "Wybierz jeden item, który da się odświeżyć albo scalić bez tworzenia duplikatu.",
            "Wskaż blocker, który jasno mówi, dlaczego nie wolno jeszcze pisać.",
            "Sprawdź, czy final canonical nie jest adresem dev/staging.",
            "Powiedz, czy safe_next_step mówi dokładnie, co zrobić dalej.",
            "Potwierdź, czy measurement readiness blokuje zbyt wczesny claim sukcesu.",
            (
                "Zadaj pytanie 'skąd to wzięło?' i sprawdź, czy WILQ pokazuje "
                "evidence IDs oraz source connectors."
            ),
        ],
        "hard_rules": [
            "Brak evidence ID oznacza brak rekomendacji.",
            "Brak source connector oznacza brak rekomendacji.",
            "Review-required wiedza może wspierać UAT, ale nie odblokowuje production-depth.",
            "Public service review action nie promuje faktu ani karty wiedzy.",
            "Private proposal review action nie promuje faktu ani karty wiedzy.",
            "Dev URL nie jest canonical ani SEO evidence.",
            "WordPress pozostaje draft-only albo podgląd zmian.",
            "Sukces lub porażka treści wymagają gotowego measurement outcome.",
        ],
    }
    packet["marketer_summary"] = marketer_summary_lines(packet)

    if args.format == "json":
        print(json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    print(f"# {packet['purpose']}")
    print()
    print(f"Status kolejki: {packet['queue_status']}")
    print(f"Podsumowanie: {packet['operator_summary']}")
    print()
    print("## Krótko dla Wilka")
    marketer_summary = packet.get("marketer_summary")
    if isinstance(marketer_summary, list):
        for line in marketer_summary:
            print(f"- {line}")
    print()
    service_profile_raw = packet.get("service_profile")
    if not isinstance(service_profile_raw, dict):
        raise SystemExit("Service Profile UAT summary must be an object")
    service_profile_md = cast(dict[str, Any], service_profile_raw)
    readiness_raw = packet.get("uat_readiness")
    if not isinstance(readiness_raw, dict):
        raise SystemExit("UAT readiness must be an object")
    readiness_md = cast(dict[str, Any], readiness_raw)
    print("## Gotowość UAT")
    print(f"- status: {readiness_md['status']}")
    print(f"- zakres: {readiness_md['recommended_scope']}")
    readiness_blockers = [str(value) for value in readiness_md.get("blockers") or []]
    print(f"- blokady: {', '.join(readiness_blockers) or 'brak'}")
    print()
    print("## Service Profile")
    print(f"- endpoint: `{service_profile_md['endpoint']}`")
    print(f"- read-only: {service_profile_md['read_only']}")
    print(f"- production-depth: {service_profile_md['production_depth_ready']}")
    print(f"- status: {service_profile_md['status_label']}")
    print(f"- następny krok: {service_profile_md['safe_next_step']}")
    review_action_summary = service_profile_md.get("review_action_summary")
    if isinstance(review_action_summary, dict):
        print(
            "- akcje review: "
            f"{review_action_summary.get('total_count')} razem, "
            f"{review_action_summary.get('public_service_review_count')} publicznych usług, "
            f"{review_action_summary.get('private_review_count')} prywatnych propozycji "
            f"({review_action_summary.get('private_service_review_count')} service, "
            f"{review_action_summary.get('private_policy_review_count')} policy)"
        )
    review_recorders = service_profile_md.get("review_result_recorders")
    if isinstance(review_recorders, dict):
        print(f"- recorder review: `{review_recorders.get('recorder_script')}`")
        public_recorder = review_recorders.get("public_review")
        if isinstance(public_recorder, dict):
            public_preview = public_recorder.get("promotion_preview")
            if isinstance(public_preview, dict):
                print(
                    "- public review recorder: "
                    f"{public_recorder.get('result_report_type')}, "
                    f"promotion preview rows={public_preview.get('preview_row_count')}"
                )
        private_recorder = review_recorders.get("private_review")
        if isinstance(private_recorder, dict):
            private_preview = private_recorder.get("promotion_preview")
            if isinstance(private_preview, dict):
                print(
                    "- private review recorder: "
                    f"{private_recorder.get('result_report_type')}, "
                    f"promotion preview rows={private_preview.get('preview_row_count')}"
                )
        safety_note = review_recorders.get("safety_note")
        if safety_note:
            print(f"- recorder safety: {safety_note}")
    private_proposals = service_profile_md.get("private_source_proposals")
    if isinstance(private_proposals, dict):
        print(f"- promocja private proposals: {private_proposals.get('promotion_ready')}")
        print(
            "- zakres private proposals: "
            f"{private_proposals.get('service_proposal_count')} service, "
            f"{private_proposals.get('claim_policy_proposal_count')} claim-policy, "
            f"{private_proposals.get('evidence_requirement_proposal_count')} evidence-policy"
        )
        blocked_reason = private_proposals.get("promotion_blocked_reason")
        if blocked_reason:
            print(f"- blokada promocji: {blocked_reason}")
        promotion_checklist = private_proposals.get("promotion_checklist")
        if isinstance(promotion_checklist, list) and promotion_checklist:
            print("- warunki przed reviewed source fact:")
            for item in promotion_checklist:
                print(f"  - {item}")
    proposal_details = service_profile_md.get("private_proposal_details")
    if isinstance(proposal_details, list) and proposal_details:
        print("- szczegóły private proposals:")
        for raw_proposal in proposal_details:
            if not isinstance(raw_proposal, dict):
                continue
            blocked_claims = [
                str(value) for value in raw_proposal.get("blocked_claims") or []
            ]
            print(
                f"  - {raw_proposal.get('target_card_title')}: "
                f"status={raw_proposal.get('review_status')}, "
                f"support={raw_proposal.get('support_level')}, "
                f"risk={raw_proposal.get('risk_tier')}, "
                f"promotion_allowed={raw_proposal.get('promotion_allowed')}"
            )
            if blocked_claims:
                print(f"    claimy zablokowane: {', '.join(blocked_claims)}")
            data_classes = [str(value) for value in raw_proposal.get("data_classes") or []]
            source_block_refs = [
                str(value) for value in raw_proposal.get("source_block_refs") or []
            ]
            deletion_path = [str(value) for value in raw_proposal.get("deletion_path") or []]
            eval_case_ids = [str(value) for value in raw_proposal.get("eval_case_ids") or []]
            if data_classes:
                print(f"    klasy danych: {', '.join(data_classes)}")
            if source_block_refs:
                print(f"    source block refs: {', '.join(source_block_refs)}")
            if raw_proposal.get("retention_decision"):
                print(f"    retencja: {raw_proposal.get('retention_decision')}")
            if raw_proposal.get("freshness_status"):
                print(f"    aktualność: {raw_proposal.get('freshness_status')}")
            if raw_proposal.get("audience"):
                print(f"    audience: {raw_proposal.get('audience')}")
            if deletion_path:
                print(f"    ścieżka usunięcia: {'; '.join(deletion_path)}")
            if eval_case_ids:
                print(f"    eval gates: {', '.join(eval_case_ids)}")
    gaps = service_profile_md.get("coverage_gaps")
    if isinstance(gaps, list) and gaps:
        print("- luki:")
        for raw_gap in gaps:
            if isinstance(raw_gap, dict):
                print(
                    f"  - `{raw_gap.get('gap_id')}`: {raw_gap.get('label')} "
                    f"({raw_gap.get('severity')})"
                )
    public_actions = service_profile_md.get("public_service_review_actions")
    if isinstance(public_actions, list) and public_actions:
        print("- public service review actions:")
        for raw_action in public_actions:
            if isinstance(raw_action, dict):
                print(
                    f"  - `{raw_action.get('action_id')}` "
                    f"({raw_action.get('target_card_id')}): "
                    f"{raw_action.get('label')} -> {raw_action.get('blocked_write_claim')}"
                )
                requirements_summary = review_requirements_summary(raw_action)
                if requirements_summary:
                    print(f"    wymagania review: {requirements_summary}")
    actions = service_profile_md.get("private_review_actions")
    if isinstance(actions, list) and actions:
        print("- private review actions:")
        for raw_action in actions:
            if isinstance(raw_action, dict):
                print(
                    f"  - `{raw_action.get('action_id')}`: "
                    f"{raw_action.get('label')} -> {raw_action.get('blocked_write_claim')}"
                )
                requirements_summary = review_requirements_summary(raw_action)
                if requirements_summary:
                    print(f"    wymagania review: {requirements_summary}")
    policy_actions = service_profile_md.get("private_policy_review_actions")
    if isinstance(policy_actions, list) and policy_actions:
        print("- private policy review actions:")
        for raw_action in policy_actions:
            if isinstance(raw_action, dict):
                print(
                    f"  - `{raw_action.get('action_id')}`: "
                    f"{raw_action.get('label')} -> {raw_action.get('blocked_write_claim')}"
                )
                requirements_summary = review_requirements_summary(raw_action)
                if requirements_summary:
                    print(f"    wymagania review: {requirements_summary}")
    print()
    packet_items = packet.get("items")
    if not isinstance(packet_items, list):
        raise SystemExit("UAT packet items must be a list")
    for raw_item in packet_items:
        if not isinstance(raw_item, dict):
            raise SystemExit("UAT packet item must be an object")
        item = cast(dict[str, Any], raw_item)
        evidence_ids = [str(value) for value in item.get("evidence_ids") or []]
        source_connectors = [str(value) for value in item.get("source_connectors") or []]
        print(f"## {item['title'] or item['work_item_id']}")
        print(f"- work_item_id: `{item['work_item_id']}`")
        print(f"- tryb: {item['recommended_mode_label']} (`{item['recommended_mode']}`)")
        print(f"- status: {item['status_label']}")
        print(f"- dowody: {', '.join(evidence_ids) or 'brak'}")
        print(f"- źródła danych: {', '.join(source_connectors) or 'brak'}")
        print(f"- final canonical: {item['final_canonical_url'] or 'brak'}")
        print(f"- preview: {item['preview_url'] or 'brak'}")
        print(f"- następny krok: {item['safe_next_step']}")
        search_demand = item.get("search_demand")
        if isinstance(search_demand, dict):
            for line in search_demand_markdown_lines(search_demand):
                print(line)
        sales_brief_trace = item.get("sales_brief_trace")
        if isinstance(sales_brief_trace, dict):
            for line in sales_brief_trace_markdown_lines(sales_brief_trace):
                print(line)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
