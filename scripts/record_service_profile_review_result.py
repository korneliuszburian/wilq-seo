from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from wilq.content.knowledge.source_facts import ekologus_source_facts

REVIEW_DECISIONS = {"approve", "needs_changes", "stale", "reject"}
REVIEW_TYPES = {"public_service_cards", "private_source_proposals"}
PUBLIC_SERVICE_REVIEW_SCOPES = {"public_service_card"}
PRIVATE_SOURCE_REVIEW_SCOPES = {
    "private_service_proposal",
    "private_claim_policy_proposal",
    "private_evidence_policy_proposal",
}
DEFAULT_REVIEW_TYPE = "public_service_cards"
PROMOTION_ACTION_IDS = {
    "public_service_cards": "act_prepare_service_profile_knowledge_promotion",
    "private_source_proposals": "act_prepare_service_profile_private_proposal_promotion",
}
REQUIRED_TEXT_FIELDS = {
    "data_review": "data review",
    "reviewer": "reviewer",
    "scope_label": "zakres review",
}
REQUIRED_DECISION_TEXT_FIELDS = {
    "action_id": "action ID",
    "target_card_id": "target card ID",
    "decision": "decyzja",
    "notes": "notatki review",
}
REQUIRED_DECISION_BOOLEAN_FIELDS = {
    "source_trace_clear": "czy ślad źródłowy jest czytelny",
    "blocked_claims_reviewed": "czy claimy zablokowane zostały sprawdzone",
}
PRIVATE_DECISION_BOOLEAN_FIELDS = {
    "data_classes_confirmed": "czy klasy danych prywatnego źródła są poprawne",
    "source_block_refs_confirmed": (
        "czy source block refs są wystarczające do śladu źródłowego"
    ),
    "freshness_status_confirmed": (
        "czy aktualność prywatnego źródła została potwierdzona"
    ),
    "audience_scope_confirmed": (
        "czy zakres dostępu/audience prywatnego źródła jest poprawny"
    ),
    "retention_decision_confirmed": (
        "czy decyzja retencji została podjęta albo świadomie zablokowana"
    ),
    "deletion_path_confirmed": "czy ścieżka usunięcia/odrzucenia proposal jest jasna",
    "eval_gates_confirmed": "czy eval gates blokujące unsafe claimy są wskazane",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Waliduje wynik review publicznych kart usług Service Profile. "
            "Nie promuje kart i nie edytuje source facts."
        )
    )
    parser.add_argument("input", nargs="?", help="Ścieżka do JSON z wynikiem review")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument(
        "--review-type",
        choices=tuple(sorted(REVIEW_TYPES)),
        default=DEFAULT_REVIEW_TYPE,
        help="Zakres review używany przy generowaniu przykładu wejścia.",
    )
    parser.add_argument(
        "--print-input-example",
        action="store_true",
        help=(
            "Wypisz JSON do uzupełnienia na podstawie live review_actions i "
            "review_requirements. Nie zapisuje wyniku review."
        ),
    )
    parser.add_argument(
        "--promotion-readiness",
        action="store_true",
        help=(
            "Po walidacji review zbuduj prepare-only promotion readiness preview. "
            "Nie edytuje source facts ani kart."
        ),
    )
    parser.add_argument(
        "--api-base",
        help="Opcjonalnie sprawdza action/card IDs przeciw live Service Profile.",
    )
    args = parser.parse_args()

    try:
        if args.print_input_example:
            if not args.api_base:
                raise RuntimeError("--print-input-example wymaga --api-base")
            live_context = load_live_context(args.api_base)
            example = build_input_example(
                live_context,
                review_type=args.review_type,
            )
            print(json.dumps(example, ensure_ascii=False, indent=2))
            return 0
        if not args.input:
            raise RuntimeError("Podaj ścieżkę input albo użyj --print-input-example")
        payload = load_json(Path(args.input))
        live_context = load_live_context(args.api_base) if args.api_base else None
        if args.promotion_readiness:
            if live_context is None:
                raise RuntimeError("--promotion-readiness wymaga --api-base")
            report = build_promotion_readiness_report(
                payload,
                live_context=live_context,
            )
            if args.format == "json":
                print(json.dumps(report, ensure_ascii=False, indent=2))
            else:
                print(render_promotion_readiness_markdown(report))
            return 0 if report["promotion_request_ready"] is True else 1
        report = build_review_result_report(payload, live_context=live_context)
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(report))
    return 0


def build_input_example(
    live_context: dict[str, Any],
    *,
    review_type: str,
) -> dict[str, Any]:
    if review_type not in REVIEW_TYPES:
        raise RuntimeError(
            "review_type musi mieć wartość "
            f"{' albo '.join(sorted(REVIEW_TYPES))}"
        )
    profile = live_context.get("service_profile")
    if not isinstance(profile, dict):
        raise RuntimeError("Live Service Profile must be an object")
    required_fields_by_action = live_required_review_fields(
        live_context,
        review_type=review_type,
    )
    actions = [
        action
        for action in raw_list(profile.get("review_actions"))
        if isinstance(action, dict)
        and str(action.get("review_scope") or "").strip()
        in review_scopes_for_type(review_type)
    ]
    decisions = [
        input_example_decision(action, required_fields_by_action)
        for action in actions
    ]
    return {
        "review_type": review_type,
        "data_review": "<YYYY-MM-DD>",
        "reviewer": "<imię reviewera>",
        "scope_label": scope_label_for_review_type(review_type),
        "decisions": decisions,
        "follow_up_beads": [
            "<wymagane tylko gdy jakaś decyzja nie jest approve albo ma pole = nie>"
        ],
        "_instruction": (
            "Uzupełnij placeholdery i usuń _instruction przed zapisem wyniku. "
            "Ten JSON jest wygenerowany z live Service Profile review_actions; "
            "promotion nadal wymaga osobnego, audytowanego kroku."
        ),
    }


def input_example_decision(
    action: dict[str, Any],
    required_fields_by_action: dict[str, tuple[dict[str, Any], ...]],
) -> dict[str, Any]:
    action_id = str(action.get("action_id") or "").strip()
    decision: dict[str, Any] = {
        "action_id": action_id,
        "target_card_id": str(action.get("target_card_id") or "").strip(),
        "decision": "approve|needs_changes|stale|reject",
        "notes": "<krótka decyzja Wilka/ownera i powód>",
    }
    for requirement in required_fields_by_action.get(action_id, ()):
        field = str(requirement.get("field") or "").strip()
        if not field or field in decision:
            continue
        requirement_type = str(requirement.get("requirement_type") or "text").strip()
        if requirement_type == "boolean":
            decision[field] = "tak|nie"
        else:
            decision[field] = f"<{field}>"
    decision["follow_up_beads"] = [
        "<opcjonalnie: bead albo krótki follow-up dla tej decyzji>"
    ]
    return decision


def scope_label_for_review_type(review_type: str) -> str:
    if review_type == "private_source_proposals":
        return "prywatne propozycje ekologus-ai"
    return "publiczne karty usług"


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


def build_review_result_report(
    payload: dict[str, Any],
    *,
    live_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    errors = validate_payload(payload, live_context=live_context)
    if errors:
        raise RuntimeError(
            "Niepoprawny wynik Service Profile review:\n- " + "\n- ".join(errors)
        )

    review_type = normalize_review_type(payload.get("review_type"))
    decisions = [normalize_decision(item) for item in raw_list(payload.get("decisions"))]
    follow_up_tasks = list_payload(payload.get("follow_up_beads"))
    blocking_decisions = [
        decision
        for decision in decisions
        if decision["decision"] != "approve"
        or not decision["source_trace_clear"]
        or not decision["blocked_claims_reviewed"]
        or private_governance_blocks(decision, review_type=review_type)
    ]
    approved_count = sum(1 for decision in decisions if decision["decision"] == "approve")
    live_provenance = live_review_provenance(
        live_context=live_context,
        decisions=decisions,
        review_type=review_type,
    )
    overall_status = (
        "review_ready_for_promotion_request"
        if not blocking_decisions
        else "needs_follow_up_before_promotion_request"
    )
    return {
        "report_type": report_type_for_review_type(review_type),
        "date": str(payload["data_review"]).strip(),
        "reviewer": str(payload["reviewer"]).strip(),
        "scope_label": str(payload["scope_label"]).strip(),
        "decision_count": len(decisions),
        "approved_decision_count": approved_count,
        "blocking_decision_count": len(blocking_decisions),
        "decisions": decisions,
        "follow_up_tasks": follow_up_tasks,
        "live_provenance": live_provenance,
        "overall_status": overall_status,
        "promotion_allowed": False,
        "safe_next_step": safe_next_step_for_review_type(
            review_type,
            overall_status=overall_status,
        ),
        "safety_note": safety_note_for_review_type(review_type),
    }


def build_promotion_readiness_report(
    payload: dict[str, Any],
    *,
    live_context: dict[str, Any],
) -> dict[str, Any]:
    review_report = build_review_result_report(payload, live_context=live_context)
    review_type = normalize_review_type(payload.get("review_type"))
    rows = [
        promotion_readiness_row(
            decision,
            review_type=review_type,
            reviewer=review_report["reviewer"],
            live_context=live_context,
        )
        for decision in review_report["decisions"]
        if decision["decision"] == "approve"
    ]
    review_ready = review_report["overall_status"] == "review_ready_for_promotion_request"
    row_blockers = [
        blocker for row in rows for blocker in row["promotion_blockers"]
    ]
    if not rows:
        row_blockers.append("no_approved_review_decisions")
    if not review_ready:
        row_blockers.append("review_result_not_ready_for_promotion_request")
    promotion_request_ready = review_ready and bool(rows) and not row_blockers
    return {
        "report_type": "service_profile_promotion_readiness_v1",
        "review_result_type": review_report["report_type"],
        "reviewer": review_report["reviewer"],
        "review_type": review_type,
        "review_ready": review_ready,
        "promotion_request_ready": promotion_request_ready,
        "promotion_allowed": False,
        "mutation_allowed": False,
        "production_depth_unlocked": False,
        "raw_private_text_included": False,
        "approved_decision_count": len(rows),
        "promotion_blockers": _unique(row_blockers),
        "promotion_request_preview": rows,
        "safe_next_step": promotion_readiness_next_step(promotion_request_ready),
        "safety_note": (
            "Ten raport jest prepare-only. Nie edytuje source_facts.json, nie ustawia "
            "approved_current i nie odblokowuje production-depth."
        ),
    }


def promotion_readiness_row(
    decision: dict[str, Any],
    *,
    review_type: str,
    reviewer: str,
    live_context: dict[str, Any],
) -> dict[str, Any]:
    if review_type == "private_source_proposals":
        return private_promotion_readiness_row(
            decision,
            reviewer=reviewer,
            live_context=live_context,
        )
    return public_promotion_readiness_row(
        decision,
        reviewer=reviewer,
        live_context=live_context,
    )


def public_promotion_readiness_row(
    decision: dict[str, Any],
    *,
    reviewer: str,
    live_context: dict[str, Any],
) -> dict[str, Any]:
    section = live_service_section_by_card_id(live_context).get(decision["target_card_id"], {})
    row = {
        "action_id": decision["action_id"],
        "target_card_id": decision["target_card_id"],
        "review_scope": "public_service_card",
        "reviewer": reviewer,
        "source_fact_ids": list_payload(section.get("source_fact_ids")),
        "evidence_ids": list_payload(section.get("evidence_ids")),
        "source_connectors": list_payload(section.get("source_connector_labels")),
        "blocked_claims": [
            str(rule.get("claim") or rule.get("reason") or "").strip()
            for rule in raw_list(section.get("forbidden_claims"))
            if isinstance(rule, dict)
        ],
        "freshness": str(section.get("freshness_label") or "").strip(),
        "confidence": str(section.get("confidence_label") or "").strip(),
        "raw_private_text_included": False,
    }
    blockers = promotion_row_blockers(row)
    row["promotion_ready"] = not blockers
    row["promotion_blockers"] = blockers
    return row


def private_promotion_readiness_row(
    decision: dict[str, Any],
    *,
    reviewer: str,
    live_context: dict[str, Any],
) -> dict[str, Any]:
    proposal = live_private_proposals_by_target(live_context).get(
        decision["target_card_id"],
        {},
    )
    source_fact = source_fact_by_id().get(str(proposal.get("source_id") or ""))
    row = {
        "action_id": decision["action_id"],
        "target_card_id": decision["target_card_id"],
        "proposal_id": proposal.get("proposal_id"),
        "source_id": proposal.get("source_id"),
        "review_scope": "private_source_proposal",
        "reviewer": reviewer,
        "source_fact_ids": [str(proposal.get("source_id") or "").strip()],
        "evidence_ids": list(source_fact.evidence_ids) if source_fact else [],
        "source_connectors": list(source_fact.source_connectors) if source_fact else [],
        "blocked_claims": list_payload(proposal.get("blocked_claims")),
        "freshness": str(source_fact.freshness_date if source_fact else "").strip(),
        "freshness_status": str(proposal.get("freshness_status") or "").strip(),
        "confidence": (
            str(source_fact.confidence)
            if source_fact
            else str(proposal.get("confidence_label") or "")
        ),
        "audience": proposal.get("audience"),
        "retention_decision": proposal.get("retention_decision"),
        "data_classes": list_payload(proposal.get("data_classes")),
        "source_block_refs": list_payload(proposal.get("source_block_refs")),
        "deletion_path": list_payload(proposal.get("deletion_path")),
        "eval_case_ids": list_payload(proposal.get("eval_case_ids")),
        "raw_private_text_included": False,
    }
    blockers = promotion_row_blockers(row)
    if row["freshness_status"] in {"stale", "unknown", ""}:
        blockers.append("private_freshness_not_usable")
    if row["retention_decision"] in {"pending_owner_decision", "do_not_retain", None, ""}:
        blockers.append("private_retention_not_usable")
    for field in (
        "data_classes",
        "source_block_refs",
        "deletion_path",
        "eval_case_ids",
    ):
        if not row[field]:
            blockers.append(f"missing_{field}")
    row["promotion_ready"] = not blockers
    row["promotion_blockers"] = _unique(blockers)
    return row


def promotion_row_blockers(row: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not list_payload(row.get("source_fact_ids")):
        blockers.append("missing_source_fact_ids")
    if not list_payload(row.get("evidence_ids")):
        blockers.append("missing_evidence_ids")
    if not list_payload(row.get("source_connectors")):
        blockers.append("missing_source_connectors")
    if not list_payload(row.get("blocked_claims")):
        blockers.append("missing_blocked_claims")
    if is_blank_or_placeholder(row.get("freshness")):
        blockers.append("missing_freshness")
    if is_blank_or_placeholder(row.get("confidence")):
        blockers.append("missing_confidence")
    if is_blank_or_placeholder(row.get("reviewer")):
        blockers.append("missing_reviewer")
    if row.get("raw_private_text_included") is True:
        blockers.append("raw_private_text_included")
    return _unique(blockers)


def promotion_readiness_next_step(ready: bool) -> str:
    if ready:
        return (
            "Przygotuj osobny ActionObject promotion request z preview i audytem; "
            "nadal bez bezpośredniej edycji source facts."
        )
    return (
        "Uzupełnij blokery promotion readiness przed osobnym promotion request. "
        "Najczęściej brakuje evidence IDs albo decyzji retencji/freshness dla "
        "prywatnych propozycji."
    )


def validate_payload(
    payload: dict[str, Any],
    *,
    live_context: dict[str, Any] | None = None,
) -> list[str]:
    errors: list[str] = []
    for key, label in REQUIRED_TEXT_FIELDS.items():
        if is_blank_or_placeholder(payload.get(key)):
            errors.append(f"Brak pola albo placeholder: {label}")
    decisions = raw_list(payload.get("decisions"))
    if not decisions:
        errors.append("Brak decyzji review w polu decisions")
        return errors

    review_type = normalize_review_type(payload.get("review_type"))
    if review_type not in REVIEW_TYPES:
        errors.append(
            "review_type musi mieć wartość "
            f"{' albo '.join(sorted(REVIEW_TYPES))}"
        )
        review_type = DEFAULT_REVIEW_TYPE
    live_actions = live_review_actions(live_context, review_type=review_type)
    live_required_fields = live_required_review_fields(
        live_context,
        review_type=review_type,
    )
    live_target_ids = live_target_card_ids(live_context, review_type=review_type)
    live_promotion_preview = live_promotion_preview_actions(
        live_context,
        review_type=review_type,
    )
    follow_up_tasks = list_payload(payload.get("follow_up_beads"))
    has_blocking_decision = False

    seen_action_ids: set[str] = set()
    for index, raw_decision in enumerate(decisions, start=1):
        if not isinstance(raw_decision, dict):
            errors.append(f"Decyzja #{index} musi być obiektem")
            continue
        for key, label in REQUIRED_DECISION_TEXT_FIELDS.items():
            if is_blank_or_placeholder(raw_decision.get(key)):
                errors.append(f"Decyzja #{index}: brak pola albo placeholder: {label}")
        decision_value = str(raw_decision.get("decision") or "").strip()
        if decision_value and decision_value not in REVIEW_DECISIONS:
            errors.append(
                f"Decyzja #{index}: decision musi być jedną z wartości "
                f"{', '.join(sorted(REVIEW_DECISIONS))}"
            )
        for key, label in REQUIRED_DECISION_BOOLEAN_FIELDS.items():
            if normalize_bool(raw_decision.get(key)) is None:
                errors.append(f"Decyzja #{index}: {label} musi mieć wartość tak albo nie")
        if review_type == "private_source_proposals":
            for key, label in PRIVATE_DECISION_BOOLEAN_FIELDS.items():
                if normalize_bool(raw_decision.get(key)) is None:
                    errors.append(
                        f"Decyzja #{index}: {label} musi mieć wartość tak albo nie"
                    )

        action_id = str(raw_decision.get("action_id") or "").strip()
        target_card_id = str(raw_decision.get("target_card_id") or "").strip()
        if action_id:
            if action_id in seen_action_ids:
                errors.append(f"Decyzja #{index}: powtórzony action_id {action_id}")
            seen_action_ids.add(action_id)
        if live_context is not None and action_id:
            live_target = live_actions.get(action_id)
            if live_target is None:
                errors.append(
                    f"Decyzja #{index}: action_id nie występuje w live Service Profile: "
                    f"{action_id}"
                )
            elif target_card_id and live_target != target_card_id:
                errors.append(
                    f"Decyzja #{index}: target_card_id nie pasuje do live action "
                    f"{action_id}: {target_card_id} != {live_target}"
                )
            errors.extend(
                validate_live_required_fields(
                    raw_decision,
                    required_fields=live_required_fields.get(action_id, ()),
                    index=index,
                )
            )
        if live_context is not None and target_card_id and target_card_id not in live_target_ids:
            errors.append(
                f"Decyzja #{index}: target_card_id nie występuje w live Service Profile: "
                f"{target_card_id}"
            )
        if live_context is not None and decision_value == "approve" and action_id:
            promotion_target = live_promotion_preview.get(action_id)
            if promotion_target is None:
                errors.append(
                    f"Decyzja #{index}: action_id nie występuje w live promotion preview: "
                    f"{action_id}"
                )
            elif target_card_id and promotion_target != target_card_id:
                errors.append(
                    f"Decyzja #{index}: target_card_id nie pasuje do promotion preview "
                    f"{action_id}: {target_card_id} != {promotion_target}"
                )

        decision_blocks = (
            decision_value != "approve"
            or normalize_bool(raw_decision.get("source_trace_clear")) is not True
            or normalize_bool(raw_decision.get("blocked_claims_reviewed")) is not True
            or (
                review_type == "private_source_proposals"
                and any(
                    normalize_bool(raw_decision.get(field)) is not True
                    for field in PRIVATE_DECISION_BOOLEAN_FIELDS
                )
            )
        )
        has_blocking_decision = has_blocking_decision or decision_blocks

    if has_blocking_decision and not follow_up_tasks:
        errors.append("Blokujące decyzje review wymagają follow_up_beads")
    return errors


def normalize_review_type(value: Any) -> str:
    if is_blank_or_placeholder(value):
        return DEFAULT_REVIEW_TYPE
    return str(value or "").strip()


def report_type_for_review_type(review_type: str) -> str:
    if review_type == "private_source_proposals":
        return "service_profile_private_proposal_review_result_v1"
    return "service_profile_public_card_review_result_v1"


def safe_next_step_for_review_type(review_type: str, *, overall_status: str) -> str:
    if overall_status != "review_ready_for_promotion_request":
        return "Zamknij follow-upy review przed przygotowaniem promotion request."
    if review_type == "private_source_proposals":
        return (
            "Przygotuj osobny, audytowany private source promotion request dla "
            "zatwierdzonych redacted propozycji."
        )
    return "Przygotuj osobny, audytowany promotion request dla zatwierdzonych kart."


def safety_note_for_review_type(review_type: str) -> str:
    if review_type == "private_source_proposals":
        return (
            "Ten raport zapisuje wynik review prywatnych redacted propozycji. Nie "
            "edytuje source_facts.json, nie zapisuje raw private text, nie promuje "
            "source fact ani knowledge card i nie odblokowuje production-depth."
        )
    return (
        "Ten raport zapisuje wynik review publicznych kart usług. Nie edytuje "
        "source_facts.json, nie zmienia lifecycle kart, nie ustawia "
        "approved_current i nie odblokowuje production-depth."
    )


def normalize_decision(raw_decision: Any) -> dict[str, Any]:
    if not isinstance(raw_decision, dict):
        raise RuntimeError("Decyzja review musi być obiektem")
    decision = {
        "action_id": str(raw_decision["action_id"]).strip(),
        "target_card_id": str(raw_decision["target_card_id"]).strip(),
        "decision": str(raw_decision["decision"]).strip(),
        "source_trace_clear": normalize_bool(raw_decision["source_trace_clear"]),
        "blocked_claims_reviewed": normalize_bool(raw_decision["blocked_claims_reviewed"]),
        "notes": str(raw_decision["notes"]).strip(),
        "follow_up_beads": list_payload(raw_decision.get("follow_up_beads")),
    }
    for field in PRIVATE_DECISION_BOOLEAN_FIELDS:
        if field in raw_decision:
            decision[field] = normalize_bool(raw_decision[field])
    return decision


def private_governance_blocks(decision: dict[str, Any], *, review_type: str) -> bool:
    if review_type != "private_source_proposals":
        return False
    return any(decision.get(field) is not True for field in PRIVATE_DECISION_BOOLEAN_FIELDS)


def load_live_context(api_base: str) -> dict[str, Any]:
    health = request_json(api_base, "GET", "/api/health")
    if not isinstance(health, dict) or health.get("status") != "ok":
        raise RuntimeError(f"WILQ API health is not ok at {api_base}")
    profile = request_json(api_base, "GET", "/api/content/service-profile")
    if not isinstance(profile, dict):
        raise RuntimeError("Live Service Profile must be an object")
    promotion_actions: dict[str, Any] = {}
    for action_id in PROMOTION_ACTION_IDS.values():
        action = request_json(api_base, "GET", f"/api/actions/{action_id}")
        if isinstance(action, dict):
            promotion_actions[action_id] = action
    return {
        "api_base": api_base.rstrip("/"),
        "service_profile": profile,
        "promotion_actions": promotion_actions,
    }


def request_json(api_base: str, method: str, path: str, *, timeout: int = 60) -> Any:
    request = urllib.request.Request(
        f"{api_base.rstrip('/')}{path}",
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"HTTP {error.code} from {path}: {detail}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Could not reach WILQ API at {api_base}: {error.reason}") from error


def live_public_review_actions(live_context: dict[str, Any] | None) -> dict[str, str]:
    return live_review_actions(live_context, review_type="public_service_cards")


def live_private_review_actions(live_context: dict[str, Any] | None) -> dict[str, str]:
    return live_review_actions(live_context, review_type="private_source_proposals")


def live_review_actions(
    live_context: dict[str, Any] | None,
    *,
    review_type: str,
) -> dict[str, str]:
    if live_context is None:
        return {}
    profile = live_context.get("service_profile")
    if not isinstance(profile, dict):
        return {}
    expected_scopes = review_scopes_for_type(review_type)
    actions: dict[str, str] = {}
    for action in raw_list(profile.get("review_actions")):
        if not isinstance(action, dict):
            continue
        action_id = str(action.get("action_id") or "").strip()
        review_scope = str(action.get("review_scope") or "").strip()
        target_card_id = str(action.get("target_card_id") or "").strip()
        if review_scope in expected_scopes and action_id and target_card_id:
            actions[action_id] = target_card_id
    return actions


def live_required_review_fields(
    live_context: dict[str, Any] | None,
    *,
    review_type: str,
) -> dict[str, tuple[dict[str, Any], ...]]:
    if live_context is None:
        return {}
    profile = live_context.get("service_profile")
    if not isinstance(profile, dict):
        return {}
    expected_scopes = review_scopes_for_type(review_type)
    fields_by_action: dict[str, tuple[dict[str, Any], ...]] = {}
    for action in raw_list(profile.get("review_actions")):
        if not isinstance(action, dict):
            continue
        action_id = str(action.get("action_id") or "").strip()
        review_scope = str(action.get("review_scope") or "").strip()
        if review_scope not in expected_scopes or not action_id:
            continue
        required_fields: list[dict[str, Any]] = []
        for requirement in raw_list(action.get("review_requirements")):
            if not isinstance(requirement, dict) or requirement.get("required") is not True:
                continue
            field = str(requirement.get("field") or "").strip()
            if not field:
                continue
            required_fields.append(
                {
                    "field": field,
                    "label": str(requirement.get("label") or field).strip(),
                    "requirement_type": str(
                        requirement.get("requirement_type") or "text"
                    ).strip(),
                }
            )
        fields_by_action[action_id] = tuple(required_fields)
    return fields_by_action


def review_scopes_for_type(review_type: str) -> set[str]:
    if review_type == "private_source_proposals":
        return PRIVATE_SOURCE_REVIEW_SCOPES
    return PUBLIC_SERVICE_REVIEW_SCOPES


def validate_live_required_fields(
    raw_decision: dict[str, Any],
    *,
    required_fields: tuple[dict[str, Any], ...],
    index: int,
) -> list[str]:
    errors: list[str] = []
    for requirement in required_fields:
        field = str(requirement.get("field") or "").strip()
        if not field:
            continue
        label = str(requirement.get("label") or field).strip()
        requirement_type = str(requirement.get("requirement_type") or "text").strip()
        if requirement_type == "boolean":
            if normalize_bool(raw_decision.get(field)) is None:
                errors.append(
                    f"Decyzja #{index}: wymagane przez live Service Profile pole "
                    f"{field} ({label}) musi mieć wartość tak albo nie"
                )
            continue
        if is_blank_or_placeholder(raw_decision.get(field)):
            errors.append(
                f"Decyzja #{index}: wymagane przez live Service Profile pole "
                f"{field} ({label}) jest puste"
            )
    return errors


def live_service_card_ids(live_context: dict[str, Any] | None) -> set[str]:
    return live_target_card_ids(live_context, review_type="public_service_cards")


def live_private_target_card_ids(live_context: dict[str, Any] | None) -> set[str]:
    return live_target_card_ids(live_context, review_type="private_source_proposals")


def live_target_card_ids(
    live_context: dict[str, Any] | None,
    *,
    review_type: str,
) -> set[str]:
    if live_context is None:
        return set()
    profile = live_context.get("service_profile")
    if not isinstance(profile, dict):
        return set()
    if review_type == "private_source_proposals":
        return {
            str(proposal.get("target_card_id") or "").strip()
            for proposal in raw_list(profile.get("private_source_proposals"))
            if isinstance(proposal, dict) and proposal.get("target_card_id")
        }
    return {
        str(section.get("card_id") or "").strip()
        for section in raw_list(profile.get("service_sections"))
        if isinstance(section, dict) and section.get("card_id")
    }


def live_promotion_preview_actions(
    live_context: dict[str, Any] | None,
    *,
    review_type: str,
) -> dict[str, str]:
    if live_context is None:
        return {}
    promotion_actions = live_context.get("promotion_actions")
    if not isinstance(promotion_actions, dict):
        return {}
    action_id = PROMOTION_ACTION_IDS.get(review_type)
    action = promotion_actions.get(action_id)
    if not isinstance(action, dict):
        return {}
    payload = action.get("payload")
    if not isinstance(payload, dict):
        return {}
    preview_by_review_action: dict[str, str] = {}
    for item in raw_list(payload.get("payload_preview")):
        if not isinstance(item, dict):
            continue
        review_action_id = str(item.get("review_action_id") or "").strip()
        target_card_id = str(item.get("target_card_id") or "").strip()
        if review_action_id and target_card_id:
            preview_by_review_action[review_action_id] = target_card_id
    return preview_by_review_action


def live_review_provenance(
    *,
    live_context: dict[str, Any] | None,
    decisions: list[dict[str, Any]],
    review_type: str = DEFAULT_REVIEW_TYPE,
) -> dict[str, Any] | None:
    if live_context is None:
        return None
    profile = live_context.get("service_profile")
    if not isinstance(profile, dict):
        return None
    raw_coverage = profile.get("coverage_summary")
    coverage: dict[str, Any] = raw_coverage if isinstance(raw_coverage, dict) else {}
    live_actions = live_review_actions(live_context, review_type=review_type)
    live_required_fields = live_required_review_fields(
        live_context,
        review_type=review_type,
    )
    live_promotion_preview = live_promotion_preview_actions(
        live_context,
        review_type=review_type,
    )
    if review_type == "private_source_proposals":
        private_proposal_provenance = live_private_proposal_provenance(
            profile,
            decisions=decisions,
        )
        raw_private_summary = profile.get("private_source_proposal_summary")
        private_summary: dict[str, Any] = (
            raw_private_summary if isinstance(raw_private_summary, dict) else {}
        )
        return {
            "api_base": live_context.get("api_base"),
            "service_profile_read_only": profile.get("read_only"),
            "production_depth_ready": coverage.get("ready_for_daily_content"),
            "live_private_review_action_count": len(live_actions),
            "live_private_promotion_preview_count": len(live_promotion_preview),
            "reviewed_action_count": len(decisions),
            "reviewed_action_ids": [decision["action_id"] for decision in decisions],
            "reviewed_target_card_ids": [decision["target_card_id"] for decision in decisions],
            "reviewed_required_review_fields": {
                decision["action_id"]: [
                    requirement["field"]
                    for requirement in live_required_fields.get(decision["action_id"], ())
                ]
                for decision in decisions
            },
            "private_proposal_promotion_ready": private_summary.get("promotion_ready"),
            "reviewed_private_proposal_provenance": private_proposal_provenance,
        }
    return {
        "api_base": live_context.get("api_base"),
        "service_profile_read_only": profile.get("read_only"),
        "production_depth_ready": coverage.get("ready_for_daily_content"),
        "live_public_review_action_count": len(live_actions),
        "live_public_promotion_preview_count": len(live_promotion_preview),
        "reviewed_action_count": len(decisions),
        "reviewed_action_ids": [decision["action_id"] for decision in decisions],
        "reviewed_target_card_ids": [decision["target_card_id"] for decision in decisions],
        "reviewed_required_review_fields": {
            decision["action_id"]: [
                requirement["field"]
                for requirement in live_required_fields.get(decision["action_id"], ())
            ]
            for decision in decisions
        },
    }


def live_private_proposal_provenance(
    profile: dict[str, Any],
    *,
    decisions: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    proposals_by_target = {
        str(proposal.get("target_card_id") or "").strip(): proposal
        for proposal in raw_list(profile.get("private_source_proposals"))
        if isinstance(proposal, dict) and proposal.get("target_card_id")
    }
    provenance: dict[str, dict[str, Any]] = {}
    for decision in decisions:
        target_card_id = str(decision.get("target_card_id") or "").strip()
        proposal = proposals_by_target.get(target_card_id)
        if proposal is None:
            continue
        provenance[target_card_id] = {
            "proposal_id": proposal.get("proposal_id"),
            "source_id": proposal.get("source_id"),
            "freshness_status": proposal.get("freshness_status"),
            "audience": proposal.get("audience"),
            "retention_decision": proposal.get("retention_decision"),
            "risk_tier": proposal.get("risk_tier"),
            "support_level": proposal.get("support_level"),
            "promotion_allowed": proposal.get("promotion_allowed"),
            "redacted": proposal.get("redacted"),
        }
    return provenance


def live_service_section_by_card_id(
    live_context: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    profile = live_context.get("service_profile")
    if not isinstance(profile, dict):
        return {}
    return {
        str(section.get("card_id") or "").strip(): section
        for section in raw_list(profile.get("service_sections"))
        if isinstance(section, dict) and section.get("card_id")
    }


def live_private_proposals_by_target(
    live_context: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    profile = live_context.get("service_profile")
    if not isinstance(profile, dict):
        return {}
    return {
        str(proposal.get("target_card_id") or "").strip(): proposal
        for proposal in raw_list(profile.get("private_source_proposals"))
        if isinstance(proposal, dict) and proposal.get("target_card_id")
    }


def source_fact_by_id() -> dict[str, Any]:
    return {fact.source_id: fact for fact in ekologus_source_facts()}


def render_promotion_readiness_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Service Profile promotion readiness",
        "",
        f"- Typ: `{report['report_type']}`",
        f"- Review type: `{report['review_type']}`",
        f"- Review ready: {visible_bool(report['review_ready'])}",
        f"- Promotion request ready: {visible_bool(report['promotion_request_ready'])}",
        f"- Promotion allowed: {visible_bool(report['promotion_allowed'])}",
        f"- Mutation allowed: {visible_bool(report['mutation_allowed'])}",
        f"- Production-depth unlocked: {visible_bool(report['production_depth_unlocked'])}",
        f"- Raw private text included: {visible_bool(report['raw_private_text_included'])}",
        "",
        report["safety_note"],
        "",
        "## Blokery",
        "",
    ]
    for blocker in report["promotion_blockers"] or ["brak"]:
        lines.append(f"- `{blocker}`")
    lines.extend(["", "## Preview", ""])
    for row in report["promotion_request_preview"]:
        lines.extend(
            [
                f"### `{row['target_card_id']}`",
                "",
                f"- action_id: `{row['action_id']}`",
                f"- promotion_ready: {visible_bool(row['promotion_ready'])}",
                f"- source facts: {', '.join(row['source_fact_ids']) or 'brak'}",
                f"- evidence IDs: {', '.join(row['evidence_ids']) or 'brak'}",
                f"- source connectors: {', '.join(row['source_connectors']) or 'brak'}",
                f"- blocked claims: {', '.join(row['blocked_claims']) or 'brak'}",
                f"- freshness: `{row['freshness']}`",
                f"- confidence: `{row['confidence']}`",
                "- blokery: "
                + (
                    ", ".join(f"`{blocker}`" for blocker in row["promotion_blockers"])
                    or "brak"
                ),
                "",
            ]
        )
    lines.extend(["## Następny krok", "", report["safe_next_step"]])
    return "\n".join(lines).rstrip() + "\n"


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Wynik Service Profile review",
        "",
        f"- Typ: `{report['report_type']}`",
        f"- Data: `{report['date']}`",
        f"- Reviewer: `{report['reviewer']}`",
        f"- Zakres: {report['scope_label']}",
        f"- Status: {visible_status(report['overall_status'])}",
        f"- Decyzje: `{report['decision_count']}`",
        f"- Zatwierdzone w review: `{report['approved_decision_count']}`",
        f"- Blokujące: `{report['blocking_decision_count']}`",
        f"- Promotion allowed: {visible_bool(report['promotion_allowed'])}",
        "",
        report["safety_note"],
        "",
        "## Live provenance",
        "",
        render_live_provenance(report.get("live_provenance")),
        "",
        "## Decyzje",
        "",
    ]
    for decision in report["decisions"]:
        lines.extend(
            [
                f"### `{decision['target_card_id']}`",
                "",
                f"- action_id: `{decision['action_id']}`",
                f"- decyzja: `{decision['decision']}`",
                f"- ślad źródłowy czytelny: {visible_bool(decision['source_trace_clear'])}",
                "- claimy zablokowane sprawdzone: "
                f"{visible_bool(decision['blocked_claims_reviewed'])}",
            ]
        )
        for field in PRIVATE_DECISION_BOOLEAN_FIELDS:
            if field in decision:
                lines.append(f"- {field}: {visible_bool(decision[field])}")
        lines.append(f"- notatki: {decision['notes']}")
        for task in decision["follow_up_beads"]:
            lines.append(f"- follow-up: {task}")
        lines.append("")
    lines.extend(["## Follow-up", ""])
    for task in report["follow_up_tasks"] or ["brak"]:
        lines.append(f"- {task}")
    lines.extend(["", "## Następny krok", "", report["safe_next_step"]])
    return "\n".join(lines).rstrip() + "\n"


def render_live_provenance(value: Any) -> str:
    if not isinstance(value, dict):
        return "- Nie sprawdzono live Service Profile."
    lines = [
        f"- API: `{value.get('api_base')}`",
        "- Service Profile read-only: "
        f"{visible_bool(value.get('service_profile_read_only') is True)}",
        "- Production-depth ready: "
        f"{visible_bool(value.get('production_depth_ready') is True)}",
    ]
    if "live_private_review_action_count" in value:
        lines.extend(
            [
                "- Private review actions live: "
                f"`{value.get('live_private_review_action_count')}`",
                "- Private promotion preview rows live: "
                f"`{value.get('live_private_promotion_preview_count')}`",
                "- Private proposal promotion ready: "
                f"{visible_bool(value.get('private_proposal_promotion_ready') is True)}",
            ]
        )
    else:
        lines.append(
            "- Public review actions live: "
            f"`{value.get('live_public_review_action_count')}`"
        )
        lines.append(
            "- Public promotion preview rows live: "
            f"`{value.get('live_public_promotion_preview_count')}`"
        )
    lines.append(f"- Review actions w wyniku: `{value.get('reviewed_action_count')}`")
    required_fields = value.get("reviewed_required_review_fields")
    if isinstance(required_fields, dict) and required_fields:
        lines.append("- Wymagane pola review z live Service Profile:")
        for action_id, fields in required_fields.items():
            rendered_fields = ", ".join(str(field) for field in fields) or "brak"
            lines.append(f"  - `{action_id}`: {rendered_fields}")
    private_proposals = value.get("reviewed_private_proposal_provenance")
    if isinstance(private_proposals, dict) and private_proposals:
        lines.append("- Private proposal provenance z live Service Profile:")
        for target_card_id, proposal in private_proposals.items():
            if not isinstance(proposal, dict):
                continue
            lines.append(
                "  - "
                f"`{target_card_id}`: "
                f"freshness={proposal.get('freshness_status')}, "
                f"audience={proposal.get('audience')}, "
                f"retencja={proposal.get('retention_decision')}, "
                f"ryzyko={proposal.get('risk_tier')}, "
                f"support={proposal.get('support_level')}, "
                f"promotion_allowed={visible_bool(proposal.get('promotion_allowed') is True)}"
            )
    return "\n".join(lines)


def normalize_bool(value: Any) -> bool | None:
    lowered = str(value or "").strip().lower()
    if lowered == "tak":
        return True
    if lowered == "nie":
        return False
    return None


def visible_bool(value: Any) -> str:
    return "tak" if value is True else "nie"


def visible_status(value: Any) -> str:
    if value == "review_ready_for_promotion_request":
        return "review gotowy do osobnego promotion request"
    return "wymaga follow-up przed promotion request"


def list_payload(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if not is_blank_or_placeholder(item)]
    if is_blank_or_placeholder(value):
        return []
    return [str(value).strip()]


def raw_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def is_blank_or_placeholder(value: Any) -> bool:
    text = str(value or "").strip()
    return not text or text.startswith("<") or text in {"-", "TODO", "todo"}


if __name__ == "__main__":
    raise SystemExit(main())
