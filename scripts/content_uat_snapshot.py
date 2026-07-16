from __future__ import annotations

from typing import Any, cast


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def exact_candidate_from_snapshot(
    snapshot: dict[str, Any], work_item_id: str
) -> dict[str, Any]:
    candidate = snapshot.get("candidate")
    if not isinstance(candidate, dict) or candidate.get("work_item_id") != work_item_id:
        return {}
    return cast(dict[str, Any], candidate)


def matched_snapshot_for_work_item(
    snapshot: dict[str, Any], work_item_id: str
) -> dict[str, Any]:
    return snapshot if exact_candidate_from_snapshot(snapshot, work_item_id) else {}


def search_demand_from_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    planning_workspace = snapshot.get("planning_workspace")
    if not isinstance(planning_workspace, dict):
        return {"status": "missing", "gsc_query_count": None}
    proposal = planning_workspace.get("proposal")
    if not isinstance(proposal, dict):
        return {"status": "missing", "gsc_query_count": None}
    search_demand = proposal.get("search_demand")
    if not isinstance(search_demand, dict):
        return {"status": "missing", "gsc_query_count": None}

    status = str(search_demand.get("status") or "missing")
    raw_rows = search_demand.get("gsc_query_rows")
    rows = raw_rows if status == "available" and isinstance(raw_rows, list) else None
    return {
        "status": status,
        "gsc_query_count": len(rows) if rows is not None else None,
        "gsc_impressions": _total(rows, "impressions"),
        "gsc_clicks": _total(rows, "clicks"),
        "safe_next_step": search_demand.get("safe_next_step"),
    }


def search_demand_markdown_lines(summary: dict[str, Any]) -> list[str]:
    if summary.get("status") == "available":
        return [
            "- popyt GSC: "
            f"{summary.get('gsc_query_count')} sygnałów, "
            f"{summary.get('gsc_impressions')} wyświetleń, "
            f"{summary.get('gsc_clicks')} kliknięć"
        ]
    return [
        "- popyt GSC: brak exact danych; "
        f"{summary.get('safe_next_step') or 'nie interpretuj jako zero'}"
    ]


def sales_brief_trace_from_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    sales_brief_stage = snapshot.get("sales_brief")
    if not isinstance(sales_brief_stage, dict):
        return {"status": "missing", "blocker": "snapshot nie zawiera sales_brief"}
    result = sales_brief_stage.get("sales_brief_result")
    if not isinstance(result, dict):
        return {"status": "missing", "blocker": "snapshot nie zawiera sales_brief_result"}
    brief = result.get("brief")
    blockers = result.get("blockers")
    if not isinstance(brief, dict):
        return {
            "status": "blocked",
            "blockers": blockers if isinstance(blockers, list) else [],
        }
    signal_quality = brief.get("signal_quality")
    constraints = [
        {
            "card_id": constraint.get("card_id"),
            "constraint_type": constraint.get("constraint_type"),
            "label": constraint.get("label"),
            "reason": constraint.get("reason"),
            "evidence_ids": constraint.get("evidence_ids") or [],
        }
        for constraint in _as_list(brief.get("knowledge_constraints"))[:5]
        if isinstance(constraint, dict)
    ]
    return {
        "status": "ready",
        "signal_quality": signal_quality if isinstance(signal_quality, dict) else {},
        "knowledge_constraint_count": len(_as_list(brief.get("knowledge_constraints"))),
        "shown_knowledge_constraints": constraints,
    }


def sales_brief_trace_markdown_lines(trace: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    signal_quality = trace.get("signal_quality")
    if isinstance(signal_quality, dict) and signal_quality.get("status_label"):
        lines.append(f"- jakość Sales Brief: {signal_quality.get('status_label')}")
    status = str(trace.get("status") or "")
    blocker = trace.get("blocker")
    blockers = [
        str(item.get("label") or item.get("reason") or item.get("code") or item)
        for item in _as_list(trace.get("blockers"))
        if isinstance(item, dict) or item
    ]
    if status in {"missing", "blocked"} and (blocker or blockers):
        reason = str(blocker) if blocker else "; ".join(blockers)
        lines.append(f"- Sales Brief: zablokowany albo niedostępny ({reason})")
    constraints = [
        constraint
        for constraint in _as_list(trace.get("shown_knowledge_constraints"))
        if isinstance(constraint, dict)
    ]
    if constraints:
        lines.append("- ograniczenia wiedzy z dowodami:")
        for constraint in constraints:
            constraint_evidence = [
                str(value) for value in constraint.get("evidence_ids") or []
            ]
            lines.append(
                f"  - {constraint.get('label')}: {constraint.get('reason')} "
                f"(dowody: {', '.join(constraint_evidence) or 'brak'})"
            )
    return lines


def _total(rows: list[Any] | None, field: str) -> int | float | None:
    if rows is None:
        return None
    value: int | float = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        metric = row.get(field)
        if isinstance(metric, (int, float)) and not isinstance(metric, bool):
            value += metric
    return value
