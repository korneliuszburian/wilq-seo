from __future__ import annotations

import argparse
import json
from collections import Counter
from typing import Any

from wilq.content.knowledge.service_profile import content_service_profile_response
from wilq.content.knowledge.source_facts import ekologus_source_fact_registry

SCOPE_LABELS = {
    "public_service_card": "publiczna karta usługi",
    "private_claim_policy_proposal": "prywatna propozycja polityki twierdzeń",
    "private_evidence_policy_proposal": "prywatna propozycja wymagań dowodowych",
    "private_service_proposal": "prywatna propozycja usługi",
    "claim_policy": "polityka twierdzeń",
    "evidence_requirement": "wymaganie dowodowe",
    "service": "usługa",
    "general_knowledge_review": "ogólna ocena wiedzy",
}
RISK_LABELS = {
    "high": "wysokie",
    "medium": "średnie",
    "low": "niskie",
}
DECISION_LABELS = {
    "approve": "zatwierdź",
    "needs_changes": "wróć z poprawkami",
    "stale": "oznacz jako nieaktualne",
    "reject": "odrzuć",
}
KNOWLEDGE_STATUS_LABELS = {
    "seeded_contract_proof": "tylko techniczny seed/proof kontraktu",
    "source_backed_review_required": "źródła są, wymagają oceny",
    "approved_current": "zatwierdzona aktualna wiedza",
    "stale": "wiedza wymaga odświeżenia",
    "rejected": "odrzucone, nie używać w treści",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit WILQ source facts and Service Profile coverage for Goal 005. "
            "Reports review backlog and production-depth readiness without "
            "promoting any knowledge."
        )
    )
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args()

    report = build_report()
    if args.format == "markdown":
        print(render_markdown(report))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["pass"] else 1


def build_report() -> dict[str, Any]:
    fact_registry = ekologus_source_fact_registry()
    profile = content_service_profile_response()
    facts = list(fact_registry.facts)
    private_proposals = list(profile.private_source_proposals)
    service_sections = list(profile.service_sections)
    review_actions = list(profile.review_actions)

    fact_review_counts = Counter(fact.review_status for fact in facts)
    fact_scope_counts = Counter(fact.scope for fact in facts)
    fact_connector_counts = Counter(
        connector for fact in facts for connector in fact.source_connectors
    )
    approved_service_count = sum(
        1 for section in service_sections if section.status == "approved_current"
    )
    production_depth_percent = _percent(
        profile.production_depth_readiness.production_depth_card_count,
        max(profile.coverage_summary.service_card_count, 1),
    )
    approved_service_percent = _percent(
        approved_service_count,
        max(len(service_sections), 1),
    )
    reviewed_fact_percent = _percent(
        fact_review_counts["approved"],
        max(len(facts), 1),
    )
    private_review_queue = [_private_review_item(proposal) for proposal in private_proposals]
    private_review_queue.sort(
        key=lambda item: (
            _risk_order(item["risk_tier"]),
            _scope_order(item["scope"]),
            item["target_card_title"],
        )
    )
    private_review_value = _private_review_value_summary(
        facts=facts,
        private_review_queue=private_review_queue,
    )
    title_by_card_id = _target_title_lookup(service_sections, private_proposals)
    review_action_queue = [
        _review_action_item(action, title_by_card_id=title_by_card_id)
        for action in review_actions
    ]
    review_action_queue.sort(
        key=lambda item: (
            _priority_order(item["priority"]),
            _scope_order(item["review_scope"]),
            item["target_card_title"],
            item["action_id"],
        )
    )
    review_action_queue = _pin_first_review_action(
        review_action_queue,
        first_review_action_id=profile.review_action_summary.first_review_action_id,
    )
    blockers = list(profile.production_depth_readiness.blocker_labels)
    blockers.extend(gap.reason for gap in profile.coverage_gaps)

    pass_state = bool(facts) and bool(profile.review_actions) and not any(
        proposal["promotion_allowed"] for proposal in private_review_queue
    )

    return {
        "workspace_id": profile.workspace_id,
        "generated_at": profile.generated_at,
        "pass": pass_state,
        "knowledge_status": profile.production_depth_readiness.status,
        "ready_for_daily_content": profile.production_depth_readiness.ready_for_daily_content,
        "production_depth_percent": production_depth_percent,
        "approved_service_percent": approved_service_percent,
        "reviewed_fact_percent": reviewed_fact_percent,
        "fact_count": len(facts),
        "fact_review_counts": dict(sorted(fact_review_counts.items())),
        "fact_scope_counts": dict(sorted(fact_scope_counts.items())),
        "fact_connector_counts": dict(sorted(fact_connector_counts.items())),
        "service_card_count": profile.coverage_summary.service_card_count,
        "coverage_gap_count": len(profile.coverage_gaps),
        "review_action_count": profile.review_action_summary.total_count,
        "first_review_action_id": profile.review_action_summary.first_review_action_id,
        "first_review_action_label": profile.review_action_summary.first_review_action_label,
        "private_proposal_count": len(private_proposals),
        "private_review_required_count": (
            profile.private_source_proposal_summary.review_required_count
        ),
        "private_review_value": private_review_value,
        "private_review_queue": private_review_queue,
        "review_action_queue": review_action_queue,
        "blockers": blockers,
        "safe_next_step": profile.coverage_summary.safe_next_step,
    }


def render_markdown(report: dict[str, Any]) -> str:
    ready = report["ready_for_daily_content"] is True
    verdict = (
        "WILQ ma wiedzę zatwierdzoną do użycia w finalnych treściach."
        if ready
        else (
            "WILQ ma materiał do oceny, ale nie ma jeszcze wiedzy zatwierdzonej "
            "do gotowych treści."
        )
    )
    lines = [
        "# Audyt faktów źródłowych WILQ",
        "",
        verdict,
        "",
        f"- Workspace: `{report['workspace_id']}`",
        f"- Stan wiedzy: {_knowledge_status_label(report['knowledge_status'])}",
        f"- Gotowe do codziennych treści: {_ready_label(ready)}",
        f"- Wiedza usług zatwierdzona do finalnych treści: {report['production_depth_percent']}%",
        f"- Zatwierdzone karty usług: {report['approved_service_percent']}%",
        f"- Zatwierdzone fakty źródłowe: {report['reviewed_fact_percent']}%",
        f"- Fakty źródłowe w rejestrze: {report['fact_count']}",
        f"- Decyzje do oceny: {report['review_action_count']}",
        f"- Prywatne propozycje wymagające oceny: {report['private_review_required_count']}",
        "",
        "## Co pokazać Wilkowi",
        "",
        _operator_text(report["safe_next_step"]),
        _first_review_action_line(report),
        "",
        "## Co wnosi prywatna wiedza",
        "",
        _operator_text(report["private_review_value"]["value_summary"]),
        "",
        "| Sygnał | Liczba |",
        "| --- | ---: |",
        "| Propozycje do oceny | "
        f"{report['private_review_value']['proposal_count']} |",
        "| Zablokowane twierdzenia opisane | "
        f"{report['private_review_value']['blocked_claim_proposal_count']} |",
        "| CTA do oceny | "
        f"{report['private_review_value']['cta_pattern_proposal_count']} |",
        "| Triggery/problem kupującego | "
        f"{report['private_review_value']['buyer_trigger_proposal_count']} |",
        "| Promocja bez oceny | "
        f"{report['private_review_value']['promotion_allowed_count']} |",
        "",
        "Najważniejsze punkty do oceny:",
        "",
        *[
            f"- {_operator_text(point)}"
            for point in report["private_review_value"]["review_value_points"]
        ],
        "",
        "Pytania do Wilka:",
        "",
        *[
            f"- {_operator_text(question)}"
            for question in report["private_review_value"].get("review_questions", [])
        ],
        "",
        "## Prywatne propozycje do oceny",
        "",
        "| Priorytet | Typ oceny | Temat | Ryzyko | Następny krok |",
        "| ---: | --- | --- | --- | --- |",
    ]
    for index, item in enumerate(report["private_review_queue"], start=1):
        lines.append(
            "| {index} | {scope} | {target} | {risk} | {next_step} |".format(
                index=index,
                scope=_scope_label(item["scope"]),
                target=_markdown_cell(_operator_text(item["target_card_title"])),
                risk=_risk_label(item["risk_tier"]),
                next_step=_markdown_cell(_operator_text(item["safe_next_step"])),
            )
        )
    review_actions = report.get("review_action_queue") or []
    if review_actions:
        lines.extend(
            [
                "",
                "## Konkretne decyzje do oceny",
                "",
                "| Priorytet | Typ oceny | Temat | Decyzje | Dowód |",
                "| ---: | --- | --- | --- | --- |",
            ]
        )
        for index, item in enumerate(review_actions[:8], start=1):
            lines.append(
                "| {index} | {scope} | {target} | {decisions} | `{action_id}` |".format(
                    index=index,
                    scope=_scope_label(item["review_scope"]),
                    action_id=item["action_id"],
                    target=_markdown_cell(_operator_text(item["target_card_title"])),
                    decisions=_markdown_cell(_decision_options_label(item["decision_options"])),
                )
            )
    if report["blockers"]:
        lines.extend(["", "## Blokery wiedzy do finalnych treści", ""])
        for blocker in report["blockers"]:
            lines.append(f"- {_operator_text(blocker)}")
    return "\n".join(lines)


def _private_review_item(proposal: Any) -> dict[str, Any]:
    return {
        "proposal_id": proposal.proposal_id,
        "source_id": proposal.source_id,
        "scope": proposal.scope,
        "target_card_id": proposal.target_card_id,
        "target_card_title": proposal.target_card_title,
        "risk_tier": proposal.risk_tier,
        "freshness_status": proposal.freshness_status,
        "audience": proposal.audience,
        "review_status": proposal.review_status,
        "promotion_allowed": proposal.promotion_allowed,
        "blocked_claim_count": len(proposal.blocked_claims),
        "safe_next_step": proposal.safe_next_step,
    }


def _first_review_action_line(report: dict[str, Any]) -> str:
    action_id = report.get("first_review_action_id")
    label = report.get("first_review_action_label")
    if not action_id and not label:
        return "Pierwsza decyzja do oceny: brak."
    if label and action_id:
        return f"Pierwsza decyzja do oceny: {label} (dowód: `{action_id}`)."
    return "Pierwsza decyzja do oceny: " + str(label or action_id)


def _scope_label(value: Any) -> str:
    raw = str(value or "")
    return SCOPE_LABELS.get(raw, raw or "brak")


def _risk_label(value: Any) -> str:
    raw = str(value or "")
    return RISK_LABELS.get(raw, raw or "brak")


def _decision_options_label(values: list[Any]) -> str:
    labels = [DECISION_LABELS.get(str(value), str(value)) for value in values]
    return ", ".join(labels) or "brak"


def _knowledge_status_label(value: Any) -> str:
    raw = str(value or "")
    return KNOWLEDGE_STATUS_LABELS.get(raw, raw or "brak")


def _ready_label(value: bool) -> str:
    return "tak" if value else "nie, najpierw ocena"


def _private_review_value_summary(
    *,
    facts: list[Any],
    private_review_queue: list[dict[str, Any]],
) -> dict[str, Any]:
    private_source_ids = {item["source_id"] for item in private_review_queue}
    private_facts = [fact for fact in facts if fact.source_id in private_source_ids]
    proposal_count = len(private_review_queue)
    blocked_claim_proposal_count = sum(
        1 for item in private_review_queue if item["blocked_claim_count"] > 0
    )
    cta_pattern_proposal_count = sum(1 for fact in private_facts if fact.cta_patterns)
    buyer_trigger_proposal_count = sum(
        1
        for fact in private_facts
        if fact.buyer_triggers or fact.buyer_problem_terms
    )
    promotion_allowed_count = sum(
        1 for item in private_review_queue if item["promotion_allowed"]
    )
    review_value_points: list[str] = []
    review_questions: list[str] = []
    if cta_pattern_proposal_count:
        review_value_points.append(
            "Prywatne propozycje dodają CTA lub kierunek rozmowy do oceny przez Wilka."
        )
        review_questions.append(
            "Czy proponowane CTA brzmi jak realny następny krok Ekologus, a nie obietnica wyniku?"
        )
    if buyer_trigger_proposal_count:
        review_value_points.append(
            "Prywatne propozycje doprecyzowują problemy i triggery kupującego."
        )
        review_questions.append(
            "Czy opisany problem kupującego faktycznie pasuje do rozmów z klientami Ekologus?"
        )
    if blocked_claim_proposal_count:
        review_value_points.append(
            "Każda propozycja niesie jawne zablokowane twierdzenia, więc może "
            "pomagać w Claim Ledgerze bez luzowania bezpieczeństwa."
        )
        review_questions.append(
            "Czy zablokowane twierdzenia są kompletne, szczególnie dla prawa, kar, zgodności i efektów?"
        )
    if promotion_allowed_count == 0 and proposal_count:
        review_value_points.append(
            "Żadna prywatna propozycja nie może wejść do wiedzy do finalnych "
            "treści bez oceny człowieka."
        )
        review_questions.append(
            "Które propozycje odrzucić, oznaczyć jako nieaktualne albo zostawić tylko jako tło do UAT?"
        )
    operator_value_score = 0
    if proposal_count:
        operator_value_score += 2
    if cta_pattern_proposal_count:
        operator_value_score += 2
    if buyer_trigger_proposal_count:
        operator_value_score += 2
    if blocked_claim_proposal_count == proposal_count and proposal_count:
        operator_value_score += 2
    if promotion_allowed_count == 0:
        operator_value_score += 1
    operator_value_score = min(operator_value_score, 9)
    return {
        "proposal_count": proposal_count,
        "promotion_allowed_count": promotion_allowed_count,
        "blocked_claim_proposal_count": blocked_claim_proposal_count,
        "cta_pattern_proposal_count": cta_pattern_proposal_count,
        "buyer_trigger_proposal_count": buyer_trigger_proposal_count,
        "operator_value_score": operator_value_score,
        "value_summary": (
            "Prywatne propozycje ekologus-ai dają materiał do oceny "
            "i mogą poprawić konkretność Service Profile, ale nie odblokowują "
            "finalnych treści, publikacji ani gotowych twierdzeń bez decyzji człowieka."
        ),
        "review_value_points": review_value_points,
        "review_questions": review_questions,
    }


def _review_action_item(
    action: Any,
    *,
    title_by_card_id: dict[str, str],
) -> dict[str, Any]:
    target_card_id = str(getattr(action, "target_card_id", "") or "")
    target_title = (
        str(getattr(action, "target_card_title", "") or "").strip()
        or title_by_card_id.get(target_card_id)
        or target_card_id
        or "ogólny przegląd wiedzy"
    )
    return {
        "action_id": getattr(action, "action_id", ""),
        "review_scope": getattr(action, "review_scope", ""),
        "priority": getattr(action, "priority", ""),
        "target_card_id": target_card_id,
        "target_card_title": target_title,
        "decision_options": list(getattr(action, "decision_options", []) or []),
    }


def _pin_first_review_action(
    review_action_queue: list[dict[str, Any]],
    *,
    first_review_action_id: str | None,
) -> list[dict[str, Any]]:
    if not first_review_action_id:
        return review_action_queue
    first_items = [
        item for item in review_action_queue if item["action_id"] == first_review_action_id
    ]
    if not first_items:
        return review_action_queue
    remaining = [
        item for item in review_action_queue if item["action_id"] != first_review_action_id
    ]
    return [first_items[0], *remaining]


def _target_title_lookup(
    service_sections: list[Any],
    private_proposals: list[Any],
) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for section in service_sections:
        card_id = str(getattr(section, "card_id", "") or "")
        title = str(getattr(section, "title", "") or "")
        if card_id and title:
            lookup[card_id] = title
    for proposal in private_proposals:
        card_id = str(getattr(proposal, "target_card_id", "") or "")
        title = str(getattr(proposal, "target_card_title", "") or "")
        if card_id and title:
            lookup[card_id] = title
    return lookup


def _percent(value: int, total: int) -> int:
    if total <= 0:
        return 0
    return round((value / total) * 100)


def _risk_order(value: str) -> int:
    return {"high": 0, "medium": 1, "low": 2, "unknown": 3}.get(value, 4)


def _priority_order(value: str) -> int:
    return {"high": 0, "medium": 1, "low": 2, "unknown": 3}.get(value, 4)


def _scope_order(value: str) -> int:
    return {
        "claim_policy": 0,
        "private_claim_policy_proposal": 0,
        "evidence_requirement": 1,
        "private_evidence_policy_proposal": 1,
        "service": 2,
        "private_service_proposal": 2,
        "public_service_card": 2,
        "buyer_problem": 3,
        "cta": 4,
        "metric_signal": 5,
        "coverage_gap": 6,
        "general_knowledge_review": 7,
    }.get(value, 6)


def _markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")[:180]


def _operator_text(value: str) -> str:
    return (
        value.replace("claimów", "twierdzeń")
        .replace("claimy", "twierdzenia")
        .replace(
            "Brakuje zatwierdzonych production-depth kart usług Ekologus.",
            "Brakuje zatwierdzonych kart usług Ekologus do finalnych treści.",
        )
        .replace("review-required", "wymagające oceny")
        .replace("reviewed źródeł", "ocenionych źródeł")
        .replace("reviewed sources", "ocenionych źródeł")
        .replace("reviewerem", "osobą oceniającą")
        .replace("reviewerowi", "osobie oceniającej")
        .replace("reviewed policy fact", "zatwierdzonym faktem polityki")
        .replace("production-depth", "wiedzy do finalnych treści")
        .replace("seed/contract proof", "techniczny seed/proof kontraktu")
        .replace("source-backed", "oparte na źródłach")
        .replace("claim policy", "polityka twierdzeń")
        .replace("Source trace", "Ślad źródłowy")
        .replace("evidence pack", "pakiet dowodów")
        .replace("reviewed evidence policy", "zatwierdzoną polityką dowodową")
        .replace("review", "ocenę")
        .replace("bez ocenę", "bez oceny")
        .replace("wymaga ocenę", "wymaga oceny")
        .replace("redacted source fact", "zredagowany fakt źródłowy")
        .replace(
            "wejść do WILQ jako zatwierdzoną polityką dowodową",
            "wejść do WILQ jako zatwierdzona polityka dowodowa",
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
