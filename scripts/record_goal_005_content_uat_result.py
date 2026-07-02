from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REQUIRED_TEXT_FIELDS = {
    "data_sesji": "data sesji",
    "osoba": "osoba",
    "czas_do_zrozumienia_statusu": "czas do zrozumienia statusu",
    "punkty_niezrozumienia": "punkty niezrozumienia",
    "wybrany_work_item": "wybrany work item",
    "pytania_skad_to_wzielo": 'pytania "skąd to wzięło?"',
    "miejsca_generyczne_off_brand": "miejsca generyczne/off-brand",
    "najwiekszy_brak_produktu": "największy brak produktu",
}

REQUIRED_BOOLEAN_FIELDS = {
    "wilku_rozumie_blokady_pelnego_uat": "czy Wilku rozumie blokady pełnego UAT",
    "service_profile_czytelny": "czy Service Profile jest czytelny",
    "public_service_review_actions_czytelne": (
        "czy public service review actions są czytelne"
    ),
    "private_review_actions_czytelne": "czy private review actions są czytelne",
    "private_policy_review_actions_czytelne": (
        "czy private policy review actions są czytelne"
    ),
    "mozna_przejsc_do_pelnego_content_uat": "czy można przejść do pełnego content UAT",
}
REVIEW_ARTIFACTS_FIELD = "pokazane_materialy_review"
REVIEW_ARTIFACTS_ROOT = Path("docs/handoffs")
RECOMMENDED_REVIEW_ARTIFACTS = [
    "docs/handoffs/2026-07-02-wilq-marketing-content-model.md",
    "docs/handoffs/2026-07-02-co-pokazac-wilkowi.md",
]
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Waliduje i renderuje wynik Goal 005 Wilku content UAT. "
            "Nie uruchamia UAT i nie zamyka goalu."
        )
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Ścieżka do wypełnionego JSON z wynikiem UAT",
    )
    parser.add_argument(
        "--print-input-example",
        action="store_true",
        help=(
            "Wypisuje fillable JSON do zapisania przed rozmową z Wilkiem. "
            "To nie jest wynik UAT i celowo zawiera placeholdery."
        ),
    )
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument(
        "--api-base",
        help=(
            "Opcjonalnie sprawdza wynik przeciw aktualnej kolejce i Service Profile "
            "z WILQ API."
        ),
    )
    args = parser.parse_args()

    try:
        live_context = load_live_uat_context(args.api_base) if args.api_base else None
        if args.print_input_example:
            print(
                json.dumps(
                    build_content_uat_input_example(live_context=live_context),
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        if not args.input:
            parser.error(
                "podaj ścieżkę input albo użyj --print-input-example, żeby wygenerować wzór"
            )
        payload = load_json(Path(args.input))
        report = build_content_uat_result_report(payload, live_context=live_context)
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(report))
    return 0


def build_content_uat_input_example(
    *,
    live_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    selected_work_item = "<work_item_id_z_uat_packet>"
    if live_context is not None:
        selected_work_item = select_uat_candidate_id(live_context) or selected_work_item
    return {
        "data_sesji": "<YYYY-MM-DD>",
        "osoba": "Wilku",
        "czas_do_zrozumienia_statusu": "UZUPEŁNIJ: np. 8 minut",
        "punkty_niezrozumienia": (
            "UZUPEŁNIJ: co było niejasne w statusie, blokadach albo kolejce"
        ),
        "wybrany_work_item": selected_work_item,
        REVIEW_ARTIFACTS_FIELD: RECOMMENDED_REVIEW_ARTIFACTS,
        "pytania_skad_to_wzielo": (
            'UZUPEŁNIJ: gdzie Wilku zapytał "skąd to wzięło?" albo "brak pytań"'
        ),
        "miejsca_generyczne_off_brand": (
            "UZUPEŁNIJ: co brzmiało generycznie/off-brand albo brak uwag"
        ),
        "najwiekszy_brak_produktu": (
            "UZUPEŁNIJ: największa luka przed pełnym content UAT"
        ),
        "wilku_rozumie_blokady_pelnego_uat": "nie",
        "service_profile_czytelny": "nie",
        "public_service_review_actions_czytelne": "nie",
        "private_review_actions_czytelne": "nie",
        "private_policy_review_actions_czytelne": "nie",
        "mozna_przejsc_do_pelnego_content_uat": "nie",
        "follow_up_beads": [
            "<wilq-seo-...: opisz follow-up po sesji, jeżeli pełny UAT jest zablokowany>"
        ],
    }


def load_json(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as error:
        raise RuntimeError(f"Could not read {path}: {error}") from error
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"{path} is not valid JSON") from error
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} must contain a JSON object")
    return payload


def build_content_uat_result_report(
    payload: dict[str, Any],
    *,
    live_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    errors = validate_content_uat_payload(payload, live_context=live_context)
    if errors:
        raise RuntimeError("Niepoprawny wynik Goal 005 content UAT:\n- " + "\n- ".join(errors))

    can_continue = normalize_bool(payload["mozna_przejsc_do_pelnego_content_uat"])
    blockers_understood = normalize_bool(payload["wilku_rozumie_blokady_pelnego_uat"])
    service_profile_clear = normalize_bool(payload["service_profile_czytelny"])
    public_actions_clear = normalize_bool(
        payload["public_service_review_actions_czytelne"]
    )
    private_actions_clear = normalize_bool(payload["private_review_actions_czytelne"])
    private_policy_actions_clear = normalize_bool(
        payload["private_policy_review_actions_czytelne"]
    )
    follow_up_tasks = list_payload(payload.get("follow_up_beads"))
    shown_review_artifacts = review_artifact_paths(payload.get(REVIEW_ARTIFACTS_FIELD))
    missing_recommended_review_artifacts = recommended_review_artifact_gaps(
        shown_review_artifacts
    )
    missing_follow_up = not can_continue and not follow_up_tasks
    selected_work_item = str(payload["wybrany_work_item"]).strip()
    live_provenance = live_uat_provenance(
        live_context=live_context,
        selected_work_item=selected_work_item,
    )

    ready_for_full_content_uat = (
        can_continue
        and blockers_understood
        and service_profile_clear
        and public_actions_clear
        and private_actions_clear
        and private_policy_actions_clear
    )

    return {
        "report_type": "goal_005_content_uat_result_v1",
        "date": str(payload["data_sesji"]).strip(),
        "person": str(payload["osoba"]).strip(),
        "selected_work_item": selected_work_item,
        "time_to_status_understanding": str(
            payload["czas_do_zrozumienia_statusu"]
        ).strip(),
        "confusion_points": str(payload["punkty_niezrozumienia"]).strip(),
        "blockers_understood": blockers_understood,
        "service_profile_clear": service_profile_clear,
        "public_service_review_actions_clear": public_actions_clear,
        "private_review_actions_clear": private_actions_clear,
        "private_policy_review_actions_clear": private_policy_actions_clear,
        "source_trace_questions": str(payload["pytania_skad_to_wzielo"]).strip(),
        "generic_or_off_brand_findings": str(
            payload["miejsca_generyczne_off_brand"]
        ).strip(),
        "largest_product_gap": str(payload["najwiekszy_brak_produktu"]).strip(),
        "can_continue_to_full_content_uat": can_continue,
        "shown_review_artifacts": shown_review_artifacts,
        "missing_recommended_review_artifacts": missing_recommended_review_artifacts,
        "follow_up_tasks": follow_up_tasks,
        "live_provenance": live_provenance,
        "overall_status": (
            "ready_for_full_content_uat"
            if ready_for_full_content_uat
            else "needs_follow_up_before_full_content_uat"
        ),
        "missing_follow_up_task": missing_follow_up,
        "safety_note": (
            "Ten raport zapisuje wynik Goal 005 content UAT. Nie promuje private "
            "proposals do source facts, nie zatwierdza publicznych service cards "
            "i nie odblokowuje publikacji, WordPress write ani success claims."
        ),
    }


def validate_content_uat_payload(
    payload: dict[str, Any],
    *,
    live_context: dict[str, Any] | None = None,
) -> list[str]:
    errors: list[str] = []
    for key, label in REQUIRED_TEXT_FIELDS.items():
        if is_blank_or_placeholder(payload.get(key)):
            errors.append(f"Brak pola albo placeholder: {label}")
    for key, label in REQUIRED_BOOLEAN_FIELDS.items():
        if normalize_bool(payload.get(key)) is None:
            errors.append(f"{label} musi mieć wartość tak albo nie")
    if not list_payload(payload.get("follow_up_beads")) and normalize_bool(
        payload.get("mozna_przejsc_do_pelnego_content_uat")
    ) is False:
        errors.append("Gdy pełny content UAT jest zablokowany, wpisz follow_up_beads")
    errors.extend(validate_review_artifacts(payload.get(REVIEW_ARTIFACTS_FIELD)))
    if live_context is not None:
        selected_work_item = str(payload.get("wybrany_work_item") or "").strip()
        candidate_ids = live_context_candidate_ids(live_context)
        if selected_work_item and selected_work_item not in candidate_ids:
            errors.append(
                "Wybrany work item nie występuje w aktualnym live UAT packet: "
                f"{selected_work_item}"
            )
    return errors


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Wynik Goal 005 content UAT",
        "",
        f"- Typ: `{report['report_type']}`",
        f"- Data: `{report['date']}`",
        f"- Osoba: `{report['person']}`",
        f"- Work item: `{report['selected_work_item']}`",
        f"- Status: {visible_status(report['overall_status'])}",
        f"- Czas do zrozumienia statusu: {report['time_to_status_understanding']}",
        f"- Punkty niezrozumienia: {report['confusion_points']}",
        "",
        report["safety_note"],
        "",
        "## Live provenance",
        "",
        render_live_provenance(report.get("live_provenance")),
        "",
        "## Ocena",
        "",
        f"- Rozumie blokady pełnego UAT: {visible_bool(report['blockers_understood'])}",
        f"- Service Profile czytelny: {visible_bool(report['service_profile_clear'])}",
        "- Public service review actions czytelne: "
        f"{visible_bool(report['public_service_review_actions_clear'])}",
        "- Private review actions czytelne: "
        f"{visible_bool(report['private_review_actions_clear'])}",
        "- Private policy review actions czytelne: "
        f"{visible_bool(report['private_policy_review_actions_clear'])}",
        "- Można przejść do pełnego content UAT: "
        f"{visible_bool(report['can_continue_to_full_content_uat'])}",
        "",
        "## Pokazane materiały review",
        "",
        *[f"- `{artifact}`" for artifact in report["shown_review_artifacts"]],
        "",
        *render_missing_recommended_review_artifacts(report),
        "## Źródła i jakość",
        "",
        f"- Pytania \"skąd to wzięło?\": {report['source_trace_questions']}",
        f"- Generyczne/off-brand: {report['generic_or_off_brand_findings']}",
        f"- Największy brak produktu: {report['largest_product_gap']}",
        "",
        "## Follow-up",
        "",
    ]
    for task in report["follow_up_tasks"] or ["brak"]:
        lines.append(f"- {task}")
    return "\n".join(lines).rstrip() + "\n"


def render_missing_recommended_review_artifacts(report: dict[str, Any]) -> list[str]:
    missing = report.get("missing_recommended_review_artifacts") or []
    if not missing:
        return []
    return [
        "## Ostrzeżenia materiałów review",
        "",
        *[
            f"- Nie pokazano rekomendowanego prostego przewodnika: `{artifact}`"
            for artifact in missing
        ],
        "",
    ]


def load_live_uat_context(api_base: str) -> dict[str, Any]:
    health = request_json(api_base, "GET", "/api/health")
    if not isinstance(health, dict) or health.get("status") != "ok":
        raise RuntimeError(f"WILQ API health is not ok at {api_base}")
    queue = request_json(api_base, "GET", "/api/content/work-items/queue")
    service_profile = request_json(api_base, "GET", "/api/content/service-profile")
    if not isinstance(queue, dict):
        raise RuntimeError("Live content work-item queue must be an object")
    if not isinstance(service_profile, dict):
        raise RuntimeError("Live Service Profile must be an object")
    return {
        "api_base": api_base.rstrip("/"),
        "queue": queue,
        "service_profile": service_profile,
        "sales_brief_traces": load_sales_brief_traces(api_base, queue),
    }


def load_sales_brief_traces(api_base: str, queue: dict[str, Any]) -> dict[str, Any]:
    traces: dict[str, Any] = {}
    for candidate in raw_list_payload(queue.get("candidates")):
        if not isinstance(candidate, dict):
            continue
        work_item_id = str(candidate.get("work_item_id") or "").strip()
        if not work_item_id:
            continue
        try:
            snapshot = request_json(
                api_base,
                "GET",
                f"/api/content/work-items/{work_item_id}/snapshot",
                timeout=120,
            )
        except RuntimeError as error:
            traces[work_item_id] = {
                "status": "unavailable",
                "blocker": str(error),
            }
            continue
        traces[work_item_id] = sales_brief_trace_from_snapshot(snapshot)
    return traces


def sales_brief_trace_from_snapshot(snapshot: Any) -> dict[str, Any]:
    if not isinstance(snapshot, dict):
        return {"status": "missing", "blocker": "snapshot nie jest obiektem"}
    sales_brief_stage = snapshot.get("sales_brief")
    if not isinstance(sales_brief_stage, dict):
        return {"status": "missing", "blocker": "snapshot nie zawiera sales_brief"}
    result = sales_brief_stage.get("sales_brief_result")
    if not isinstance(result, dict):
        return {
            "status": "missing",
            "blocker": "snapshot nie zawiera sales_brief_result",
        }
    brief = result.get("brief")
    blockers = result.get("blockers")
    if not isinstance(brief, dict):
        return {
            "status": "blocked",
            "blockers": blockers if isinstance(blockers, list) else [],
        }
    signal_quality = brief.get("signal_quality")
    constraints = [
        constraint
        for constraint in raw_list_payload(brief.get("knowledge_constraints"))
        if isinstance(constraint, dict)
    ]
    evidence_ids = sorted(
        {
            str(evidence_id)
            for constraint in constraints
            for evidence_id in raw_list_payload(constraint.get("evidence_ids"))
            if evidence_id
        }
    )
    return {
        "status": "ready",
        "signal_quality_status_label": (
            signal_quality.get("status_label")
            if isinstance(signal_quality, dict)
            else None
        ),
        "knowledge_constraint_count": len(constraints),
        "knowledge_constraint_evidence_ids": evidence_ids,
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


def live_context_candidate_ids(live_context: dict[str, Any]) -> set[str]:
    queue = live_context.get("queue")
    if not isinstance(queue, dict):
        return set()
    return {
        str(candidate.get("work_item_id") or "").strip()
        for candidate in raw_list_payload(queue.get("candidates"))
        if isinstance(candidate, dict) and candidate.get("work_item_id")
    }


def select_uat_candidate_id(live_context: dict[str, Any]) -> str | None:
    queue = live_context.get("queue")
    if not isinstance(queue, dict):
        return None
    candidates = [
        candidate
        for candidate in raw_list_payload(queue.get("candidates"))
        if isinstance(candidate, dict) and candidate.get("work_item_id")
    ]
    if not candidates:
        return None
    ranked = sorted(
        candidates,
        key=lambda candidate: (
            -uat_candidate_score(candidate, live_context),
            str(candidate.get("work_item_id") or ""),
        ),
    )
    return str(ranked[0].get("work_item_id") or "").strip() or None


def uat_candidate_score(candidate: dict[str, Any], live_context: dict[str, Any]) -> int:
    score = 0
    mode = str(candidate.get("recommended_mode") or "").strip()
    if mode in {"refresh", "merge", "refresh_or_merge"}:
        score += 50
    elif mode == "block":
        score -= 20
    if candidate.get("final_canonical_url") or candidate.get("intended_final_url"):
        score += 20
    if candidate.get("source_public_url"):
        score += 10
    if candidate.get("preflight_status") in {"plan_allowed", "ready"}:
        score += 10
    if candidate.get("source_connectors"):
        score += 5
    traces = live_context.get("sales_brief_traces")
    if isinstance(traces, dict):
        trace = traces.get(str(candidate.get("work_item_id") or ""))
        if isinstance(trace, dict):
            if trace.get("status") == "ready":
                score += 20
            elif trace.get("status") == "blocked":
                score += 5
    return score


def live_uat_provenance(
    *,
    live_context: dict[str, Any] | None,
    selected_work_item: str,
) -> dict[str, Any] | None:
    if live_context is None:
        return None
    raw_queue = live_context.get("queue")
    queue: dict[str, Any] = raw_queue if isinstance(raw_queue, dict) else {}
    raw_service_profile = live_context.get("service_profile")
    service_profile: dict[str, Any] = (
        raw_service_profile if isinstance(raw_service_profile, dict) else {}
    )
    candidates = [
        candidate
        for candidate in raw_list_payload(queue.get("candidates"))
        if isinstance(candidate, dict)
    ]
    selected = next(
        (
            candidate
            for candidate in candidates
            if str(candidate.get("work_item_id") or "") == selected_work_item
        ),
        {},
    )
    raw_coverage = service_profile.get("coverage_summary")
    coverage: dict[str, Any] = raw_coverage if isinstance(raw_coverage, dict) else {}
    raw_private_summary = service_profile.get("private_source_proposal_summary")
    private_summary: dict[str, Any] = (
        raw_private_summary if isinstance(raw_private_summary, dict) else {}
    )
    raw_sales_brief_traces = live_context.get("sales_brief_traces")
    sales_brief_traces: dict[str, Any] = (
        raw_sales_brief_traces if isinstance(raw_sales_brief_traces, dict) else {}
    )
    raw_selected_sales_brief_trace = sales_brief_traces.get(selected_work_item)
    selected_sales_brief_trace: dict[str, Any] = (
        raw_selected_sales_brief_trace
        if isinstance(raw_selected_sales_brief_trace, dict)
        else {}
    )
    review_actions = [
        action
        for action in raw_list_payload(service_profile.get("review_actions"))
        if isinstance(action, dict)
    ]
    return {
        "api_base": live_context.get("api_base"),
        "queue_status": queue.get("queue_status"),
        "candidate_count": queue.get("candidate_count"),
        "actionable_candidate_count": queue.get("actionable_candidate_count"),
        "selected_work_item_found": bool(selected),
        "selected_recommended_mode": selected.get("recommended_mode"),
        "selected_evidence_ids": selected.get("evidence_ids") or [],
        "selected_source_connectors": selected.get("source_connectors") or [],
        "selected_sales_brief_status": selected_sales_brief_trace.get("status"),
        "selected_sales_brief_blocker": selected_sales_brief_trace.get("blocker"),
        "selected_sales_brief_blockers": sales_brief_blocker_labels(
            selected_sales_brief_trace.get("blockers")
        ),
        "selected_sales_brief_constraint_count": selected_sales_brief_trace.get(
            "knowledge_constraint_count"
        ),
        "selected_sales_brief_constraint_evidence_ids": selected_sales_brief_trace.get(
            "knowledge_constraint_evidence_ids"
        )
        or [],
        "service_profile_read_only": service_profile.get("read_only"),
        "production_depth_ready": coverage.get("ready_for_daily_content"),
        "public_service_review_action_count": len(
            [
                action
                for action in review_actions
                if review_scope(action) in PUBLIC_SERVICE_REVIEW_SCOPES
            ]
        ),
        "private_review_action_count": len(
            [
                action
                for action in review_actions
                if review_scope(action) in PRIVATE_SOURCE_REVIEW_SCOPES
            ]
        ),
        "private_service_review_action_count": len(
            [
                action
                for action in review_actions
                if review_scope(action) in PRIVATE_SERVICE_REVIEW_SCOPES
            ]
        ),
        "private_policy_review_action_count": len(
            [
                action
                for action in review_actions
                if review_scope(action) in PRIVATE_POLICY_REVIEW_SCOPES
            ]
        ),
        "private_proposal_promotion_ready": private_summary.get("promotion_ready"),
    }


def review_scope(action: dict[str, Any]) -> str:
    return str(action.get("review_scope") or "").strip()


def render_live_provenance(value: Any) -> str:
    if not isinstance(value, dict):
        return "- Nie sprawdzono live WILQ API dla tego wyniku."
    return "\n".join(
        [
            f"- API: `{value.get('api_base')}`",
            "- Kolejka: "
            f"`{value.get('queue_status')}`, kandydaci: `{value.get('candidate_count')}`",
            "- Wybrany work item znaleziony w live packet: "
            f"{visible_bool(value.get('selected_work_item_found') is True)}",
            f"- Tryb wybranego itemu: `{value.get('selected_recommended_mode')}`",
            "- Źródła wybranego itemu: "
            f"{', '.join(value.get('selected_source_connectors') or []) or 'brak'}",
            "- Sales Brief wybranego itemu: "
            f"`{value.get('selected_sales_brief_status') or 'brak'}`",
            "- Sales Brief blocker: "
            f"{sales_brief_blocker_label(value)}",
            "- Sales Brief constraint evidence: "
            f"{sales_brief_evidence_label(value)}",
            "- Service Profile read-only: "
            f"{visible_bool(value.get('service_profile_read_only') is True)}",
            "- Production-depth ready: "
            f"{visible_bool(value.get('production_depth_ready') is True)}",
            "- Public service review actions: "
            f"`{value.get('public_service_review_action_count')}`",
            "- Private review actions: "
            f"`{value.get('private_review_action_count')}`",
            "- Private service review actions: "
            f"`{value.get('private_service_review_action_count')}`",
            "- Private policy review actions: "
            f"`{value.get('private_policy_review_action_count')}`",
            "- Private proposal promotion ready: "
            f"{visible_bool(value.get('private_proposal_promotion_ready') is True)}",
        ]
    )


def sales_brief_blocker_label(value: dict[str, Any]) -> str:
    blocker = value.get("selected_sales_brief_blocker")
    if blocker:
        return str(blocker)
    blockers = sales_brief_blocker_labels(value.get("selected_sales_brief_blockers"))
    return "; ".join(blockers) or "brak"


def sales_brief_evidence_label(value: dict[str, Any]) -> str:
    evidence_ids = value.get("selected_sales_brief_constraint_evidence_ids") or []
    return ", ".join(evidence_ids) or "brak"


def sales_brief_blocker_labels(value: Any) -> list[str]:
    labels: list[str] = []
    for item in raw_list_payload(value):
        if isinstance(item, dict):
            labels.append(str(item.get("label") or item.get("reason") or item.get("code")))
        elif item:
            labels.append(str(item))
    return [label for label in labels if label and label != "None"]


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
    if value == "ready_for_full_content_uat":
        return "gotowe do pełnego content UAT"
    return "wymaga follow-up przed pełnym content UAT"


def list_payload(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if not is_blank_or_placeholder(item)]
    if is_blank_or_placeholder(value):
        return []
    return [str(value).strip()]


def review_artifact_paths(value: Any) -> list[str]:
    return list_payload(value)


def validate_review_artifacts(value: Any) -> list[str]:
    artifacts = review_artifact_paths(value)
    if not artifacts:
        return ["Brak pokazanych materiałów review w polu pokazane_materialy_review"]
    errors: list[str] = []
    for artifact in artifacts:
        path = Path(artifact)
        if path.is_absolute() or ".." in path.parts:
            errors.append(f"Materiał review musi być ścieżką repo-relative: {artifact}")
            continue
        if REVIEW_ARTIFACTS_ROOT not in [path, *path.parents]:
            errors.append(f"Materiał review musi pochodzić z docs/handoffs: {artifact}")
            continue
        if not path.is_file():
            errors.append(f"Materiał review nie istnieje: {artifact}")
    return errors


def recommended_review_artifact_gaps(shown_review_artifacts: list[str]) -> list[str]:
    shown = set(shown_review_artifacts)
    return [
        artifact
        for artifact in RECOMMENDED_REVIEW_ARTIFACTS
        if artifact not in shown
    ]


def raw_list_payload(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def is_blank_or_placeholder(value: Any) -> bool:
    text = str(value or "").strip()
    lowered = text.lower()
    return (
        not text
        or text.startswith("<")
        or text in {"-", "TODO", "todo"}
        or lowered.startswith("todo:")
        or lowered.startswith("uzupełnij:")
        or lowered.startswith("uzupelnij:")
    )


if __name__ == "__main__":
    raise SystemExit(main())
